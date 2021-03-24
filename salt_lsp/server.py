"""
Language Server Protocol implementation
"""

import os.path
import re
from typing import Any, Dict, List, Tuple, Optional
import logging

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
        self._state_name_completions: Dict[str, StateNameCompletion] = {}

        self.logger: logging.Logger = logging.getLogger()
        self._state_names: List[str] = []

    def post_init(
        self,
        state_name_completions: Dict[str, StateNameCompletion],
        log_level=logging.DEBUG,
    ) -> None:
        self._state_name_completions = state_name_completions
        self._state_names = list(state_name_completions.keys())
        self.logger = logging.getLogger("SaltServer")
        self.logger.setLevel(log_level)

    def complete_state_name(
        self, params: types.CompletionParams
    ) -> List[Tuple[str, Optional[str]]]:
        assert (
            params.context is not None
            and params.context.trigger_character == "."
        )

        contents = self._files[params.text_document.uri]
        ind = utils.position_to_index(
            contents, params.position.line, params.position.character
        )
        last_match = utils.get_last_element_of_iterator(
            SaltServer.LINE_START_REGEX.finditer(contents, 0, ind)
        )
        if last_match is None:
            # FIXME: log a warning/error
            return []
        state_name = contents[last_match.span()[1] : ind - 1]
        if state_name in self._state_name_completions:
            completer = self._state_name_completions[state_name]
            return completer.provide_subname_completion()
        return []

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
                self.show_message(
                    "Failed parsing YAML: " + str(err),
                    msg_type=types.MessageType.Error,
                )
                return None
        return None


salt_server = SaltServer()


@salt_server.feature(
    COMPLETION, CompletionOptions(trigger_characters=["-", "."])
)
def completions(
    salt_srv: SaltServer, params: CompletionParams
) -> Optional[CompletionList]:
    """Returns completion items."""
    if params.context is not None and params.context.trigger_character == ".":
        return CompletionList(
            is_incomplete=False,
            items=[
                CompletionItem(label=sub_name, documentation=docs)
                for sub_name, docs in salt_srv.complete_state_name(params)
            ],
        )

    file_contents = ls.get_file_contents(params.text_document.uri)
    if file_contents is None:
        # FIXME: load the file
        return None

    path = utils.construct_path_to_position(file_contents, params.position)
    if (
        path == ["include"]
        or os.path.basename(params.text_document.uri) == "top.sls"
        and len(path) == 2
    ):
        file_path = utils.FileUri(params.text_document.uri).path
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
def on_did_change(
    salt_srv: SaltServer, params: types.DidChangeTextDocumentParams
):
    salt_srv.reconcile_file(params)


@salt_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(salt_srv: SaltServer, params: types.DidCloseTextDocumentParams):
    """Text document did close notification."""
    salt_srv.remove_file(params)


@salt_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(
    salt_srv: SaltServer, params: types.DidOpenTextDocumentParams
):
    """Text document did open notification."""
    salt_srv.register_file(params)
