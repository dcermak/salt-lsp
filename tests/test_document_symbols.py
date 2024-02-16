from lsprotocol import types

from salt_lsp.document_symbols import tree_to_document_symbols
from salt_lsp.parser import parse


SLS_FILE = """include:
  - opensuse

saltmaster.packages:
  pkg.installed:
    - pkgs:
      - salt-master

git -C /srv/salt pull -q:
  cron.present:
    - user: root
    - minute: '*/5'

/srv/git/salt-states:
  file.symlink:
    - target: /srv/salt

touch /var/log:
  file: []
"""


TREE = parse(SLS_FILE)


def test_document_symbols(file_name_completer):
    doc_symbols = tree_to_document_symbols(TREE, file_name_completer)

    assert doc_symbols == [
        types.DocumentSymbol(
            name="includes",
            kind=types.SymbolKind.Object,
            range=types.Range(
                start=types.Position(line=0, character=0),
                end=types.Position(line=3, character=0),
            ),
            selection_range=types.Range(
                start=types.Position(line=0, character=0),
                end=types.Position(line=0, character=8),
            ),
            detail="""A list of included SLS files.
See also https://docs.saltproject.io/en/latest/ref/states/include.html
""",
            children=[
                types.DocumentSymbol(
                    name="opensuse",
                    kind=types.SymbolKind.String,
                    range=types.Range(
                        start=types.Position(line=1, character=2),
                        end=types.Position(line=1, character=12),
                    ),
                    selection_range=types.Range(
                        start=types.Position(line=1, character=2),
                        end=types.Position(line=1, character=10),
                    ),
                    detail="",
                    children=[],
                )
            ],
        ),
        types.DocumentSymbol(
            name="saltmaster.packages",
            kind=types.SymbolKind.Object,
            range=types.Range(
                start=types.Position(line=3, character=0),
                end=types.Position(line=8, character=0),
            ),
            selection_range=types.Range(
                start=types.Position(line=3, character=0),
                end=types.Position(line=3, character=19),
            ),
            detail="",
            children=[
                types.DocumentSymbol(
                    name="pkg.installed",
                    kind=types.SymbolKind.Object,
                    range=types.Range(
                        start=types.Position(line=4, character=2),
                        end=types.Position(line=8, character=0),
                    ),
                    selection_range=types.Range(
                        start=types.Position(line=4, character=2),
                        end=types.Position(line=4, character=15),
                    ),
                    detail="",
                    children=[
                        types.DocumentSymbol(
                            name="pkgs",
                            kind=types.SymbolKind.Object,
                            range=types.Range(
                                start=types.Position(line=5, character=4),
                                end=types.Position(line=8, character=0),
                            ),
                            selection_range=types.Range(
                                start=types.Position(line=5, character=4),
                                end=types.Position(line=5, character=8),
                            ),
                            detail="",
                            children=[],
                        )
                    ],
                )
            ],
        ),
        types.DocumentSymbol(
            name="git -C /srv/salt pull -q",
            kind=types.SymbolKind.Object,
            range=types.Range(
                start=types.Position(line=8, character=0),
                end=types.Position(line=13, character=0),
            ),
            selection_range=types.Range(
                start=types.Position(line=8, character=0),
                end=types.Position(line=8, character=24),
            ),
            detail="",
            children=[
                types.DocumentSymbol(
                    name="cron.present",
                    kind=types.SymbolKind.Object,
                    range=types.Range(
                        start=types.Position(line=9, character=2),
                        end=types.Position(line=13, character=0),
                    ),
                    selection_range=types.Range(
                        start=types.Position(line=9, character=2),
                        end=types.Position(line=9, character=14),
                    ),
                    detail="",
                    children=[
                        types.DocumentSymbol(
                            name="user",
                            kind=types.SymbolKind.Object,
                            range=types.Range(
                                start=types.Position(line=10, character=4),
                                end=types.Position(line=11, character=4),
                            ),
                            selection_range=types.Range(
                                start=types.Position(line=10, character=4),
                                end=types.Position(line=10, character=8),
                            ),
                            detail="",
                            children=[],
                        ),
                        types.DocumentSymbol(
                            name="minute",
                            kind=types.SymbolKind.Object,
                            range=types.Range(
                                start=types.Position(line=11, character=4),
                                end=types.Position(line=13, character=0),
                            ),
                            selection_range=types.Range(
                                start=types.Position(line=11, character=4),
                                end=types.Position(line=11, character=10),
                            ),
                            detail="",
                            children=[],
                        ),
                    ],
                )
            ],
        ),
        types.DocumentSymbol(
            name="/srv/git/salt-states",
            kind=types.SymbolKind.Object,
            range=types.Range(
                start=types.Position(line=13, character=0),
                end=types.Position(line=17, character=0),
            ),
            selection_range=types.Range(
                start=types.Position(line=13, character=0),
                end=types.Position(line=13, character=20),
            ),
            detail="",
            children=[
                types.DocumentSymbol(
                    name="file.symlink",
                    kind=types.SymbolKind.Object,
                    range=types.Range(
                        start=types.Position(line=14, character=2),
                        end=types.Position(line=17, character=0),
                    ),
                    selection_range=types.Range(
                        start=types.Position(line=14, character=2),
                        end=types.Position(line=14, character=14),
                    ),
                    detail="Just a dummy documentation of file.symlink",
                    children=[
                        types.DocumentSymbol(
                            name="target",
                            kind=types.SymbolKind.Object,
                            range=types.Range(
                                start=types.Position(line=15, character=4),
                                end=types.Position(line=17, character=0),
                            ),
                            selection_range=types.Range(
                                start=types.Position(line=15, character=4),
                                end=types.Position(line=15, character=10),
                            ),
                            detail="",
                            children=[],
                        )
                    ],
                )
            ],
        ),
        types.DocumentSymbol(
            name="touch /var/log",
            kind=types.SymbolKind.Object,
            range=types.Range(
                start=types.Position(line=17, character=0),
                end=types.Position(line=19, character=0),
            ),
            selection_range=types.Range(
                start=types.Position(line=17, character=0),
                end=types.Position(line=17, character=14),
            ),
            detail="",
            children=[
                types.DocumentSymbol(
                    name="file",
                    kind=types.SymbolKind.Object,
                    range=types.Range(
                        start=types.Position(line=18, character=2),
                        end=types.Position(line=18, character=10),
                    ),
                    selection_range=types.Range(
                        start=types.Position(line=18, character=2),
                        end=types.Position(line=18, character=6),
                    ),
                    detail="doc of file",
                    children=[],
                )
            ],
        ),
    ]
