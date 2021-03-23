from collections import OrderedDict
import os
import os.path
import subprocess
import shlex
from typing import Any, Dict, Union, Optional, List
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
    Position,
)
from pygls.lsp import types


def get_git_root(path: str) -> str:
    return str(
        subprocess.run(
            shlex.split("git rev-parse --show-toplevel"), capture_output=True
        ).stdout,
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
    print(path)
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
    document: Any, pos: Position, cur_path: List[Union[str, int]]
) -> Optional[List[Union[str, int]]]:
    if not isinstance(document, OrderedDict) and not isinstance(
        document, list
    ):
        return None

    entries = (
        document if isinstance(document, list) else list(document.values())
    )
    if len(entries) == 0:
        return cur_path

    match = entries[0] if hasattr(entries[0], "lc") else None
    match_ind = 0

    # Iterate over all entries in the document and find the first that is
    # beyond the given position. Store the entry *before* that one in match and
    # its index in match_index.
    # Special case: if we hit the exact line, then that is the match and not
    # the previous one
    for ind, entry in enumerate(entries):
        # entry can be a primitive type and will have no position information
        # then => have to skip over these for lack of better knowledge
        if hasattr(entry, "lc") and entry.lc.line >= pos.line:
            if entry.lc.line == pos.line:
                match, match_ind = entry, ind
            break
        match, match_ind = entry, ind

    # add the current node to the path list
    if isinstance(document, OrderedDict):
        cur_path.append(list(document.keys())[match_ind])
    elif isinstance(document, list):
        cur_path.append(match_ind)

    if isinstance(match, list) or isinstance(match, OrderedDict):
        return _construct_path_to_position(match, pos, cur_path)

    # we should have only primitive types now
    assert (
        match is None
        or isinstance(match, str)
        or isinstance(match, bool)
        or isinstance(match, int)
        or isinstance(match, float)
    ), (
        "expected to reach a leaf node that must be a primitive type, "
        + f"but got a '{type(match)}' instead"
    )
    # if we are in a YAML list of primitive types (i.e. the last list entry is
    # the list index), then we will not be able to get the correct list index
    # as ruamel.yaml does not store the positions of primitive types
    if isinstance(cur_path[-1], int):
        cur_path.pop()
    return cur_path


def construct_path_to_position(
    document: Any, pos: Position
) -> List[Union[str, int]]:
    if not isinstance(document, OrderedDict) and not isinstance(
        document, list
    ):
        # oops, we cannot do a thing with this
        raise ValueError(
            f"Expected an ordered dictionary or a list, but got a {type(document)}"
        )

    return _construct_path_to_position(document, pos, []) or []


def position_to_index(text, line, column):
    split = text.splitlines(keepends=True)
    return sum([len(l) for i, l in enumerate(split) if i < line]) + column


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    def __init__(self) -> None:
        super().__init__()

        self._files: Dict[str, Any] = {}

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
                start = position_to_index(
                    content,
                    change.range.start.line,
                    change.range.start.character,
                )
                end = position_to_index(
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
            except Exception:
                return None
        return None


salt_server = SaltServer()


@salt_server.feature(COMPLETION, CompletionOptions(trigger_characters=["-"]))
def completions(ls: SaltServer, params: CompletionParams):
    """Returns completion items."""
    file_contents = ls.get_file_contents(params.text_document.uri)
    if file_contents is None:
        # FIXME: load the file
        return

    path = construct_path_to_position(file_contents, params.position)
    if (
        path == ["include"]
        or os.path.basename(params.text_document.uri) == "top.sls"
        and len(path) == 2
    ):
        file_path = urllib.parse.urlparse(params.text_document.uri).path
        includes = get_sls_includes(file_path)
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
    del ls.files[params.text_document.uri]


@salt_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: SaltServer, params: types.DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.register_file(params)
