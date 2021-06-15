"""Module implementing a custom workspace that automatically updates the parsed
contents utilizing the existing Workspace implementation from pygls.

"""
from logging import getLogger, Logger, DEBUG
from pathlib import Path
from platform import python_version_tuple
from typing import List, Optional, Union

from pygls.lsp import types, InitializeResult
from pygls.protocol import LanguageServerProtocol
from pygls.workspace import Workspace

from salt_lsp.base_types import CompletionsDict, SLS_LANGUAGE_ID
from salt_lsp.utils import UriDict, FileUri, get_top
from salt_lsp.parser import parse, Tree
from salt_lsp.document_symbols import tree_to_document_symbols


if int(python_version_tuple()[1]) <= 8:

    def is_relative_to(p1: Path, p2: Path) -> bool:
        # stolen from CPython's source
        """Return True if the path is relative to another path or False."""
        try:
            p1.relative_to(p2)
            return True
        except ValueError:
            return False


else:

    def is_relative_to(p1: Path, p2: Path) -> bool:
        return p1.is_relative_to(p2)


class SlsFileWorkspace(Workspace):
    """An extension of pygl's :ref:`Workspace` class that has additional
    properties that are collected from the workspace.

    It hooks into the :ref:`Workspace`'s update function to automatically keep
    all properties up to date.
    """

    def __init__(
        self, state_name_completions: CompletionsDict, *args, **kwargs
    ) -> None:
        #: dictionary containing the parsed contents of all tracked documents
        self._trees: UriDict[Tree] = UriDict()

        #: document symbols of all tracked documents
        self._document_symbols: UriDict[List[types.DocumentSymbol]] = UriDict()

        #: included FileUris of every tracked document
        self._includes: UriDict[List[FileUri]] = UriDict()

        #: top path corresponding to every workspace folder
        self._top_paths: UriDict[Optional[FileUri]] = UriDict()
        self._state_name_completions = state_name_completions

        self.logger: Logger = getLogger(self.__class__.__name__)
        # FIXME: make this configurable
        self.logger.setLevel(DEBUG)

        super().__init__(*args, **kwargs)

    @property
    def trees(self) -> UriDict[Tree]:
        """A dictionary which contains the parsed :ref:`Tree` for each document
        tracked by the workspace.
        """
        return self._trees

    @property
    def document_symbols(self) -> UriDict[List[types.DocumentSymbol]]:
        """The document symbols of each SLS files in the workspace."""
        return self._document_symbols

    @property
    def includes(self) -> UriDict[List[FileUri]]:
        """The list of includes of each SLS file in the workspace."""
        return self._includes

    def _resolve_includes(
        self, text_document_uri: Union[str, FileUri]
    ) -> None:
        if (
            (tree := self._trees[text_document_uri]) is None
            or tree.includes is None
            or len(tree.includes.includes) == 0
        ):
            return

        ws_folder = self._get_workspace_of_document(text_document_uri)
        if (
            ws_folder in self._top_paths
            and self._top_paths[ws_folder] is not None
        ):
            top_path = self._top_paths[ws_folder]
        else:
            top_path = ws_folder

        assert top_path is not None

        self._includes[text_document_uri] = [
            FileUri(f)
            for incl in tree.includes.includes
            if (f := incl.get_file(FileUri(top_path).path)) is not None
        ]

        new_includes = self._includes[text_document_uri]

        # now try to re-read all the trees if they are not present:
        for inc in self._includes[text_document_uri]:
            if inc not in self._trees:
                self.logger.debug(
                    "Adding file '%s' via includes of '%s'",
                    inc,
                    text_document_uri,
                )
                with open(inc.path, "r") as inc_file:
                    self.put_document(
                        types.TextDocumentItem(
                            uri=str(inc),
                            language_id=SLS_LANGUAGE_ID,
                            version=0,
                            text=inc_file.read(-1),
                        )
                    )
                self._resolve_includes(inc)

            if inc in self._trees and self._includes.get(inc):
                new_includes += self._includes[inc]

        assert len(new_includes) >= len(self._includes[text_document_uri])
        self._includes[text_document_uri] = new_includes

    def _update_document(
        self,
        text_document: Union[
            types.TextDocumentItem, types.VersionedTextDocumentIdentifier
        ],
    ) -> None:
        self.logger.debug("updating document '%s'", text_document.uri)
        uri = text_document.uri
        tree = parse(self.get_document(uri).source)
        self._trees[uri] = tree

        self._document_symbols[uri] = tree_to_document_symbols(
            tree, self._state_name_completions
        )

        self._resolve_includes(text_document.uri)

    def _get_workspace_of_document(self, uri: Union[str, FileUri]) -> FileUri:
        for workspace in self._folders:
            workspace_uri = workspace.uri

            if is_relative_to(
                Path(FileUri(uri).path), Path(FileUri(workspace_uri).path)
            ):
                return workspace_uri

        return self.root_uri

    def add_folder(self, folder: types.WorkspaceFolder) -> None:
        super().add_folder(folder)
        top_path = get_top(FileUri(folder.uri).path)
        self._top_paths[FileUri(folder.uri)] = (
            FileUri(top_path) if top_path is not None else None
        )

    def remove_folder(self, folder_uri: Union[str, FileUri]) -> None:
        super().remove_folder(str(folder_uri))
        self._top_paths.pop(FileUri(folder_uri))

    def update_document(
        self,
        text_document: types.VersionedTextDocumentIdentifier,
        change: types.TextDocumentContentChangeEvent,
    ) -> None:
        super().update_document(text_document, change)
        self._update_document(text_document)

    def remove_document(self, doc_uri: str) -> None:
        super().remove_document(doc_uri)
        self._document_symbols.pop(FileUri(doc_uri))
        self._trees.pop(FileUri(doc_uri))

    def put_document(self, text_document: types.TextDocumentItem) -> None:
        super().put_document(text_document)
        self._update_document(text_document)


class SaltLspProto(LanguageServerProtocol):
    """Custom protocol that replaces the workspace with a SlsFileWorkspace
    instance.
    """

    workspace: SlsFileWorkspace

    def bf_initialize(self, *args, **kwargs) -> InitializeResult:
        res = super().bf_initialize(*args, **kwargs)
        ws = self.workspace
        self.workspace = SlsFileWorkspace(
            self._server._state_name_completions,
            ws.root_uri,
            self._server.sync_kind,
            ws.folders.values(),
        )
        return res
