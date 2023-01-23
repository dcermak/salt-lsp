"""
Language Server Protocol implementation
"""

import logging
import re
from os.path import basename
from typing import Dict, List, Optional, Sequence, Tuple, Union, cast

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    INITIALIZE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    DeclarationParams,
    DidOpenTextDocumentParams,
    DocumentSymbol,
    DocumentSymbolParams,
    InitializeParams,
    Location,
    SymbolInformation,
    TextDocumentItem,
)
from pygls.server import LanguageServer

from salt_lsp import __version__
from salt_lsp import utils
from salt_lsp.base_types import StateNameCompletion, SLS_LANGUAGE_ID
from salt_lsp.workspace import SaltLspProto, SlsFileWorkspace
from salt_lsp.parser import (
    IncludesNode,
    RequisiteNode,
    StateParameterNode,
    Tree,
)


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    LINE_START_REGEX = re.compile(r"^(\s*)\b", re.MULTILINE)

    def __init__(self) -> None:
        super().__init__(
            name="SaltServer", version=__version__, protocol_cls=SaltLspProto
        )

        self._state_name_completions: Dict[str, StateNameCompletion] = {}

        self.logger: logging.Logger = logging.getLogger()
        self._state_names: List[str] = []

    @property
    def workspace(self) -> SlsFileWorkspace:
        assert isinstance(super().workspace, SlsFileWorkspace), (
            "expected to get a 'SlsFileWorkspace', but got a "
            f"'{super().workspace.__class__.__name__}' instead"
        )
        return cast(SlsFileWorkspace, super().workspace)

    def post_init(
        self,
        state_name_completions: Dict[str, StateNameCompletion],
        log_level: int = logging.DEBUG,
    ) -> None:
        """Further initialisation, called after
        setup_salt_server_capabilities."""
        self._state_name_completions = state_name_completions
        self._state_names = list(state_name_completions.keys())
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)

    def complete_state_name(
        self, params: CompletionParams
    ) -> List[Tuple[str, Optional[str]]]:
        """Complete state name at current position"""
        assert (
            params.context is not None
            and params.context.trigger_character == "."
        )

        doc = self.workspace.get_document(params.text_document.uri)
        contents = doc.source
        ind = doc.offset_at_position(params.position)
        last_match = utils.get_last_element_of_iterator(
            SaltServer.LINE_START_REGEX.finditer(contents, 0, ind)
        )
        if last_match is None:
            self.logger.debug(
                "expected to find whitespace before the position (%d, %d) "
                "but got no regex match for the document: %s",
                params.position.line,
                params.position.character,
                contents,
            )
            return []
        state_name = contents[last_match.span()[1] : ind - 1]
        if state_name in self._state_name_completions:
            completer = self._state_name_completions[state_name]
            return completer.provide_subname_completion()
        return []

    def find_id_in_doc_and_includes(
        self, id_to_find: str, starting_uri: str
    ) -> Optional[Location]:
        """Finds the first matching location of the given id in the document or
        in its includes.

        This function searches for the `id_to_find` starting in
        `starting_uri`. If it does not find it in there, then it will continue
        to search in the includes and returns the first match that it finds.
        """
        self.logger.debug(
            "Request to find id '%s' starting in uri '%s'",
            id_to_find,
            starting_uri,
        )
        if (tree := self.workspace.trees.get(starting_uri)) is None:
            self.logger.error(
                "Cannot search in '%s', no tree present", starting_uri
            )
            return None

        inc_of_uri = self.workspace.includes.get(starting_uri, [])

        # FIXME: need to take ordering into account:
        # https://docs.saltproject.io/en/latest/ref/states/compiler_ordering.html#the-include-statement
        trees_and_uris_to_search: Sequence[
            Tuple[Tree, Union[str, utils.FileUri]]
        ] = [(tree, starting_uri)] + [
            (t, inc)
            for inc in inc_of_uri
            if (t := self.workspace.trees.get(inc)) is not None
        ]

        for tree, uri in trees_and_uris_to_search:
            self.logger.debug("Searching in '%s'", uri)
            matching_states = [
                state
                for state in tree.states
                if state.identifier == id_to_find
            ]
            if len(matching_states) != 1:
                continue

            if (
                lsp_range := utils.ast_node_to_range(matching_states[0])
            ) is not None:
                self.logger.debug(
                    "found match at '%s', '%s", lsp_range.start, lsp_range.end
                )
                return Location(uri=str(uri), range=lsp_range)

        return None


def setup_salt_server_capabilities(server: SaltServer) -> None:
    """Adds the completion, goto definition and document symbol capabilities to
    the provided server.
    """

    @server.feature(INITIALIZE)
    def initialize(params: InitializeParams) -> None:
        """Set up custom workspace."""
        del params  # not needed
        server.lsp.setup_custom_workspace()
        server.logger.debug("Replaced workspace with SlsFileWorkspace")

    @server.feature(
        TEXT_DOCUMENT_COMPLETION,
        CompletionOptions(trigger_characters=["-", "."]),
    )
    def completions(
        salt_server: SaltServer, params: CompletionParams
    ) -> Optional[CompletionList]:
        """Returns completion items."""
        if (
            params.context is not None
            and params.context.trigger_character == "."
        ):
            return CompletionList(
                is_incomplete=False,
                items=[
                    CompletionItem(label=sub_name, documentation=docs)
                    for sub_name, docs in salt_server.complete_state_name(
                        params
                    )
                ],
            )

        if (
            tree := salt_server.workspace.trees.get(params.text_document.uri)
        ) is None:
            return None

        path = utils.construct_path_to_position(tree, params.position)
        if (
            path
            and isinstance(path[-1], IncludesNode)
            or basename(params.text_document.uri) == "top.sls"
            and isinstance(path[-1], StateParameterNode)
        ):
            file_path = utils.FileUri(params.text_document.uri).path
            includes = utils.get_sls_includes(file_path)
            return CompletionList(
                is_incomplete=False,
                items=[
                    CompletionItem(label=f" {include}") for include in includes
                ],
            )
        return None

    @server.feature(TEXT_DOCUMENT_DEFINITION)
    def goto_definition(
        salt_server: SaltServer, params: DeclarationParams
    ) -> Optional[Location]:
        uri = params.text_document.uri
        if (tree := salt_server.workspace.trees.get(uri)) is None:
            return None
        path = utils.construct_path_to_position(tree, params.position)

        # Going to definition is only handled on requisites ids
        if not isinstance(path[-1], RequisiteNode):
            return None

        if (id_to_find := path[-1].reference) is None:
            return None

        return salt_server.find_id_in_doc_and_includes(id_to_find, uri)

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    def did_open(
        salt_server: SaltServer, params: DidOpenTextDocumentParams
    ) -> Optional[TextDocumentItem]:
        """Text document did open notification.

        This function registers the newly opened file with the salt server.
        """
        salt_server.logger.debug(
            "adding text document '%s' to the workspace",
            params.text_document.uri,
        )
        doc = salt_server.workspace.get_document(params.text_document.uri)
        return TextDocumentItem(
            uri=params.text_document.uri,
            language_id=SLS_LANGUAGE_ID,
            text=params.text_document.text or "",
            version=doc.version,
        )

    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(
        salt_server: SaltServer, params: DocumentSymbolParams
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation]]]:
        return salt_server.workspace.document_symbols.get(
            params.text_document.uri, []
        )
