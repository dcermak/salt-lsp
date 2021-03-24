"""
Language Server Protocol implementation
"""

import os.path
import re
from typing import Any, Dict, List, Optional
import urllib.parse

from ruamel import yaml
from pygls.server import LanguageServer
from pygls.capabilities import (
    COMPLETION,
)
from pygls.lsp.methods import (
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
)
from pygls.lsp.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionParams,
    CompletionOptions,
)
from pygls.lsp import types

import salt_lsp.utils as utils
from salt_lsp.base_types import StateNameCompletion


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    LINE_START_REGEX = re.compile(r"^(\s*)\b", re.MULTILINE)

    def __init__(self) -> None:
        super().__init__()

        self._files: Dict[str, Any] = {}
        self._state_name_completions: Optional[
            Dict[str, StateNameCompletion]
        ] = None

    def post_init(
        self, state_name_completions: Dict[str, StateNameCompletion]
    ) -> None:
        self._state_name_completions = state_name_completions
        self._state_names = list(state_name_completions.keys())

    def complete_state_name(self, params: types.CompletionParams) -> List[str]:
        assert params.context.trigger_character == "."
        if self._state_name_completions is None:
            # FIXME: log an error
            return []

        contents = self._files[params.text_document.uri]
        ind = utils.position_to_index(
            contents, params.position.line, params.position.character
        )
        print(SaltServer.LINE_START_REGEX.search(contents, 0, ind))
        last_match = SaltServer.LINE_START_REGEX.search(contents[:ind])

        state_name = contents[last_match.span()[1] : ind - 1]
        completer = self._state_name_completions[state_name]
        return completer.provide_subname_completion()

    def remove_file(self, params: types.DidCloseTextDocumentParams) -> None:
        del self._files[params.text_document.uri]

    def register_file(
        self,
        params: types.DidOpenTextDocumentParams,
    ) -> None:
        self._files[params.text_document.uri] = params.text_document.text

    def reconcile_file(
        self,
        params: types.DidChangeTextDocumentParams,
    ) -> None:
        if params.text_document.uri in self._files:
            content = self._files[params.text_document.uri]
            for change in params.content_changes:
                if not hasattr(change, "range"):
                    continue
                assert isinstance(change, types.TextDocumentContentChangeEvent)
                if change.range is None:
                    continue
                start = utils.position_to_index(
                    content,
                    change.range.start.line,
                    change.range.start.character,
                )
                end = utils.position_to_index(
                    content, change.range.end.line, change.range.end.character
                )
                self._files[params.text_document.uri] = (
                    content[:start] + change.text + content[end:]
                )

    def get_file_contents(self, uri: str) -> Optional[Any]:
        if uri in self._files:
            try:
                content = self._files[uri]
                return yaml.load(content, Loader=yaml.RoundTripLoader)
            except Exception as err:
                self.show_message("Failed parsing YAML: " + str(err), msg_type=types.MessageType.Error)
                return None
        return None


salt_server = SaltServer()


@salt_server.feature(
    COMPLETION, CompletionOptions(trigger_characters=["-", "."])
)
def completions(ls: SaltServer, params: CompletionParams):
    """Returns completion items."""
    file_contents = ls.get_file_contents(params.text_document.uri)
    if file_contents is None:
        # FIXME: load the file
        return

    if params.context.trigger_character == ".":
        return ls.complete_state_name(params)

    path = utils.construct_path_to_position(file_contents, params.position)
    if (
        path == ["include"]
        or os.path.basename(params.text_document.uri) == "top.sls"
        and len(path) == 2
    ):
        file_path = urllib.parse.urlparse(params.text_document.uri).path
        includes = utils.get_sls_includes(file_path)
        return CompletionList(
            is_incomplete=False,
            items=[
                CompletionItem(label=f" {include}") for include in includes
            ],
        )

    return CompletionList(
        is_incomplete=False,
        items=[
            CompletionItem(label="Item1", kind=CompletionItemKind.Text),
            CompletionItem(label="Item2"),
            CompletionItem(label="Item3"),
        ],
    )


@salt_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def on_did_change(ls: SaltServer, params: types.DidChangeTextDocumentParams):
    ls.reconcile_file(params)


@salt_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: SaltServer, params: types.DidCloseTextDocumentParams):
    """Text document did close notification."""
    ls.remove_file(params)


@salt_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: SaltServer, params: types.DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.register_file(params)
