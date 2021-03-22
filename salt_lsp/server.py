from collections import OrderedDict
import os
import os.path
import subprocess
import shlex
from typing import Any, Dict, Union, Optional, List

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
    Position,
)
from pygls.lsp import types


def get_git_root(path: str) -> str:
    return str(
        subprocess.run(shlex.split("git rev-parse --show-toplevel")).stdout,
        encoding="utf-8",
    )


def get_top(path: str) -> Optional[str]:
    parent = os.path.dirname(path)
    if not bool(parent):
        return None
    if os.path.isfile(os.path.join(parent, "top.sls")):
        return parent
    return get_top(parent)


def get_root(path: str) -> str:
    root = get_top(path)
    return root or get_git_root(path)


def get_sls_includes(path: str) -> List[str]:
    sls_files = []
    top = get_root(path)
    for root, _, files in os.walk(top):
        base = root[len(top) + 1 :].replace(os.path.sep, ".")
        sls_files += [
            base + (file[:-4] if file != "init.sls" else "")
            for file in files
            if file.endswith(".sls")
        ]
    return sls_files


def get_lists_parent_node(document: Any, pos: Position):
    """
    WIP: this function shall find the parent node of a new list entry

    It sorta kinda works, but it finds the last element that is before pos,
    however that is not really the node that we actually want.
    """
    if not isinstance(document, OrderedDict) and not isinstance(
        document, list
    ):
        # oops, we cannot do a thing with this
        raise ValueError(
            f"Expected an ordered dictionary or a list, but got a {type(document)}"
        )

    entries = (
        document if isinstance(document, list) else list(document.values())
    )
    if len(entries) == 0:
        return None

    prev = entries[0] if hasattr(entries[0], "lc") else None

    for entry in entries:
        if hasattr(entry, "lc") and entry.lc.line > pos.line:
            break
        prev = entry

    if isinstance(prev, list) or isinstance(prev, OrderedDict):
        res = get_lists_parent_node(prev, pos)
        return res or prev

    return prev


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    def __init__(self) -> None:
        super().__init__()

        self._files: Dict[str, Any] = {}

    def remove_file(self, params: types.DidCloseTextDocumentParams) -> None:
        del self._files[params.text_document.uri]

    def register_file(
        self,
        params: Union[
            types.DidOpenTextDocumentParams, types.DidChangeTextDocumentParams
        ],
    ) -> None:
        try:
            contents = yaml.load(
                params.text_document.text, Loader=yaml.RoundTripLoader
            )
        except Exception:
            return

        assert contents is not None
        self._files[params.text_document.uri] = contents

    def get_file_contents(self, uri: str) -> Optional[Any]:
        if uri in self._files:
            return self._files[uri]
        return None


salt_server = SaltServer()


@salt_server.feature(COMPLETION, CompletionOptions(trigger_characters=["-"]))
def completions(ls: SaltServer, params: CompletionParams):
    """Returns completion items."""
    file_contents = ls.get_file_contents(params.text_document.uri)
    if file_contents is None:
        # FIXME: load the file
        return

    print(get_lists_parent_node(file_contents, params.position))

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
    ls.register_file(params)


@salt_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: SaltServer, params: types.DidCloseTextDocumentParams):
    """Text document did close notification."""
    del ls.files[params.text_document.uri]


@salt_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: SaltServer, params: types.DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.register_file(params)
