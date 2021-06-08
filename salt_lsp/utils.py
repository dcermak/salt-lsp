"""
Utility functions to extract data from the files
"""

from __future__ import annotations

import os
import os.path
import shlex
import subprocess
from typing import Iterator, List, NewType, Optional, TypeVar, Union
from urllib.parse import urlparse, ParseResult

from pygls.lsp.types import Position, Range

import salt_lsp.parser as parser
from salt_lsp.parser import AstNode


def get_git_root(path: str) -> Optional[str]:
    """Get the root of the git repository to which `path` belongs.

    If git is not installed or `path` is not in a git repository, then `None`
    is returned.
    """
    res = subprocess.run(
        shlex.split("git rev-parse --show-toplevel"),
        cwd=os.path.dirname(path) if not os.path.isdir(path) else path,
        check=False,
        capture_output=True,
    )
    if res.returncode == 0:
        return str(res.stdout.strip(), encoding="utf-8")
    else:
        return None


def get_top(path: str) -> Optional[str]:
    if os.path.isdir(path):
        if os.path.isfile(os.path.join(path, "top.sls")):
            return path

    parent, tail = os.path.split(path)
    if (tail == "" and parent == "/") or not parent:
        return None
    if os.path.isfile(os.path.join(parent, "top.sls")):
        return parent
    return get_top(parent)


def get_root(path: str) -> str:
    root = get_top(path)
    return root or get_git_root(path)


def get_sls_includes(path: str) -> List[str]:
    sls_files = []
    top = get_root(path)
    for root, _, files in os.walk(top):
        base = root[len(top) + 1 :].replace(os.path.sep, ".")
        sls_files += [
            base + (file[:-4] if file != "init.sls" else "")
            for file in files
            if file.endswith(".sls")
        ]
    return sls_files


def construct_path_to_position(
    document: str, pos: Position
) -> List[parser.AstNode]:
    tree = parser.parse(document)
    found_node = None
    parser_pos = parser.Position(line=pos.line, col=pos.character)

    def visitor(node: parser.AstNode) -> bool:
        if parser_pos >= node.start and parser_pos < node.end:
            nonlocal found_node
            found_node = node
        return True

    tree.visit(visitor)

    if not found_node:
        return []

    context: List[parser.AstNode] = []
    node: Optional[parser.AstNode] = found_node
    while node:
        context.insert(0, node)
        node = node.parent
    return context


def position_to_index(text: str, line: int, column: int) -> int:
    split = text.splitlines(keepends=True)
    return sum([len(l) for i, l in enumerate(split) if i < line]) + column


T = TypeVar("T")


def get_last_element_of_iterator(iterator: Iterator[T]) -> Optional[T]:
    """
    Returns the last element of from an iterator or None if the iterator is
    empty.
    """
    try:
        *_, last = iterator
        return last
    except ValueError:
        # empty iterator
        return None


#: Type for URIs
Uri = NewType("Uri", str)


class FileUri:
    """Simple class for handling file:// URIs"""

    def __init__(self, uri: Union[str, Uri, FileUri]) -> None:
        self._parse_res: ParseResult = (
            uri._parse_res if isinstance(uri, FileUri) else urlparse(uri)
        )
        if self._parse_res.scheme != "" and self._parse_res.scheme != "file":
            raise ValueError(f"Invalid uri scheme {self._parse_res.scheme}")
        if self._parse_res.scheme == "":
            self._parse_res = urlparse("file://" + self._parse_res.path)

    @property
    def path(self) -> str:
        return self._parse_res.path

    def __str__(self) -> str:
        return self._parse_res.geturl()


def is_valid_file_uri(uri: str) -> bool:
    """Returns True if uri is a valid file:// URI"""
    try:
        FileUri(uri)
        return True
    except ValueError:
        return False


def ast_node_to_range(node: AstNode) -> Optional[Range]:
    """
    Converts a AstNode to a Range spanning from the node's starts to its end.

    If the node's start or end are None, then None is returned.
    """
    if node.start is None or node.end is None:
        return None
    return Range(start=node.start.to_lsp_pos(), end=node.end.to_lsp_pos())
