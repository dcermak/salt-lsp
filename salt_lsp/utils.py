"""
Utility functions to extract data from the files
"""

from collections import OrderedDict
import os
import os.path
import subprocess
import shlex
from typing import Any, Union, Optional, List

from pygls.lsp.types import (
    Position,
)


def get_git_root(path: str) -> str:
    return str(
        subprocess.run(
            shlex.split("git rev-parse --show-toplevel"),
            cwd=os.path.dirname(path),
            check=True,
            capture_output=True,
        ).stdout,
        encoding="utf-8",
    )


def get_top(path: str) -> Optional[str]:
    parent = os.path.dirname(path)
    if not bool(parent):
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


def _construct_path_to_position(
    document: Any, pos: Position, cur_path: List[Union[str, int]]
) -> Optional[List[Union[str, int]]]:
    if not isinstance(document, OrderedDict) and not isinstance(document, list):
        return None

    entries = document if isinstance(document, list) else list(document.values())
    if len(entries) == 0:
        return cur_path

    match = entries[0] if hasattr(entries[0], "lc") else None
    match_ind = 0

    # Iterate over all entries in the document and find the first that is
    # beyond the given position. Store the entry *before* that one in match and
    # its index in match_index.
    # Special case: if we hit the exact line, then that is the match and not
    # the previous one
    for ind, entry in enumerate(entries):
        # entry can be a primitive type and will have no position information
        # then => have to skip over these for lack of better knowledge
        if hasattr(entry, "lc") and entry.lc.line >= pos.line:
            if entry.lc.line == pos.line:
                match, match_ind = entry, ind
            break
        match, match_ind = entry, ind

    # add the current node to the path list
    if isinstance(document, OrderedDict):
        cur_path.append(list(document.keys())[match_ind])
    elif isinstance(document, list):
        cur_path.append(match_ind)

    if isinstance(match, (list, OrderedDict)):
        return _construct_path_to_position(match, pos, cur_path)

    # we should have only primitive types now
    assert match is None or isinstance(match, (str, bool, int, float)), (
        "expected to reach a leaf node that must be a primitive type, "
        + f"but got a '{type(match)}' instead"
    )
    # if we are in a YAML list of primitive types (i.e. the last list entry is
    # the list index), then we will not be able to get the correct list index
    # as ruamel.yaml does not store the positions of primitive types
    if isinstance(cur_path[-1], int):
        cur_path.pop()
    return cur_path


def construct_path_to_position(document: Any, pos: Position) -> List[Union[str, int]]:
    if not isinstance(document, OrderedDict) and not isinstance(document, list):
        # oops, we cannot do a thing with this
        raise ValueError(
            f"Expected an ordered dictionary or a list, but got a {type(document)}"
        )

    return _construct_path_to_position(document, pos, []) or []


def position_to_index(text, line, column):
    split = text.splitlines(keepends=True)
    return sum([len(l) for i, l in enumerate(split) if i < line]) + column
