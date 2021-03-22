import os
import os.path
import subprocess
import shlex
from typing import Dict, Union, Optional, List

import yaml
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


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    def __init__(self) -> None:
        super().__init__()

        self.files: Dict[str, SaltFile] = {}


salt_server = SaltServer()


class SaltFile:
    def __init__(
        self,
        params: Union[
            types.DidOpenTextDocumentParams, types.DidChangeTextDocumentParams
        ],
    ) -> None:
        self._uri = params.text_document.uri
        try:
            self.contents = yaml.safe_load(params.text_document.text)
        except Exception:
            self.contents = None


@salt_server.feature(COMPLETION, CompletionOptions(trigger_characters=["-"]))
def completions(params: CompletionParams):
    """Returns completion items."""
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
    ls: LanguageServer, params: types.DidChangeTextDocumentParams
):
    ls.files[params.text_document.uri] = SaltFile(params)


@salt_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: SaltServer, params: types.DidCloseTextDocumentParams):
    """Text document did close notification."""
    del ls.files[params.text_document.uri]


@salt_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: SaltServer, params: types.DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.files[params.text_document.uri] = SaltFile(params)
    print(ls.files[params.text_document.uri].contents)
