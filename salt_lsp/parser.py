"""
Module defining and building an AST from the SLS file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import yaml
from os.path import abspath, dirname, exists, join
from typing import Any, List, Mapping, Optional


@dataclass
class Position:
    """
    Describes a position in the document
    """

    line: int
    col: int


@dataclass
class AstNode:
    """
    Base class for all nodes of the Abstract Syntax Tree
    """

    start: Optional[Position] = None
    end: Optional[Position] = None


class AstMapNode(AstNode):
    """
    Base class for all node that are mappings
    """

    def add_key(self: AstMapNode, key: str) -> AstNode:
        """
        Abstract function to add an item

        :param key: key of the item to add
        """
        raise NotImplementedError()


@dataclass
class IncludeNode(AstNode):
    value: Optional[str] = None

    def get_file(self: IncludeNode, top_path: str) -> Optional[str]:
        """
        Convert the dotted value of the include into a proper file path
        based on the path of the top of the states folder.

        :param top_path: the path to the top states folder
        """
        if self.value is None:
            return None

        top_path = dirname(abspath(top_path))
        dest = join(*self.value.split("."))
        init_sls_path = join(top_path, dest, "init.sls")
        entry_sls_path = join(top_path, f"{dest}.sls")
        if exists(init_sls_path):
            return init_sls_path
        if exists(entry_sls_path):
            return entry_sls_path
        return None


@dataclass
class IncludesNode(AstNode):
    """
    Node representing the list of includes
    """

    includes: List[IncludeNode] = field(default_factory=list)

    def add(self: IncludesNode) -> IncludeNode:
        self.includes.append(IncludeNode())
        return self.includes[-1]


@dataclass
class StateParameterNode(AstNode):
    """
    Node representing a parameter of the state definition.
    """

    name: Optional[str] = None
    value: Any = None


@dataclass
class RequisiteNode(AstNode):
    """
    Node reprensenting one requisite
    """

    module: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class RequisitesNode(AstMapNode):
    """
    Node Representing the list of requisites of a state
    """

    kind: Optional[str] = None
    requisites: List[RequisiteNode] = field(default_factory=list)

    def add_key(self: RequisitesNode, key: str) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.requisites.append(RequisiteNode(module=key))
        return self.requisites[-1]


@dataclass
class StateCallNode(AstMapNode):
    """
    Node representing the state call part of the state definition.
    For instance it represents the following part:

    .. code-block:: yaml

            file.managed:
              - name: /etc/libvirt/libvirtd.conf
              - source: salt://libvirt/libvirtd.conf

    from this complete state definition:

    .. code-block:: yaml

          libvirt_config:
            file.managed:
              - name: /etc/libvirt/libvirtd.conf
              - source: salt://libvirt/libvirtd.conf
    """

    name: Optional[str] = None
    parameters: List[StateParameterNode] = field(default_factory=list)
    requisites: List[RequisitesNode] = field(default_factory=list)

    def add_key(self: StateCallNode, key: str) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        requisites_keys = [
            "require",
            "onchanges",
            "watch",
            "listen",
            "prereq",
            "onfail",
            "use",
        ]
        all_requisites_keys = (
            requisites_keys
            + [k + "_any" for k in requisites_keys]
            + [k + "_in" for k in requisites_keys]
        )
        if key in all_requisites_keys:
            self.requisites.append(RequisitesNode(kind=key))
            return self.requisites[-1]

        self.parameters.append(StateParameterNode(name=key))
        return self.parameters[-1]


@dataclass
class StateNode(AstMapNode):
    """
    Node representing a state definition like the following.

    .. code-block:: yaml

          libvirt_config:
            file.managed:
              - name: /etc/libvirt/libvirtd.conf
              - source: salt://libvirt/libvirtd.conf
    """

    identifier: Optional[str] = None
    states: List[StateCallNode] = field(default_factory=list)

    def add_key(self: StateNode, key: str) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateCallNode(name=key))
        return self.states[-1]


@dataclass
class ExtendNode(AstMapNode):
    """
    Node representing an ``extend`` declaration
    """

    states: List[StateNode] = field(default_factory=list)

    def add_key(self: ExtendNode, key: str) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateNode(identifier=key))
        return self.states[-1]


@dataclass
class Tree(AstMapNode):
    """
    Node representing the whole SLS file
    """

    includes: Optional[IncludesNode] = None
    extend: Optional[ExtendNode] = None
    states: List[StateNode] = field(default_factory=list)

    def add_key(self: Tree, key: str) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        if key == "include":
            self.includes = IncludesNode()
            return self.includes

        if key == "extend":
            self.extend = ExtendNode()
            return self.extend

        self.states.append(StateNode(identifier=key))
        return self.states[-1]


@dataclass(init=False, eq=False)
class TokenNode(AstNode):
    token: yaml.Token = field(default_factory=lambda: yaml.Token(0, 0))

    def __init__(self: TokenNode, token: yaml.Token) -> None:
        super().__init__(
            start=Position(
                line=token.start_mark.line, col=token.start_mark.column
            ),
            end=Position(line=token.end_mark.line, col=token.end_mark.column),
        )
        self.token = token

    def __eq__(self, other):
        if not isinstance(other, TokenNode) or type(self.token) != type(
            other.token
        ):
            return False

        is_scalar = isinstance(self.token, yaml.ScalarToken)
        scalar_equal = is_scalar and self.token.value == other.token.value
        return super().__eq__(other) and (scalar_equal or not is_scalar)


def parse(document: str) -> Tree:
    """
    Generate the Abstract Syntax Tree for a ``jinja|yaml`` rendered SLS file.

    :param document: the content of the SLS file to parse
    :return: the generated AST
    :raises ValueException: for any other renderer but ``jinja|yaml``
    """
    tree = Tree()
    breadcrumbs: List[AstNode] = []
    next_scalar_as_key = False
    unprocessed_tokens: Optional[List[TokenNode]] = None
    last_start = None

    tokens = yaml.scan(document)
    try:
        for token in tokens:
            if isinstance(token, yaml.StreamStartToken):
                tree.start = Position(
                    line=token.start_mark.line, col=token.start_mark.column
                )
            if isinstance(token, yaml.StreamEndToken):
                tree.end = Position(
                    line=token.end_mark.line, col=token.end_mark.column
                )

            if isinstance(token, yaml.BlockMappingStartToken):
                if not breadcrumbs:
                    # Top level mapping block
                    breadcrumbs.append(tree)
                if not last_start:
                    last_start = Position(
                        line=token.start_mark.line, col=token.start_mark.column
                    )

            if isinstance(token, yaml.ValueToken) and isinstance(
                breadcrumbs[-1], StateParameterNode
            ):
                if not unprocessed_tokens:
                    unprocessed_tokens = []
                    # We don't need to do anything else with this token,
                    # just flag the next tokens to be simply collected
                    continue

            if unprocessed_tokens is not None:
                if not isinstance(
                    breadcrumbs[-1], StateParameterNode
                ) or not isinstance(token, yaml.BlockEndToken):
                    unprocessed_tokens.append(TokenNode(token=token))
                if isinstance(
                    token,
                    (
                        yaml.BlockMappingStartToken,
                        yaml.BlockSequenceStartToken,
                    ),
                ):
                    breadcrumbs.append(unprocessed_tokens[-1])

            if isinstance(token, yaml.BlockEndToken):
                last = breadcrumbs.pop()
                if not isinstance(last, TokenNode):
                    last.end = Position(
                        line=token.end_mark.line, col=token.end_mark.column
                    )
                if (
                    isinstance(last, StateParameterNode)
                    and unprocessed_tokens is not None
                ):
                    if len(unprocessed_tokens) == 1 and isinstance(
                        unprocessed_tokens[0].token, yaml.ScalarToken
                    ):
                        last.value = unprocessed_tokens[0].token.value
                    else:
                        last.value = unprocessed_tokens
                    unprocessed_tokens = None

            if unprocessed_tokens is not None:
                # If unprocessed_tokens is set then we don't have Salt-specific data token to process
                continue

            if isinstance(token, yaml.KeyToken):
                next_scalar_as_key = True

            if isinstance(token, yaml.BlockEntryToken):
                # Store the token for the parameter and requisite start position since those are dicts in lists
                if isinstance(
                    breadcrumbs[-1], (StateCallNode, RequisitesNode)
                ):
                    last_start = Position(
                        line=token.start_mark.line, col=token.start_mark.column
                    )
                if isinstance(breadcrumbs[-1], IncludesNode):
                    breadcrumbs.append(breadcrumbs[-1].add())
                    breadcrumbs[-1].start = Position(
                        line=token.start_mark.line, col=token.start_mark.column
                    )

            if isinstance(token, yaml.ScalarToken):
                if next_scalar_as_key and isinstance(
                    breadcrumbs[-1], AstMapNode
                ):
                    breadcrumbs.append(breadcrumbs[-1].add_key(token.value))
                    breadcrumbs[-1].start = last_start
                    last_start = None
                    next_scalar_as_key = False
                if isinstance(breadcrumbs[-1], IncludeNode):
                    breadcrumbs[-1].value = token.value
                    breadcrumbs[-1].end = Position(
                        line=token.end_mark.line, col=token.end_mark.column
                    )
                    breadcrumbs.pop()
                if isinstance(breadcrumbs[-1], RequisiteNode):
                    breadcrumbs[-1].reference = token.value
    except yaml.scanner.ScannerError:
        # TODO We may want to check if the error occurs at the searched position
        return tree
    return tree
