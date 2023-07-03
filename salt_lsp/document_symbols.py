"""
Implementation of the DocumentSymbolsRequest, see:
https://microsoft.github.io/language-server-protocol/specification#textDocument_documentSymbol
"""
from dataclasses import dataclass, field
import itertools
from typing import Callable, Dict, List, Sequence, TypedDict, cast

from lsprotocol import types

from salt_lsp.parser import (
    AstNode,
    Tree,
    Optional,
    IncludeNode,
    IncludesNode,
    StateParameterNode,
    StateCallNode,
    StateNode,
    RequisiteNode,
    RequisitesNode,
    ExtendNode,
)
from salt_lsp.base_types import CompletionsDict
from salt_lsp.utils import ast_node_to_range


class DocumentSymbolKWArgs(TypedDict):
    """
    Keyword arguments for the DocumentSymbol constructor that can be extracted
    for every AstNode.
    """

    name: str
    range: types.Range
    selection_range: types.Range
    kind: types.SymbolKind


#: Dictionary containing functions that convert the AstNode subclasses to their
#: string identifier
NODE_IDENTIFIERS: Dict[str, Callable[[AstNode], Optional[str]]] = {
    IncludeNode.__name__: lambda node: cast(IncludeNode, node).value,
    IncludesNode.__name__: lambda node: "includes",
    StateParameterNode.__name__: lambda node: cast(
        StateParameterNode, node
    ).name,
    StateCallNode.__name__: lambda node: cast(StateCallNode, node).name,
    StateNode.__name__: lambda node: cast(StateNode, node).identifier,
    RequisiteNode.__name__: lambda node: cast(RequisiteNode, node).module,
    RequisitesNode.__name__: lambda node: cast(RequisitesNode, node).kind,
    ExtendNode.__name__: lambda node: "extend",
}


def _get_doc_from_module_name(
    node: AstNode,
    state_completions: CompletionsDict,
) -> Optional[str]:
    """
    This function returns the documentation of a StateCallNode or a
    RequisiteNode from its name using the state_completions dictionary.

    This function must not be used for other types of AstNode subclasses.
    """
    assert isinstance(node, (RequisiteNode, StateCallNode))

    mod_name = NODE_IDENTIFIERS[type(node).__name__](node)
    if mod_name is None:
        return None

    if "." in mod_name:
        mod_base_name, submod_name = mod_name.split(".")
        completer = state_completions.get(mod_base_name)
        if completer is None:
            return None
        submod_params = completer.state_params.get(submod_name)
        return (
            submod_params.documentation if submod_params is not None else None
        )

    completer = state_completions.get(mod_name)
    return completer.state_docs if completer is not None else None


#: Dictionary of functions that return the documentation of a AstNode given the
#: AstNode and the CompletionsDict
DETAIL_OF_NODE_CONSTRUCTOR: Dict[
    str, Callable[[AstNode, CompletionsDict], Optional[str]]
] = {
    RequisiteNode.__name__: _get_doc_from_module_name,
    StateCallNode.__name__: _get_doc_from_module_name,
    ExtendNode.__name__: lambda n, c: """Extension of external SLS data.
See: https://docs.saltproject.io/en/latest/ref/states/extend.html
""",
    IncludesNode.__name__: lambda n, c: """A list of included SLS files.
See also https://docs.saltproject.io/en/latest/ref/states/include.html
""",
    RequisitesNode.__name__: lambda n, c: """List of requisites.
See also: https://docs.saltproject.io/en/latest/ref/states/requisites.html
""",
}


def get_children(
    node: AstNode, state_completions: CompletionsDict
) -> List[types.DocumentSymbol]:
    children: Sequence[AstNode] = []
    if isinstance(node, IncludesNode):
        children = node.includes
    elif isinstance(
        node, (ExtendNode, RequisitesNode, StateCallNode, StateNode)
    ):
        children = node.get_children()
    else:
        return []

    visitor = Visitor(state_completions=state_completions, recurse=False)
    for child in children:
        child.visit(visitor)

    assert isinstance(visitor.document_symbols, list)
    return visitor.document_symbols


def _document_symbol_init_kwargs(
    node: AstNode,
) -> Optional[DocumentSymbolKWArgs]:
    string_identifier = NODE_IDENTIFIERS.get(
        type(node).__name__, lambda node: None
    )(node)
    symbol_kind = (
        types.SymbolKind.String
        if isinstance(node, IncludeNode)
        else types.SymbolKind.Object
    )

    if string_identifier is None or node.start is None or node.end is None:
        return None

    lsp_range = ast_node_to_range(node)
    assert lsp_range is not None

    return {
        "name": string_identifier,
        "range": lsp_range,
        "selection_range": types.Range(
            start=node.start.to_lsp_pos(),
            end=types.Position(
                line=node.start.line,
                character=node.start.col + len(string_identifier),
            ),
        ),
        "kind": symbol_kind,
    }


@dataclass
class Visitor:
    """
    Stateful visitor that constructs the document symbols from a AstNode
    utilizing the visit() function.
    """

    #: The resulting document symbols created from the AstNode are saved in
    #: this field
    document_symbols: List[types.DocumentSymbol] = field(default_factory=list)

    #: The visitor uses this attribute to obtain the documentation of certain
    #: AstNodes.
    state_completions: CompletionsDict = field(default_factory=dict)

    #: This attribute specifies whether the visitor will be called on the
    #: children of the AstNode.
    #: By default this is not the case and should not be enabled, as LSP
    #: clients will not be able to use the resulting document symbols list.
    recurse: bool = False

    def __call__(self, node: AstNode) -> bool:
        kwargs = _document_symbol_init_kwargs(node)
        if kwargs is None:
            return self.recurse

        self.document_symbols.append(
            types.DocumentSymbol(
                detail=DETAIL_OF_NODE_CONSTRUCTOR.get(
                    type(node).__name__, lambda n, c: None
                )(node, self.state_completions)
                or "",
                children=get_children(node, self.state_completions),
                **kwargs,
            )
        )
        return self.recurse


def tree_to_document_symbols(
    tree: Tree, state_completions: CompletionsDict
) -> List[types.DocumentSymbol]:
    res = []

    for elem in itertools.chain.from_iterable(
        (
            ([tree.includes] if tree.includes else []),
            ([tree.extend] if tree.extend else []),
            tree.states,
        )
    ):
        visitor = Visitor(state_completions=state_completions, recurse=False)
        elem.visit(visitor)

        res += visitor.document_symbols

    return res
