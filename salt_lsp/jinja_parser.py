"""
Module providing a fault-tolerant and simplified jinja2 parser
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence
import jinja2
import logging
import re

from salt_lsp.parser import Position, AstNode, AstMapNode

log = logging.getLogger(__name__)


@dataclass
class Token:
    start: Position
    end: Position
    token_type: str
    data: str


@dataclass(init=False)
class BlockToken(Token):
    """
    Token representing a block with its kind (if, else, for, endif...)
    """

    kind: str

    def __init__(self, start: Position, end: Position, kind: str, data: str):
        """
        Construct a new block token
        """
        super().__init__(start, end, "block", data)
        self.kind = kind


def tokenize(document: str) -> List[Token]:
    """
    Convert the Jinja document into tokens
    """
    pos = 0
    tokens = []

    # Get the tokens from jinja's lexer and enrich them with column data
    jinja_env = jinja2.Environment()
    jinja_env.keep_trailing_newline = True
    # Jinja strips the whitespaces in the lexer... so we need to remove those controls
    no_whitespace_control = re.sub(
        "-+%}", " %}", re.sub("{%[-+]", "{% ", document)
    )
    for token in jinja_env.lex(no_whitespace_control):
        start_pos = Position(token[0] - 1, pos)
        lines = token[2].split("\n")
        pos = len(lines[-1]) if len(lines) > 1 else pos + len(lines[0])
        end_pos = Position(start_pos.line + len(lines) - 1, pos)
        tokens.append(Token(start_pos, end_pos, token[1], token[2]))

    # Simplify the jinja tokens to ease merging with YAML later
    # The block and variable tokens are merged together.
    new_tokens = []
    to_aggregate = None
    for token in tokens:
        if to_aggregate is not None:
            if token.token_type not in ["variable_end", "block_end"]:
                to_aggregate.append(token)
            else:
                to_aggregate.append(token)
                start = to_aggregate[0].start
                end = to_aggregate[-1].end
                data = "".join([t.data for t in to_aggregate])
                if token.token_type == "block_end":
                    kind = "unknown"
                    for aggregated in to_aggregate:
                        if aggregated.token_type == "name":
                            kind = aggregated.data
                            break
                    new_token = BlockToken(start, end, kind, data)
                else:
                    new_token = Token(
                        start,
                        end,
                        to_aggregate[0].token_type[0 : -(len("_begin"))],
                        data,
                    )
                new_tokens.append(new_token)
                to_aggregate = None
            continue

        if token.token_type in ["variable_begin", "block_begin"]:
            to_aggregate = [token]
            continue

        new_tokens.append(token)

    return new_tokens


@dataclass
class VariableNode(AstNode):
    """
    Node representing a Jinja variable block
    """

    expression: Optional[str] = None


@dataclass
class BlockNode(AstMapNode):
    """
    Node representing a Jinja block with multiple code branches like 'for' or 'if'
    """

    kind: Optional[str] = None
    branches: List[BranchNode] = field(default_factory=list)
    block_end_start: Optional[Position] = None

    @staticmethod
    def from_token(token: BlockToken) -> BlockNode:
        node = BlockNode()
        node.start = token.start
        node.kind = token.kind

        # Create the default branch
        node.branches = [BranchNode.from_token(token)]
        return node

    def get_children(self: BlockNode) -> Sequence[AstMapNode]:
        return self.branches

    def add(self: BlockNode, child: BranchNode) -> BranchNode:
        assert isinstance(child, BranchNode)
        self.branches.append(child)
        child.parent = self
        return self.branches[-1]

    def close(self: BlockNode, end_token: Optional[Token] = None):
        """
        Update the end position using the children
        """
        if end_token:
            self.block_end_start = end_token.start
            self.end = end_token.end
        elif len(self.branches) > 0:
            self.end = self.branches[-1].end
            self.block_end_start = self.end
        else:
            self.end = self.start
            self.block_end_start = self.end


@dataclass
class DataNode(AstNode):
    """
    Node representing raw text with no jinja syntax inside
    """

    data: Optional[str] = None


@dataclass
class BranchNode(AstMapNode):
    """
    Node representing on code path in a block like an 'if' or an 'else' branch but also 'for'.
    """

    expression: Optional[str] = None
    expression_end: Optional[Position] = None
    body: List[AstNode] = field(default_factory=list)

    @staticmethod
    def from_token(start_token: Token) -> BranchNode:
        node = BranchNode()
        node.start = start_token.start
        node.expression = start_token.data
        node.expression_end = start_token.end
        return node

    def get_children(self: BranchNode) -> Sequence[AstNode]:
        return self.body

    def add(self: BranchNode, child: AstNode) -> AstNode:
        assert child is not None
        self.body.append(child)
        child.parent = self
        return self.body[-1]

    def close(self: BranchNode):
        """
        Update the end position using the children
        """
        if len(self.body) > 0:
            self.end = self.body[-1].end
        elif self.expression_end:
            self.end = self.expression_end
        else:
            self.end = self.start


def parse(tokens: List[Token]) -> AstNode:
    """
    Parse Jinja tokens into a tree structure
    """
    tree = BranchNode(start=Position(0, 0))
    breadcrumbs: List[AstMapNode] = [tree]
    for token in tokens:
        if isinstance(token, BlockToken):
            if token.kind in ["if", "for"]:
                # Opening a block with a default branch
                block = BlockNode.from_token(token)
                breadcrumbs[-1].add(block)
                breadcrumbs += [block, block.get_children()[0]]

            elif token.kind in ["endif", "endfor", "else", "elif"]:
                # TODO If we don't have a matching opened block?
                if len(breadcrumbs) > 1:
                    current_node = breadcrumbs[-1]
                    if isinstance(current_node, BranchNode):
                        current_node.close()
                        breadcrumbs.pop()

                    if token.kind in ["else", "elif"]:
                        # Open a new branch
                        branch = BranchNode.from_token(token)
                        breadcrumbs[-1].add(branch)
                        breadcrumbs.append(branch)

                    if token.kind in ["endfor", "endif"]:
                        # end*: close the block as well
                        if len(breadcrumbs) > 1:
                            current_node = breadcrumbs[-1]
                            if isinstance(current_node, BlockNode):
                                if (
                                    "end" + str(current_node.kind)
                                    == token.kind
                                ):
                                    current_node.close(token)
                                    breadcrumbs.pop()
        else:
            if token.token_type == "data":
                breadcrumbs[-1].add(
                    DataNode(start=token.start, end=token.end, data=token.data)
                )
            elif token.token_type == "variable":
                breadcrumbs[-1].add(
                    VariableNode(
                        start=token.start, end=token.end, expression=token.data
                    )
                )
            else:
                log.warning("Unhandled Jinja token: " + str(token))

    # Close unmatched blocks
    for node in reversed(breadcrumbs):
        if isinstance(node, (BlockNode, BranchNode)):
            node.close()

    return tree
