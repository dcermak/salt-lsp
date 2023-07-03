"""
Module defining and building an AST from the SLS file.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os.path import abspath, dirname, exists, isdir, join
from typing import Any, Callable, List, Optional, Sequence, Tuple, Union, cast

from lsprotocol import types
import yaml
from yaml.tokens import BlockEndToken, ScalarToken


log = logging.getLogger(__name__)


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

    def to_lsp_pos(self) -> types.Position:
        """Convert this position to pygls' native Position type."""
        return types.Position(line=self.line, character=self.col)


@dataclass
class AstNode(ABC):
    """
    Base class for all nodes of the Abstract Syntax Tree
    """

    start: Optional[Position] = None
    end: Optional[Position] = None
    parent: Optional[AstNode] = field(compare=False, default=None, repr=False)

    def visit(self: AstNode, visitor: Callable[[AstNode], bool]) -> None:
        """
        Apply a visitor function to the node and apply it on children if the
        function returns True.
        """
        visitor(self)


class AstMapNode(AstNode, ABC):
    """
    Base class for all nodes that are mappings
    """

    @abstractmethod
    def add(self: AstMapNode) -> AstNode:
        """
        Abstract function to add an item
        """
        raise NotImplementedError()

    @abstractmethod
    def get_children(self: AstMapNode) -> Sequence[AstNode]:
        """
        Returns all the children nodes
        """
        raise NotImplementedError()

    def visit(self, visitor: Callable[[AstNode], bool]) -> None:
        """
        Apply a visitor function to the node and apply it on children if the
        function returns True.
        """
        if visitor(self):
            for child in self.get_children():
                child.visit(visitor)


@dataclass
class IncludeNode(AstNode):
    """
    Represents an item in the includes node
    """

    value: Optional[str] = None

    def get_file(self: IncludeNode, top_path: str) -> Optional[str]:
        """
        Convert the dotted value of the include into a proper file path
        based on the path of the top of the states folder.

        :param top_path: the path to the top states folder
        """
        if self.value is None:
            return None

        top_path = (
            abs_top_path
            if isdir(abs_top_path := abspath(top_path))
            else dirname(abs_top_path)
        )

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
        """
        Add a child node and return it.
        """
        self.includes.append(IncludeNode())
        return self.includes[-1]


@dataclass
class StateParameterNode(AstNode):
    """
    Node representing a parameter of the state definition.
    """

    name: Optional[str] = None
    value: Any = None

    def set_key(self: StateParameterNode, key: str) -> AstNode:
        """
        Set the name of the parameter. If getting a requisites, tell the parent
        to handle it and return the newly created node.

        :return: the node that finally got the name
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
        if key in all_requisites_keys and isinstance(
            self.parent, StateCallNode
        ):
            return self.parent.convert(self, key)
        self.name = key
        return self


@dataclass
class RequisiteNode(AstNode):
    """
    Node representing one requisite
    """

    module: Optional[str] = None
    reference: Optional[str] = None

    def set_key(self: RequisiteNode, key: str) -> AstNode:
        """
        Set the module of the requisite

        :param key: the module to set
        :return: the node that was updated
        """
        self.module = key
        return self


@dataclass
class RequisitesNode(AstMapNode):
    """
    Node Representing the list of requisites of a state
    """

    kind: Optional[str] = None
    requisites: List[RequisiteNode] = field(default_factory=list)

    def set_key(self: RequisitesNode, key: str) -> AstNode:
        """
        Set the kind of the requisite

        :param key: the kind to set
        :return: the node that was updated
        """
        self.kind = key
        return self

    def add(self: RequisitesNode) -> AstNode:
        """
        Add a requisite entry to the tree, the key and value will come later

        :return: the added node
        """
        self.requisites.append(RequisiteNode(parent=self))
        return self.requisites[-1]

    def get_children(self: RequisitesNode) -> Sequence[AstNode]:
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

    def add(self: StateCallNode) -> AstNode:
        """
        Add an entry to the tree, the key and value will come later

        :return: the added node
        """
        self.parameters.append(StateParameterNode(parent=self))
        return self.parameters[-1]

    def set_key(self: StateCallNode, key: str) -> AstNode:
        """
        Set the name
        """
        self.name = key
        return self

    def convert(
        self: StateCallNode, param: StateParameterNode, name: str
    ) -> AstNode:
        """
        Convert a parameter entry to a requisite one
        """
        self.parameters.remove(param)
        self.requisites.append(RequisitesNode(kind=name, parent=self))
        self.requisites[-1].start = param.start
        return self.requisites[-1]

    def get_children(self: StateCallNode) -> Sequence[AstNode]:
        """
        Returns all the children nodes
        """
        return cast(List[AstNode], self.parameters) + cast(
            List[AstNode], self.requisites
        )


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

    def add(self: StateNode) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateCallNode(parent=self))
        return self.states[-1]

    def set_key(self: StateNode, key: str) -> AstNode:
        """
        Set the identifier of the node. If the ikey is one of include or
        extend, tell the parent to handle it.

        :return: the node where the key has been set.
        """
        if key in ["include", "extend"] and isinstance(self.parent, Tree):
            return self.parent.convert(self, key)
        self.identifier = key
        return self

    def get_children(self: StateNode) -> Sequence[AstNode]:
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

    def add(self: ExtendNode) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateNode(parent=self))
        return self.states[-1]

    def get_children(self: ExtendNode) -> Sequence[AstNode]:
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

    def add(self: Tree) -> AstNode:
        """
        Add a key token to the tree, the value will come later

        :return: the added node
        """
        self.states.append(StateNode(parent=self))
        return self.states[-1]

    def convert(self: Tree, state: StateNode, name: str) -> AstNode:
        """
        Convert a child state node into the proper node type depending on the
        name.

        :param state: the state node to change
        :param name: the name of the state node

        :return: the state node if no change was needed or the newly created
            node
        """
        self.states.remove(state)

        if name == "include":
            self.includes = IncludesNode(parent=self)
            self.includes.start = state.start
            return self.includes

        if name == "extend":
            self.extend = ExtendNode(parent=self)
            self.extend.start = state.start
            return self.extend
        return self

    def get_children(self: Tree) -> Sequence[AstNode]:
        """
        Returns all the children nodes
        """
        includes = [self.includes] if self.includes else []
        extend = [self.extend] if self.extend else []

        return (
            cast(List[AstNode], includes)
            + cast(List[AstNode], extend)
            + cast(List[AstNode], self.states)
        )


@dataclass(init=False, eq=False)
class TokenNode(AstNode):
    """
    Wrapper node for unprocessed yaml tokens
    """

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
        if not isinstance(other, TokenNode) or not isinstance(
            self.token, type(other.token)
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
        self._breadcrumbs: List[AstNode] = [self._tree]
        self._block_starts: List[
            Tuple[
                Union[
                    yaml.BlockMappingStartToken,
                    yaml.BlockSequenceStartToken,
                    yaml.FlowSequenceStartToken,
                    yaml.FlowMappingStartToken,
                ],
                AstNode,
            ],
        ] = []
        self._next_scalar_as_key = False
        #: flag for _process_token that the preceding token was a ValueToken
        #: => if applicable, the next token will be a value, unless a block is
        #:    started
        self._next_token_is_value = False
        self._unprocessed_tokens: Optional[List[TokenNode]] = None
        self._last_start: Optional[Position] = None

    def _process_token(self: Parser, token: yaml.Token) -> None:
        """
        Process one token
        """
        token_start = Position(
            line=token.start_mark.line, col=token.start_mark.column
        )
        token_end = Position(
            line=token.end_mark.line, col=token.end_mark.column
        )
        if isinstance(token, yaml.StreamStartToken):
            self._tree.start = token_start
        if isinstance(token, yaml.StreamEndToken):
            self._tree.end = token_end

        if isinstance(
            token,
            (
                yaml.BlockMappingStartToken,
                yaml.BlockSequenceStartToken,
                yaml.FlowSequenceStartToken,
                yaml.FlowMappingStartToken,
            ),
        ):
            # Store which block start corresponds to what breadcrumb to help
            # handling end block tokens
            self._block_starts.append((token, self._breadcrumbs[-1]))
            # a block is starting, so the next token cannot be a value, it will
            # be a complex type instead
            self._next_token_is_value = False

        if isinstance(token, yaml.ValueToken):
            self._next_token_is_value = True
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
                    yaml.FlowSequenceStartToken,
                    yaml.FlowMappingStartToken,
                ),
            ):
                self._breadcrumbs.append(self._unprocessed_tokens[-1])
                # a block is starting, so the next token cannot be a value, it
                # will be a complex type instead
                self._next_token_is_value = False

        if isinstance(
            token,
            (
                yaml.BlockEndToken,
                yaml.FlowSequenceEndToken,
                yaml.FlowMappingEndToken,
            ),
        ):
            if len(self._block_starts) == 0 or len(self._breadcrumbs) == 0:
                log.error(
                    "Reached a %s but either no block starts "
                    "(len(self._block_starts) = %d) or no breadcrumbs "
                    "(len(self._breadcrumbs) = %d) are present",
                    type(token).__name__,
                    len(self._block_starts),
                    len(self._breadcrumbs),
                )
                return
            last_start = self._block_starts.pop()
            last = self._breadcrumbs.pop()
            # pop breadcrumbs until we match the block starts
            closed = last
            while len(self._breadcrumbs) > 0 and closed != last_start[1]:
                closed = self._breadcrumbs.pop()
                closed.end = token_end
            if not isinstance(last, TokenNode):
                last.end = token_end
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
            # If self._unprocessed_tokens is set then we don't have
            # Salt-specific data token to process
            # reset the flag that the next token is a value, as the current
            # token has now been put into self._unprocessed_tokens and will be
            # taken care of in the next sweep
            self._next_token_is_value = False
            return

        if isinstance(token, yaml.KeyToken):
            self._next_scalar_as_key = True
            if isinstance(
                self._breadcrumbs[-1], AstMapNode
            ) and not isinstance(
                self._breadcrumbs[-1], (RequisiteNode, StateParameterNode)
            ):
                self._breadcrumbs.append(self._breadcrumbs[-1].add())
                if self._last_start:
                    self._breadcrumbs[-1].start = self._last_start
                    self._last_start = None
                else:
                    self._breadcrumbs[-1].start = token_start

        if isinstance(token, yaml.BlockEntryToken):
            # Create the state parameter, include and requisite before the dict
            # since those are dicts in lists
            same_level = (
                len(self._breadcrumbs) > 0
                and self._breadcrumbs[-1].start
                and self._breadcrumbs[-1].start.col == token.start_mark.column
            )
            if same_level:
                self._breadcrumbs.pop().end = token_start
            if isinstance(
                self._breadcrumbs[-1],
                (StateCallNode, IncludesNode, RequisitesNode),
            ):
                self._breadcrumbs.append(self._breadcrumbs[-1].add())
                self._breadcrumbs[-1].start = token_start

        if isinstance(token, yaml.ScalarToken):
            if self._next_scalar_as_key and getattr(
                self._breadcrumbs[-1], "set_key"
            ):
                changed = getattr(self._breadcrumbs[-1], "set_key")(
                    token.value
                )
                # If the changed node isn't the same than the one we called the
                # function on, that means that the node had to be converted and
                # we need to update the breadcrumbs too.
                if changed != self._breadcrumbs[-1]:
                    old = self._breadcrumbs.pop()
                    self._breadcrumbs.append(changed)
                    self._block_starts = [
                        (block[0], changed) if block[1] == old else block
                        for block in self._block_starts
                    ]

                self._next_scalar_as_key = False
            else:
                if isinstance(self._breadcrumbs[-1], IncludeNode):
                    self._breadcrumbs[-1].value = token.value
                    self._breadcrumbs[-1].end = token_end
                    self._breadcrumbs.pop()
                if isinstance(self._breadcrumbs[-1], RequisiteNode):
                    self._breadcrumbs[-1].reference = token.value
                # If the user hasn't typed the ':' yet, then the state
                # parameter will come as a scalar
                if (
                    isinstance(self._breadcrumbs[-1], StateParameterNode)
                    and self._breadcrumbs[-1].name is None
                ):
                    self._breadcrumbs[-1].name = token.value
                if isinstance(self._breadcrumbs[-1], (StateNode, Tree)):
                    new_node = self._breadcrumbs[-1].add()
                    new_node.start = token_start
                    new_node.end = token_end
                    if getattr(new_node, "set_key"):
                        getattr(new_node, "set_key")(token.value)

                    # this scalar token is actually the plain value of the
                    # previous key and "a new thing" starts with the next token
                    # => pop the current breadcrumb as it is now processed
                    if self._next_token_is_value:
                        last = self._breadcrumbs.pop()
                        if last.end is None:
                            last.end = token_end

            self._next_token_is_value = False

    def parse(self) -> Tree:
        """
        Generate the Abstract Syntax Tree for a ``jinja|yaml`` rendered SLS
        file.

        :return: the generated AST
        :raises ValueException: for any other renderer but ``jinja|yaml``
        """

        tokens = yaml.scan(self.document)
        token = None
        try:
            for token in tokens:
                log.debug(token)
                self._process_token(token)
        except yaml.scanner.ScannerError as err:
            log.debug(err)
            if token:
                # Properly close the opened blocks
                for node in reversed(self._breadcrumbs):
                    if (
                        node.start is not None
                        and err.context_mark is not None
                        and err.context_mark.column < node.start.col
                    ):
                        self._process_token(
                            BlockEndToken(
                                start_mark=err.context_mark,
                                end_mark=err.context_mark,
                            )
                        )
                    elif (
                        node.start is not None
                        and err.context_mark is not None
                        and err.context_mark.column == node.start.col
                    ):
                        self._process_token(
                            BlockEndToken(
                                start_mark=err.context_mark,
                                end_mark=err.context_mark,
                            )
                        )
                        if err.problem_mark is not None:
                            value = self.document[
                                err.context_mark.index : err.problem_mark.index
                            ].strip("\r\n")
                            error_token = ScalarToken(
                                value=value,
                                start_mark=err.context_mark,
                                end_mark=err.problem_mark,
                                plain=True,
                                style=None,
                            )
                            self._process_token(error_token)
                    elif err.problem_mark is not None:
                        node.end = Position(
                            line=err.problem_mark.line,
                            col=err.problem_mark.column,
                        )
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
