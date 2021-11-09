import salt_lsp.jinja_parser as jinja_parser
from salt_lsp.parser import Position


def test_tokenize():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: {{ pillar['user'] }}
{%- for group in pillar['groups']%}
    - group: {{ group }}
{% endfor -%}
"""
    assert jinja_parser.tokenize(content) == [
        jinja_parser.Token(
            Position(0, 0),
            Position(2, 12),
            "data",
            "/etc/systemd/system/rootco-salt-backup.service:\n  file.managed:\n    - user: ",
        ),
        jinja_parser.Token(
            Position(2, 12),
            Position(2, 32),
            "variable",
            "{{ pillar['user'] }}",
        ),
        jinja_parser.Token(Position(2, 32), Position(3, 0), "data", "\n"),
        jinja_parser.BlockToken(
            Position(3, 0),
            Position(3, 35),
            "for",
            "{%  for group in pillar['groups']%}",
        ),
        jinja_parser.Token(
            Position(3, 35), Position(4, 13), "data", "\n    - group: "
        ),
        jinja_parser.Token(
            Position(4, 13), Position(4, 24), "variable", "{{ group }}"
        ),
        jinja_parser.Token(Position(4, 24), Position(5, 0), "data", "\n"),
        jinja_parser.BlockToken(
            Position(5, 0), Position(5, 13), "endfor", "{% endfor  %}"
        ),
        jinja_parser.Token(Position(5, 13), Position(6, 0), "data", "\n"),
    ]


def test_parse():
    tokens = [
        jinja_parser.Token(
            Position(0, 0),
            Position(2, 12),
            "data",
            "/etc/systemd/system/rootco-salt-backup.service:\n  file.managed:\n    - user: ",
        ),
        jinja_parser.Token(
            Position(2, 12),
            Position(2, 32),
            "variable",
            "{{ pillar['user'] }}",
        ),
        jinja_parser.Token(Position(2, 32), Position(3, 0), "data", "\n"),
        jinja_parser.BlockToken(
            Position(3, 0),
            Position(3, 34),
            "for",
            "{% for group in pillar['groups']%}",
        ),
        jinja_parser.Token(
            Position(3, 34), Position(4, 13), "data", "\n    - group: "
        ),
        jinja_parser.Token(
            Position(4, 13), Position(4, 24), "variable", "{{ group }}"
        ),
        jinja_parser.Token(Position(4, 24), Position(5, 0), "data", "\n"),
        jinja_parser.BlockToken(
            Position(5, 0), Position(5, 12), "endfor", "{% endfor %}"
        ),
    ]

    tree = jinja_parser.BranchNode(
        start=Position(0, 0),
        end=Position(5, 12),
        body=[
            jinja_parser.DataNode(
                start=Position(0, 0),
                end=Position(2, 12),
                data="/etc/systemd/system/rootco-salt-backup.service:\n  file.managed:\n    - user: ",
            ),
            jinja_parser.VariableNode(
                start=Position(2, 12),
                end=Position(2, 32),
                expression="{{ pillar['user'] }}",
            ),
            jinja_parser.DataNode(
                start=Position(2, 32), end=Position(3, 0), data="\n"
            ),
            jinja_parser.BlockNode(
                start=Position(3, 0),
                end=Position(5, 12),
                block_end_start=Position(5, 0),
                kind="for",
                branches=[
                    jinja_parser.BranchNode(
                        start=Position(3, 0),
                        end=Position(5, 0),
                        expression_end=Position(3, 34),
                        expression="{% for group in pillar['groups']%}",
                        body=[
                            jinja_parser.DataNode(
                                start=Position(3, 34),
                                end=Position(4, 13),
                                data="\n    - group: ",
                            ),
                            jinja_parser.VariableNode(
                                start=Position(4, 13),
                                end=Position(4, 24),
                                expression="{{ group }}",
                            ),
                            jinja_parser.DataNode(
                                start=Position(4, 24),
                                end=Position(5, 0),
                                data="\n",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    assert jinja_parser.parse(tokens) == tree


def test_parse_unfinished_blocks():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
{% if pillar['user']|length() > 1 %}
    - user: {{ pillar['user'] }}
{% elif pillar['user']|length() == 1 %}
    - user: bar
{% else %}
    - user: foo
{% for group in pillar['groups']%}
    - group: {{ group }}
{%- else %}
    - group: nobody
"""

    tree = jinja_parser.BranchNode(
        start=Position(0, 0),
        end=Position(12, 0),
        body=[
            jinja_parser.DataNode(
                start=Position(0, 0),
                end=Position(2, 0),
                data="/etc/systemd/system/rootco-salt-backup.service:\n  file.managed:\n",
            ),
            jinja_parser.BlockNode(
                start=Position(2, 0),
                end=Position(12, 0),
                block_end_start=Position(12, 0),
                kind="if",
                branches=[
                    jinja_parser.BranchNode(
                        start=Position(2, 0),
                        end=Position(4, 0),
                        expression_end=Position(2, 36),
                        expression="{% if pillar['user']|length() > 1 %}",
                        body=[
                            jinja_parser.DataNode(
                                start=Position(2, 36),
                                end=Position(3, 12),
                                data="\n    - user: ",
                            ),
                            jinja_parser.VariableNode(
                                start=Position(3, 12),
                                end=Position(3, 32),
                                expression="{{ pillar['user'] }}",
                            ),
                            jinja_parser.DataNode(start=Position(3, 32), end=Position(4, 0), data="\n"),
                        ],
                    ),
                    jinja_parser.BranchNode(
                        start=Position(4, 0),
                        end=Position(6, 0),
                        expression_end=Position(4, 39),
                        expression="{% elif pillar['user']|length() == 1 %}",
                        body=[
                            jinja_parser.DataNode(
                                start=Position(4, 39),
                                end=Position(6, 0),
                                data="\n    - user: bar\n",
                            ),
                        ],
                    ),
                    jinja_parser.BranchNode(
                        start=Position(6, 0),
                        end=Position(12, 0),
                        expression_end=Position(6, 10),
                        expression="{% else %}",
                        body=[
                            jinja_parser.DataNode(
                                start=Position(6, 10),
                                end=Position(8, 0),
                                data="\n    - user: foo\n",
                            ),
                            jinja_parser.BlockNode(
                                start=Position(8, 0),
                                end=Position(12, 0),
                                block_end_start=Position(12, 0),
                                kind="for",
                                branches=[
                                    jinja_parser.BranchNode(
                                        start=Position(8, 0),
                                        end=Position(10, 0),
                                        expression_end=Position(8, 34),
                                        expression="{% for group in pillar['groups']%}",
                                        body=[
                                            jinja_parser.DataNode(
                                                start=Position(8, 34),
                                                end=Position(9, 13),
                                                data="\n    - group: ",
                                            ),
                                            jinja_parser.VariableNode(
                                                start=Position(9, 13),
                                                end=Position(9, 24),
                                                expression="{{ group }}",
                                            ),
                                            jinja_parser.DataNode(
                                                start=Position(9, 24),
                                                end=Position(10, 0),
                                                data="\n",
                                            ),
                                        ],
                                    ),
                                    jinja_parser.BranchNode(
                                        start=Position(10, 0),
                                        end=Position(12, 0),
                                        expression_end=Position(10, 11),
                                        expression="{%  else %}",
                                        body=[
                                            jinja_parser.DataNode(
                                                start=Position(10, 11),
                                                end=Position(12, 0),
                                                data="\n    - group: nobody\n",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    tokens = jinja_parser.tokenize(content)
    assert jinja_parser.parse(tokens) == tree
