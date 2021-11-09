"""
Module providing a fault-tolerant and simplified jinja2 parser
"""
from __future__ import annotations

from typing import List
from dataclasses import dataclass
import jinja2
import re

from salt_lsp.parser import Position


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
