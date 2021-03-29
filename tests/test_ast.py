import yaml

from salt_lsp.parser import *
from typing import Callable


class TestIncludeNode:
    def test_get_file_with_no_value(self):
        assert IncludeNode(value=None).get_file("") is None

    def test_get_file_from_init_sls(self, fs):
        fs.create_file("/repo/root/foo/init.sls")
        assert (
            IncludeNode(value="foo").get_file("/repo/root/top.sls")
            == "/repo/root/foo/init.sls"
        )

    def test_get_file_from_foo_sls(self, fs):
        fs.create_file("/repo/root/foo.sls")
        assert (
            IncludeNode(value="foo").get_file("/repo/root/top.sls")
            == "/repo/root/foo.sls"
        )

    def test_get_file_when_sls_not_present(self):
        assert IncludeNode(value="foo").get_file("/repo/root/top.sls") is None


def test_includes():
    content = """include:
  - foo.bar
  - web
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=3, col=0),
        includes=IncludesNode(
            start=Position(line=0, col=0),
            end=Position(line=3, col=0),
            includes=[
                IncludeNode(
                    start=Position(line=1, col=2),
                    end=Position(line=1, col=11),
                    value="foo.bar",
                ),
                IncludeNode(
                    start=Position(line=2, col=2),
                    end=Position(line=2, col=7),
                    value="web",
                ),
            ],
        ),
    )


def test_simple_state():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: root
    - group: root
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=4, col=0),
        states=[
            StateNode(
                start=Position(line=0, col=0),
                end=Position(line=4, col=0),
                identifier="/etc/systemd/system/rootco-salt-backup.service",
                states=[
                    StateCallNode(
                        start=Position(line=1, col=2),
                        end=Position(line=4, col=0),
                        name="file.managed",
                        parameters=[
                            StateParameterNode(
                                start=Position(line=2, col=4),
                                end=Position(line=3, col=4),
                                name="user",
                                value="root",
                            ),
                            StateParameterNode(
                                start=Position(line=3, col=4),
                                end=Position(line=4, col=0),
                                name="group",
                                value="root",
                            ),
                        ],
                    )
                ],
            )
        ],
    )


def test_extend():
    content = """extend:
  /etc/systemd/system/rootco-salt-backup.service:
    file.managed:
      - user: root
      - group: root
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=5, col=0),
        extend=ExtendNode(
            start=Position(line=0, col=0),
            end=Position(line=5, col=0),
            states=[
                StateNode(
                    start=Position(line=1, col=2),
                    end=Position(line=5, col=0),
                    identifier="/etc/systemd/system/rootco-salt-backup.service",
                    states=[
                        StateCallNode(
                            start=Position(line=2, col=4),
                            end=Position(line=5, col=0),
                            name="file.managed",
                            parameters=[
                                StateParameterNode(
                                    start=Position(line=3, col=6),
                                    end=Position(line=4, col=6),
                                    name="user",
                                    value="root",
                                ),
                                StateParameterNode(
                                    start=Position(line=4, col=6),
                                    end=Position(line=5, col=0),
                                    name="group",
                                    value="root",
                                ),
                            ],
                        )
                    ],
                )
            ],
        ),
    )


def test_requisites():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: root
    - group: root
    - require:
      - file: /foo/bar
      - service: libvirtd
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=7, col=0),
        states=[
            StateNode(
                start=Position(line=0, col=0),
                end=Position(line=7, col=0),
                identifier="/etc/systemd/system/rootco-salt-backup.service",
                states=[
                    StateCallNode(
                        start=Position(line=1, col=2),
                        end=Position(line=7, col=0),
                        name="file.managed",
                        parameters=[
                            StateParameterNode(
                                start=Position(line=2, col=4),
                                end=Position(line=3, col=4),
                                name="user",
                                value="root",
                            ),
                            StateParameterNode(
                                start=Position(line=3, col=4),
                                end=Position(line=4, col=4),
                                name="group",
                                value="root",
                            ),
                        ],
                        requisites=[
                            RequisitesNode(
                                start=Position(line=4, col=4),
                                end=Position(line=7, col=0),
                                kind="require",
                                requisites=[
                                    RequisiteNode(
                                        start=Position(line=5, col=6),
                                        end=Position(line=6, col=6),
                                        module="file",
                                        reference="/foo/bar",
                                    ),
                                    RequisiteNode(
                                        start=Position(line=6, col=6),
                                        end=Position(line=7, col=0),
                                        module="service",
                                        reference="libvirtd",
                                    ),
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )


def create_mark(content, line, col, index):
    return yaml.Mark(
        name="<unicode string>",
        line=line,
        column=col,
        buffer=f"{content}\x00",
        pointer=index,
        index=index,
    )


def test_complex_parameter_state():
    content = """saltmaster.packages:
  pkg.installed:
    - pkgs:
      - salt-master
      - sshd
      - git
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=6, col=0),
        states=[
            StateNode(
                start=Position(line=0, col=0),
                end=Position(line=6, col=0),
                identifier="saltmaster.packages",
                states=[
                    StateCallNode(
                        start=Position(line=1, col=2),
                        end=Position(line=6, col=0),
                        name="pkg.installed",
                        parameters=[
                            StateParameterNode(
                                start=Position(line=2, col=4),
                                end=Position(line=6, col=0),
                                name="pkgs",
                                value=[
                                    TokenNode(
                                        yaml.BlockEntryToken(
                                            start_mark=create_mark(
                                                line=3,
                                                col=6,
                                                content=content,
                                                index=56,
                                            ),
                                            end_mark=create_mark(
                                                line=3,
                                                col=7,
                                                content=content,
                                                index=57,
                                            ),
                                        )
                                    ),
                                    TokenNode(
                                        yaml.ScalarToken(
                                            start_mark=create_mark(
                                                line=3,
                                                col=8,
                                                content=content,
                                                index=58,
                                            ),
                                            end_mark=create_mark(
                                                line=3,
                                                col=19,
                                                content=content,
                                                index=69,
                                            ),
                                            value="salt-master",
                                            plain=True,
                                        )
                                    ),
                                    TokenNode(
                                        yaml.BlockEntryToken(
                                            start_mark=create_mark(
                                                line=4,
                                                col=6,
                                                content=content,
                                                index=76,
                                            ),
                                            end_mark=create_mark(
                                                line=4,
                                                col=7,
                                                content=content,
                                                index=77,
                                            ),
                                        )
                                    ),
                                    TokenNode(
                                        yaml.ScalarToken(
                                            start_mark=create_mark(
                                                line=4,
                                                col=8,
                                                content=content,
                                                index=78,
                                            ),
                                            end_mark=create_mark(
                                                line=4,
                                                col=12,
                                                content=content,
                                                index=82,
                                            ),
                                            value="sshd",
                                            plain=True,
                                        )
                                    ),
                                    TokenNode(
                                        yaml.BlockEntryToken(
                                            start_mark=create_mark(
                                                line=5,
                                                col=6,
                                                content=content,
                                                index=89,
                                            ),
                                            end_mark=create_mark(
                                                line=5,
                                                col=7,
                                                content=content,
                                                index=90,
                                            ),
                                        )
                                    ),
                                    TokenNode(
                                        yaml.ScalarToken(
                                            start_mark=create_mark(
                                                line=5,
                                                col=8,
                                                content=content,
                                                index=91,
                                            ),
                                            end_mark=create_mark(
                                                line=5,
                                                col=11,
                                                content=content,
                                                index=94,
                                            ),
                                            value="git",
                                            plain=True,
                                        )
                                    ),
                                ],
                            ),
                        ],
                    )
                ],
            )
        ],
    )


def test_duplicate_key():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: root
    - user: bar
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=4, col=0),
        states=[
            StateNode(
                start=Position(line=0, col=0),
                end=Position(line=4, col=0),
                identifier="/etc/systemd/system/rootco-salt-backup.service",
                states=[
                    StateCallNode(
                        start=Position(line=1, col=2),
                        end=Position(line=4, col=0),
                        name="file.managed",
                        parameters=[
                            StateParameterNode(
                                start=Position(line=2, col=4),
                                end=Position(line=3, col=4),
                                name="user",
                                value="root",
                            ),
                            StateParameterNode(
                                start=Position(line=3, col=4),
                                end=Position(line=4, col=0),
                                name="user",
                                value="bar",
                            ),
                        ],
                    )
                ],
            )
        ],
    )


def test_empty_requisite_item():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: root
    - group: root
    - require:
      - file: /foo/bar
      - 
"""
    tree = parse(content)
    assert tree == Tree(
        start=Position(line=0, col=0),
        end=Position(line=7, col=0),
        states=[
            StateNode(
                start=Position(line=0, col=0),
                end=Position(line=7, col=0),
                identifier="/etc/systemd/system/rootco-salt-backup.service",
                states=[
                    StateCallNode(
                        start=Position(line=1, col=2),
                        end=Position(line=7, col=0),
                        name="file.managed",
                        parameters=[
                            StateParameterNode(
                                start=Position(line=2, col=4),
                                end=Position(line=3, col=4),
                                name="user",
                                value="root",
                            ),
                            StateParameterNode(
                                start=Position(line=3, col=4),
                                end=Position(line=4, col=4),
                                name="group",
                                value="root",
                            ),
                        ],
                        requisites=[
                            RequisitesNode(
                                start=Position(line=4, col=4),
                                end=Position(line=7, col=0),
                                kind="require",
                                requisites=[
                                    RequisiteNode(
                                        start=Position(line=5, col=6),
                                        end=Position(line=6, col=6),
                                        module="file",
                                        reference="/foo/bar",
                                    ),
                                    RequisiteNode(
                                        start=Position(line=6, col=6),
                                        end=Position(line=7, col=0),
                                        module=None,
                                        reference=None,
                                    ),
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )


def test_visit():
    content = """/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: root
    - group: root
"""
    tree = parse(content)
    pos = Position(line=2, col=8)
    found_node = None

    def visitor(node: AstNode) -> bool:
        if pos >= node.start and pos < node.end:
            nonlocal found_node
            found_node = node
        return True

    tree.visit(visitor)
    assert found_node == StateParameterNode(
        start=Position(line=2, col=4),
        end=Position(line=3, col=4),
        name="user",
        value="root",
    )
