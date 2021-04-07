"""
Language Server Protocol implementation
"""

import logging
import re
from dataclasses import dataclass, field
from os.path import basename, exists, join
from typing import Any, Dict, List, Optional, Tuple, Union, cast

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
from ruamel import yaml

import salt_lsp.utils as utils
from salt_lsp.base_types import StateNameCompletion
from salt_lsp.document_symbols import tree_to_document_symbols
from salt_lsp.parser import (
    IncludesNode,
    RequisiteNode,
    StateParameterNode,
    parse,
)


@dataclass(init=False)
class SlsFile:
    contents: str
    path: str
    parsed_contents: Optional[Any] = None
    parsed_contents_stale: bool = True

    #: A list of URIs with the includes of this sls file
    includes: List[utils.Uri] = field(default_factory=list)

    @staticmethod
    def resolve_include(top_sls_dir: str, include_entry: str) -> Optional[str]:
        dest = join(*include_entry.split("."))
        init_sls_path = join(top_sls_dir, dest, "init.sls")
        entry_sls_path = join(top_sls_dir, f"{dest}.sls")
        if exists(init_sls_path):
            return init_sls_path
        if exists(entry_sls_path):
            return entry_sls_path
        return None

    def __init__(self, contents: str, uri: str) -> None:
        self.contents = contents
        self.path = utils.FileUri(uri).path
        self.reparse()
        self.includes = []

        if self.parsed_contents is not None:
            top_sls_location = utils.get_top(self.path)
            if (
                "include" in self.parsed_contents
                and isinstance(self.parsed_contents["include"], list)
                and top_sls_location is not None
            ):
                self.includes = list(
                    utils.Uri(f"file://{path}")
                    for path in filter(
                        None,
                        (
                            SlsFile.resolve_include(top_sls_location, inc)
                            for inc in self.parsed_contents["include"]
                        ),
                    )
                )

    def reparse(self) -> None:
        try:
            self.parsed_contents = yaml.load(
                self.contents, Loader=yaml.RoundTripLoader
            )
            self.parsed_contents_stale = False
        except Exception:
            self.parsed_contents_stale = True


class SaltServer(LanguageServer):
    """Experimental language server for salt states"""

    LINE_START_REGEX = re.compile(r"^(\s*)\b", re.MULTILINE)

    def __init__(self) -> None:
        super().__init__()

        self._files: Dict[str, SlsFile] = {}
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

        contents = self._files[params.text_document.uri].contents
        ind = utils.position_to_index(
            contents, params.position.line, params.position.character
        )
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

    def remove_file(self, params: types.DidCloseTextDocumentParams) -> None:
        del self._files[params.text_document.uri]

    def register_file(
        self,
        params: types.DidOpenTextDocumentParams,
    ) -> None:
        if params.text_document.uri not in self._files:
            self._files[params.text_document.uri] = SlsFile(
                contents=params.text_document.text,
                uri=params.text_document.uri,
            )
        else:
            self._files[
                params.text_document.uri
            ].contents = params.text_document.text
            self._files[params.text_document.uri].reparse()

        self.register_includes(params.text_document.uri)

    def reconcile_file(
        self,
        params: types.DidChangeTextDocumentParams,
    ) -> None:
        if params.text_document.uri in self._files:
            content = self._files[params.text_document.uri].contents
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
                self._files[params.text_document.uri].contents = (
                    content[:start] + change.text + content[end:]
                )
                self._files[params.text_document.uri].reparse()

    def register_includes(self, uri: str) -> None:
        if uri not in self._files:
            return
        sls_file = self._files[uri]

        for include in sls_file.includes:
            assert utils.is_valid_file_uri(
                include
            ), f"got an invalid file uri: {include}"

            if include not in self._files:
                with open(utils.FileUri(include).path, "r") as include_file:
                    contents = include_file.read(-1)
                self.register_file(
                    types.DidOpenTextDocumentParams(
                        text_document=types.TextDocumentItem(
                            uri=include, text=contents
                        )
                    )
                )

    def find_id_in_includes(
        self, id_to_find: str, starting_uri: str
    ) -> Optional[types.Location]:
        # FIXME: this function is a bit dumb, as it actually loads the SlsFile
        # of each include and then does that again when it calls itself
        # recursively. -> the SlsFile should be one of its parameters
        sls_file = self.get_sls_file(starting_uri)
        if sls_file is None:
            self.logger.error(
                "Could not get the SlsFile of the file %s",
                starting_uri,
            )
            return None

        for inc in sls_file.includes:
            inc_contents = self.get_file_parsed_contents(inc)
            if inc_contents is None:
                continue

            if id_to_find in inc_contents:
                target_element = inc_contents[id_to_find]
                # this is a primitive type which has no line & column numbers
                if not hasattr(target_element, "lc"):
                    return None
                pos = types.Position(
                    line=target_element.lc.line,
                    character=target_element.lc.col,
                )
                return types.Location(
                    uri=inc, range=types.Range(start=pos, end=pos)
                )

        for inc in sls_file.includes:
            recursive_match = self.find_id_in_includes(id_to_find, inc)
            if recursive_match is not None:
                return recursive_match

        return None

    def get_file_parsed_contents(self, uri: str) -> Optional[Any]:
        """
        Returns the contents of the file with the given uri de-serialized from
        YAML.
        If the contents cannot be de-serialized, then None is returned.
        """
        if uri in self._files:
            try:
                if uri in self._files:
                    sls_file = self._files[uri]
                    if sls_file.parsed_contents_stale:
                        sls_file.reparse()
                    return sls_file.parsed_contents
            except Exception as err:
                self.logger.error("Failed to parse YAML: %s", str(err))
                self.show_message(
                    "Failed parsing YAML: " + str(err),
                    msg_type=types.MessageType.Error,
                )
                return None
        return None

    def get_sls_file(self, uri: str) -> Optional[SlsFile]:
        if uri in self._files:
            return self._files[uri]
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
def did_open(salt_srv: SaltServer, params: types.DidOpenTextDocumentParams):
    """Text document did open notification."""
    salt_srv.register_file(params)


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
