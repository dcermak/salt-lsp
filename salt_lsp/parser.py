"""
Module defining and building an AST from the SLS file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import yaml
from typing import Any, List, Mapping


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

    start: Position = None
    end: Position = None


@dataclass
class IncludeNode(AstNode):
    value: str = None

    def get_file(self: IncludeNode, top_path: str) -> str:
        """
        Convert the dotted value of the include into a proper file path
        based on the path of the top of the states folder.

        :param top_path: the path to the top states folder
        """
        # TODO Implement me


@dataclass
class IncludesNode(AstNode):
    """
    Node representing the list of includes
    """

    includes: List(IncludeNode) = field(default_factory=list)

    def add(self: IncludesNode) -> IncludeNode:
        self.includes.append(IncludeNode())
        return self.includes[-1]


@dataclass
class StateParameterNode(AstNode):
    """
    Node representing a parameter of the state definition.
    """

    name: str = None
    value: Any = None


@dataclass
class RequisiteNode(AstNode):
    """
    Node reprensenting one requisite
    """

    module: str = None
    reference: str = None


@dataclass
class RequisitesNode(AstNode):
    """
    Node Representing the list of requisites of a state
    """
    kind: str = None
    requisites: List(RequisiteNode) = field(default_factory=list)


    def add_key(self: StateCallNode, key: str) -> None:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.requisites.append(RequisiteNode(module=key))
        return self.requisites[-1]


@dataclass
class StateCallNode(AstNode):
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

    name: str = None
    parameters: List[StateParameterNode] = field(default_factory=list)
    requisites: List[RequisitesNode] = field(default_factory=list)

    def add_key(self: StateCallNode, key: str) -> None:
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
class StateNode(AstNode):
    """
    Node representing a state definition like the following.

    .. code-block:: yaml

          libvirt_config:
            file.managed:
              - name: /etc/libvirt/libvirtd.conf
              - source: salt://libvirt/libvirtd.conf
    """

    identifier: str = None
    states: List[StateCallNode] = field(default_factory=list)

    def add_key(self: StateNode, key: str) -> None:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateCallNode(name=key))
        return self.states[-1]


@dataclass
class ExtendNode(AstNode):
    """
    Node representing an ``extend`` declaration
    """

    states: List[StateNode] = field(default_factory=list)

    def add_key(self: ExtendNode, key: str) -> None:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateNode(identifier=key))
        return self.states[-1]


@dataclass
class Tree(AstNode):
    """
    Node representing the whole SLS file
    """

    includes: IncludesNode = None
    extend: ExtendNode = None
    states: List[StateNode] = field(default_factory=list)

    def add_key(self: Tree, key: str) -> None:
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
    token: yaml.Token = None

    def __init__(self: TokenNode, token: yaml.Token = None):
        super().__init__(
            start=Position(line=token.start_mark.line, col=token.start_mark.column),
            end=Position(line=token.end_mark.line, col=token.end_mark.column),
        )
        self.token = token

    def __eq__(self, other):
        if not isinstance(other, TokenNode) or type(self.token) != type(other.token):
            return False

        scalar_equal = self.is_scalar() and self.token.value == other.token.value
        return super().__eq__(other) and (scalar_equal or not self.is_scalar())

    def is_scalar(self):
        """
        :return: whether the token is a scalar one
        """
        return isinstance(self.token, yaml.ScalarToken)


def parse(document: str) -> Tree:
    """
    Generate the Abstract Syntax Tree for a ``jinja|yaml`` rendered SLS file.

    :param document: the content of the SLS file to parse
    :return: the generated AST
    :raises ValueException: for any other renderer but ``jinja|yaml``
    """
    tree = Tree()
    breadcrumbs = []
    next_scalar_as_key = False
    unprocessed_tokens = None

    tokens = yaml.scan(document)
    try:
        for token in tokens:
            if isinstance(token, yaml.BlockMappingStartToken):
                if not breadcrumbs:
                    # Top level mapping block
                    breadcrumbs.append(tree)

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
                    token, (yaml.BlockMappingStartToken, yaml.BlockSequenceStartToken)
                ):
                    breadcrumbs.append(unprocessed_tokens[-1])

            if isinstance(token, yaml.BlockEndToken):
                last = breadcrumbs.pop()
                if isinstance(last, StateParameterNode):
                    if (
                        len(unprocessed_tokens) == 1
                        and unprocessed_tokens[0].is_scalar()
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
                # TODO Store the token for the parameter start position
                if isinstance(breadcrumbs[-1], IncludesNode):
                    breadcrumbs.append(breadcrumbs[-1].add())

            if isinstance(token, yaml.ScalarToken):
                if next_scalar_as_key:
                    breadcrumbs.append(breadcrumbs[-1].add_key(token.value))
                    next_scalar_as_key = False
                if isinstance(breadcrumbs[-1], IncludeNode):
                    breadcrumbs.pop().value = token.value
                if isinstance(breadcrumbs[-1], RequisiteNode):
                    breadcrumbs[-1].reference = token.value
    except yaml.scanner.ScannerError:
        # TODO We may want to check if the error occurs at the searched position
        return []
    return tree
