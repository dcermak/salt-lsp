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


def _construct_path_to_position(
    document: Any, pos: Position, cur_path: List[str]
) -> Optional[List[str]]:
    if not isinstance(document, OrderedDict) and not isinstance(
        document, list
    ):
        return None

    entries = (
        document if isinstance(document, list) else list(document.values())
    )
    if len(entries) == 0:
        return cur_path

    prev = entries[0] if hasattr(entries[0], "lc") else None

    for ind, entry in enumerate(entries):
        if hasattr(entry, "lc") and entry.lc.line > pos.line:
            break
        prev = entry

    print(ind, prev)
    if hasattr(prev, "lc"):
        print(prev.lc.line, prev.lc.col)

    if isinstance(document, OrderedDict):
        if hasattr(prev, "lc"):
            if prev.lc.line == pos.line and pos.character > prev.lc.col:
                cur_path.append(list(document.keys())[max(ind - 1, 0)])

    if isinstance(prev, list) or isinstance(prev, OrderedDict):
        return _construct_path_to_position(prev, pos, cur_path)

    assert (
        isinstance(prev, str)
        or isinstance(prev, bool)
        or isinstance(prev, int)
        or isinstance(prev, float)
    ), (
        "expected to reach a leaf node that must be a primitive type, "
        + f"but got a '{type(prev)}' instead"
    )
    return cur_path


def construct_path_to_position(
    document: Any, pos: Position
) -> Optional[List[str]]:
    if not isinstance(document, OrderedDict) and not isinstance(
        document, list
    ):
        # oops, we cannot do a thing with this
        raise ValueError(
            f"Expected an ordered dictionary or a list, but got a {type(document)}"
        )

    return _construct_path_to_position(document, pos, [])


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

    print(construct_path_to_position(file_contents, params.position))

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
