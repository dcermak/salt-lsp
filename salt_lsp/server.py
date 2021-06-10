"""
Language Server Protocol implementation
"""

import logging
import re
from os.path import basename
from typing import Dict, List, Optional, Sequence, Tuple, Union, cast

from pygls.capabilities import COMPLETION
from pygls.lsp import types
from pygls.lsp.methods import (
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    DEFINITION,
    DOCUMENT_SYMBOL,
)
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
)
from pygls.server import LanguageServer

import salt_lsp.utils as utils
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
        super().__init__(protocol_cls=SaltLspProto)

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
        log_level=logging.DEBUG,
    ) -> None:
        self._state_name_completions = state_name_completions
        self._state_names = list(state_name_completions.keys())
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)

    def complete_state_name(
        self, params: types.CompletionParams
    ) -> List[Tuple[str, Optional[str]]]:
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
    ) -> Optional[types.Location]:
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
                return types.Location(
                    uri=str(uri),
                    range=lsp_range,
                )

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

    file = salt_srv.get_sls_file(params.text_document.uri)
    if file is None or file.contents is None:
        # FIXME: load the file
        return None

    path = utils.construct_path_to_position(file.contents, params.position)
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


@salt_server.feature(DEFINITION)
def goto_definition(
    salt_srv: SaltServer, params: types.DeclarationParams
) -> Optional[types.Location]:
    uri = params.text_document.uri
    file = salt_srv.get_sls_file(uri)
    parsed_contents = salt_srv.get_file_parsed_contents(uri)
    if file is None or file.contents is None or parsed_contents is None:
        return None
    path = utils.construct_path_to_position(file.contents, params.position)

    # Going to definition is only handled on requisites ids
    if not isinstance(path[-1], RequisiteNode):
        return None

    id_to_find = cast(RequisiteNode, path[-1]).reference
    if id_to_find is None:
        return None

    # we can be lucky and the id is actually defined in the same document
    if id_to_find in parsed_contents:
        pos = types.Position(
            line=parsed_contents[id_to_find].lc.line,
            character=parsed_contents[id_to_find].lc.col,
        )
        return types.Location(uri=uri, range=types.Range(start=pos, end=pos))

    return salt_srv.find_id_in_includes(id_to_find, uri)


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
def did_open(
    salt_srv: SaltServer, params: types.DidOpenTextDocumentParams
) -> Optional[types.TextDocumentItem]:
    """Text document did open notification.

    This function registers the newly opened file with the salt server.
    """
    salt_srv.register_file(params)
    registered_file = salt_srv.get_sls_file(params.text_document.uri)
    if registered_file is None:
        salt_srv.logger.error(
            "Could not retrieve the just registered file with the URI %s from "
            "the server",
            params.text_document.uri,
        )
        return None
    return types.TextDocumentItem(
        uri=params.text_document.uri,
        language_id=SLS_LANGUAGE_ID,
        text=params.text_document.text or "",
        version=registered_file.version,
    )


@salt_server.feature(DOCUMENT_SYMBOL)
def document_symbol(
    salt_srv: SaltServer, params: types.DocumentSymbolParams
) -> Optional[
    Union[List[types.DocumentSymbol], List[types.SymbolInformation]]
]:
    sls_file = salt_srv.get_sls_file(params.text_document.uri)
    # FIXME: register & read in file now
    if sls_file is None:
        return None

    tree = parse(sls_file.contents)
    doc_symbols = tree_to_document_symbols(
        tree, salt_srv._state_name_completions
    )
    return doc_symbols
