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
