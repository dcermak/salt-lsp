"""
Module defining and building an AST from the SLS file.
"""

import yaml
from typing import Any, List

from pygls.lsp.types import (
    Position,
)


class AstNode:
    """
    Base class for all nodes of the Abstract Syntax Tree
    """
    start: Position = None
    end: Position = None


class IncludeNode(AstNode):
    value: str = None

    def get_file(self: IncludeNode, top_path: str) -> str:
        """
        Convert the dotted value of the include into a proper file path
        based on the path of the top of the states folder.

        :param top_path: the path to the top states folder
        """
        # TODO Implement me


class IncludesNode(AstNode):
    """
    Node representing the list of includes
    """
    includes: List(IncludeNode) = []


class StateParameterNode(AstNode):
    """
    Node representing a parameter of the state definition.
    """
    name: str = None
    value: Any = None


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
    parameters: List[StateParameterNode]


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
    state: StateCallNode = None


class ExtendNode(AstNode):
    """
    Node representing an ``extend`` declaration
    """
    states: List[StateNode] = []


class Tree(AstNode):
    """
    Node representing the whole SLS file
    """
    includes: IncludesNode = None
    extend: ExtendNode = None
    states: List[StateNode] = []


def parse(document: str) -> Tree:
    """
    Generate the Abstract Syntax Tree for a ``jinja|yaml`` rendered SLS file.
   
    :param document: the content of the SLS file to parse
    :return: the generated AST
    :raises ValueException: for any other renderer but ``jinja|yaml``
    """
    tree = Tree()

    tokens = yaml.scan(document)
    try:
        for token in tokens:
            if token.start_mark.line >= pos.line and token.start_mark.column >= pos.character:
                break

            # Block*StartToken: push a segment to the list
            if isinstance(token, (yaml.BlockMappingStartToken, yaml.BlockSequenceStartToken)):
                tokens_status.append(token)
                path.append(None)

            if isinstance(token, yaml.BlockSequenceStartToken):
                sequence_index = 0

            if isinstance(token, yaml.KeyToken):
                next_scalar_as_key = True

            if isinstance(token, yaml.ScalarToken):
                if next_scalar_as_key:
                    path.pop()
                    path.append(token.value)
                    next_scalar_as_key = False
                # TODO Handle the value cases

            # We want to count the BlockEntryToken to get the position of the item in the list
            if isinstance(token, yaml.BlockEntryToken):
                path.pop()
                path.append(sequence_index)
                sequence_index = sequence_index + 1

            # BlockEndToken, pop the last path segment if the position hasn't been reached yet
            if isinstance(token, yaml.BlockEndToken):
                tokens_status.pop()
    except yaml.scanner.ScannerError:
        # TODO We may want to check if the error occurs at the searched position
        return []
