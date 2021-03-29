"""
Module defining and building an AST from the SLS file.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import yaml
from os.path import abspath, dirname, exists, join
from typing import Any, Callable, List, Mapping, Optional


@dataclass
class Position:
    """
    Describes a position in the document
    """

    line: int
    col: int

    def __lt__(self, other):
        if not isinstance(other, Position):
            return NotImplemented
        return (
            self.line < other.line
            or self.line == other.line
            and self.col < other.col
        )

    def __gt__(self, other):
        if not isinstance(other, Position):
            return NotImplemented
        return (
            self.line > other.line
            or self.line == other.line
            and self.col > other.col
        )

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other


@dataclass
class AstNode:
    """
    Base class for all nodes of the Abstract Syntax Tree
    """

    start: Optional[Position] = None
    end: Optional[Position] = None
    parent: Optional[AstNode] = field(compare=False, default=None)

    def visit(self: AstNode, visitor: Callable[[AstNode, bool]]) -> None:
        """
        Apply a visitor function to the node and apply it on children if the function returns True.
        """
        visitor(self)


class AstMapNode(AstNode, ABC):
    """
    Base class for all nodes that are mappings
    """

    @abstractmethod
    def add_key(self: AstMapNode, key: str) -> AstNode:
        """
        Abstract function to add an item

        :param key: key of the item to add
        """
        raise NotImplementedError()

    def get_children(self: AstMapNode) -> List[AstNode]:
        """
        Returns all the children nodes
        """
        raise NotImplementedError()

    def visit(self: AstNode, visitor: Callable[[AstNode, bool]]) -> None:
        """
        Apply a visitor function to the node and apply it on children if the function returns True.
        """
        if visitor(self):
            for child in self.get_children():
                child.visit(visitor)


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
        self.requisites.append(RequisiteNode(module=key, parent=self))
        return self.requisites[-1]

    def get_children(self: AstMapNode) -> List[AstNode]:
        """
        Returns all the children nodes
        """
        return self.requisites


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
            self.requisites.append(RequisitesNode(kind=key, parent=self))
            return self.requisites[-1]

        self.parameters.append(StateParameterNode(name=key, parent=self))
        return self.parameters[-1]

    def get_children(self: AstMapNode) -> List[AstNode]:
        """
        Returns all the children nodes
        """
        return self.parameters + self.requisites


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
        self.states.append(StateCallNode(name=key, parent=self))
        return self.states[-1]

    def get_children(self: AstMapNode) -> List[AstNode]:
        """
        Returns all the children nodes
        """
        return self.states


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
        self.states.append(StateNode(identifier=key, parent=self))
        return self.states[-1]

    def get_children(self: AstMapNode) -> List[AstNode]:
        """
        Returns all the children nodes
        """
        return self.states


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
            self.includes = IncludesNode(parent=self)
            return self.includes

        if key == "extend":
            self.extend = ExtendNode(parent=self)
            return self.extend

        self.states.append(StateNode(identifier=key, parent=self))
        return self.states[-1]

    def get_children(self: AstMapNode) -> List[AstNode]:
        """
        Returns all the children nodes
        """
        return self.includes + [self.extend] + self.states


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


class Parser:
    """
    SLS file parser class
    """

    def __init__(self: Parser, document: str) -> None:
        """
        Create a parser object for an SLS file.

        :param document: the content of the SLS file to parse
        """
        self.document = document
        self._tree = Tree()
        self._breadcrumbs: List[AstNode] = []
        self._next_scalar_as_key = False
        self._unprocessed_tokens: Optional[List[TokenNode]] = None
        self._last_start: Optional[Position] = None

    def _process_token(self: Parser, token: yaml.Token) -> None:
        """
        Process one token
        """
        if isinstance(token, yaml.StreamStartToken):
            self._tree.start = Position(
                line=token.start_mark.line, col=token.start_mark.column
            )
        if isinstance(token, yaml.StreamEndToken):
            self._tree.end = Position(
                line=token.end_mark.line, col=token.end_mark.column
            )

        if isinstance(token, yaml.BlockMappingStartToken):
            if not self._breadcrumbs:
                # Top level mapping block
                self._breadcrumbs.append(self._tree)
            if not self._last_start:
                self._last_start = Position(
                    line=token.start_mark.line, col=token.start_mark.column
                )

        if isinstance(token, yaml.ValueToken) and isinstance(
            self._breadcrumbs[-1], StateParameterNode
        ):
            if not self._unprocessed_tokens:
                self._unprocessed_tokens = []
                # We don't need to do anything else with this token,
                # just flag the next tokens to be simply collected
                return

        if self._unprocessed_tokens is not None:
            if not isinstance(
                self._breadcrumbs[-1], StateParameterNode
            ) or not isinstance(token, yaml.BlockEndToken):
                self._unprocessed_tokens.append(TokenNode(token=token))
            if isinstance(
                token,
                (
                    yaml.BlockMappingStartToken,
                    yaml.BlockSequenceStartToken,
                ),
            ):
                self._breadcrumbs.append(self._unprocessed_tokens[-1])

        if isinstance(token, yaml.BlockEndToken):
            last = self._breadcrumbs.pop()
            if not isinstance(last, TokenNode):
                last.end = Position(
                    line=token.end_mark.line, col=token.end_mark.column
                )
            if (
                isinstance(last, StateParameterNode)
                and self._unprocessed_tokens is not None
            ):
                if len(self._unprocessed_tokens) == 1 and isinstance(
                    self._unprocessed_tokens[0].token, yaml.ScalarToken
                ):
                    last.value = self._unprocessed_tokens[0].token.value
                else:
                    for unprocessed in self._unprocessed_tokens:
                        unprocessed.parent = last
                    last.value = self._unprocessed_tokens
                self._unprocessed_tokens = None

        if self._unprocessed_tokens is not None:
            # If self._unprocessed_tokens is set then we don't have Salt-specific data token to process
            return

        if isinstance(token, yaml.KeyToken):
            self._next_scalar_as_key = True

        if isinstance(token, yaml.BlockEntryToken):
            # Store the token for the parameter and requisite start position since those are dicts in lists
            if isinstance(
                self._breadcrumbs[-1], (StateCallNode, RequisitesNode)
            ):
                self._last_start = Position(
                    line=token.start_mark.line, col=token.start_mark.column
                )
            if isinstance(self._breadcrumbs[-1], IncludesNode):
                self._breadcrumbs.append(self._breadcrumbs[-1].add())
                self._breadcrumbs[-1].start = Position(
                    line=token.start_mark.line, col=token.start_mark.column
                )

        if isinstance(token, yaml.ScalarToken):
            if self._next_scalar_as_key and isinstance(
                self._breadcrumbs[-1], AstMapNode
            ):
                self._breadcrumbs.append(
                    self._breadcrumbs[-1].add_key(token.value)
                )
                self._breadcrumbs[-1].start = self._last_start
                self._last_start = None
                self._next_scalar_as_key = False
            if isinstance(self._breadcrumbs[-1], IncludeNode):
                self._breadcrumbs[-1].value = token.value
                self._breadcrumbs[-1].end = Position(
                    line=token.end_mark.line, col=token.end_mark.column
                )
                self._breadcrumbs.pop()
            if isinstance(self._breadcrumbs[-1], RequisiteNode):
                self._breadcrumbs[-1].reference = token.value

    def parse(self) -> Tree:
        """
        Generate the Abstract Syntax Tree for a ``jinja|yaml`` rendered SLS file.

        :return: the generated AST
        :raises ValueException: for any other renderer but ``jinja|yaml``
        """

        tokens = yaml.scan(self.document)
        try:
            for token in tokens:
                self._process_token(token)
        except yaml.scanner.ScannerError:
            # TODO We may want to check if the error occurs at the searched position
            return self._tree
        return self._tree


def parse(document: str) -> Tree:
    """
    Generate the Abstract Syntax Tree for a ``jinja|yaml`` rendered SLS file.

    :param document: the content of the SLS file to parse
    :return: the generated AST
    :raises ValueException: for any other renderer but ``jinja|yaml``
    """
    return Parser(document).parse()
