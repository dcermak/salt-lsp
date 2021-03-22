import subprocess
import shlex
from typing import Any

from pygls.server import LanguageServer
from pygls.capabilities import COMPLETION
from pygls.lsp.methods import *
from pygls.lsp.types import CompletionItem, CompletionList, CompletionParams, CompletionOptions
from pygls.lsp import types
# import pygls.types


def get_root(path: str) -> str:
    return subprocess.run(shlex.split("git rev-parse --show-toplevel")).stdout


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    def __init__(self) -> None:
        super().__init__()

        self.files: list[SaltFile] = []


salt_server = SaltServer()


class SaltFile:
    def __init__(self, uri: str, contents: Any) -> None:
        self._uri = uri
        self.contents = contents


@salt_server.feature(COMPLETION, CompletionOptions(triggerCharacters=['-']))
def completions(params: CompletionParams):
    """Returns completion items."""
    return CompletionList(
        is_incomplete=False,
        item=[
            CompletionItem(label='Item1'),
            CompletionItem(label='Item2'),
            CompletionItem(label='Item3'),
        ]
    )


@salt_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def on_did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams):
    print(params)


@salt_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: SaltServer, params: types.DidCloseTextDocumentParams):
    """Text document did close notification."""
    server.show_message('Text Document Did Close')


@salt_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: SaltServer, params: types.DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.files.append(SaltFile(params.text_document.uri, params.text_document.text))
    print(params)
