from salt_lsp.parser import (
    RequisiteNode,
    RequisitesNode,
    StateCallNode,
    StateNode,
    StateParameterNode,
    Tree,
)
from salt_lsp.utils import construct_path_to_position

from pygls.lsp.types import (
    Position,
)


MASTER_DOT_SLS = """saltmaster.packages:
  pkg.installed:
    - pkgs:
      - salt-master
      - sshd
      - git
    - require:
      - file: /etc/foo/bar.conf
      -

git -C /srv/salt pull -q:
  cron.present:
    - user: root
    - minute: '*/5'
    - dummy:
      -
    -

/srv/git/salt-states:
  file.symlink:
    -
    - target: /srv/salt

/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
    - user: root
    - group: root
    - mode: 644
    - source: salt://salt/rootco-salt-backup.service
    - template: jinja

/etc/systemd/system/rootco-salt-backup.timer:
  file.managed:
    - user: root
    - group: root
    - mode: 644
    - source: salt://salt/rootco-salt-backup.timer
    - require:
      - file: /etc/systemd/system/rootco-salt-backup.service

rootco-salt-backup.timer:
  service.running:
    - enable: True
    - require:
      - file: /etc/systemd/system/rootco-salt-backup.timer
"""


def test_path_to_pkgs_list():
    for line in (3, 4, 5):
        path = construct_path_to_position(
            MASTER_DOT_SLS, Position(line=line, character=8)
        )

        assert len(path) == 4
        assert isinstance(path[0], Tree)
        assert isinstance(path[1], StateNode)
        assert path[1].identifier == "saltmaster.packages"
        assert isinstance(path[2], StateCallNode)
        assert path[2].name == "pkg.installed"
        assert isinstance(path[3], StateParameterNode)
        assert path[3].name == "pkgs"

def test_path_to_require():
    path = construct_path_to_position(
        MASTER_DOT_SLS, Position(line=8, character=7)
    )
    assert len(path) == 5
    assert isinstance(path[0], Tree)
    assert isinstance(path[1], StateNode)
    assert path[1].identifier == "saltmaster.packages"
    assert isinstance(path[2], StateCallNode)
    assert path[2].name == "pkg.installed"
    assert isinstance(path[3], RequisitesNode)
    assert path[3].kind == "require"
    assert isinstance(path[4], RequisiteNode)

def test_path_to_dummy():
    path = construct_path_to_position(
        MASTER_DOT_SLS, Position(line=14, character=7)
    )

    assert len(path) == 4
    assert isinstance(path[0], Tree)
    assert isinstance(path[1], StateNode)
    assert path[1].identifier == "git -C /srv/salt pull -q"
    assert isinstance(path[2], StateCallNode)
    assert path[2].name == "cron.present"
    assert isinstance(path[3], StateParameterNode)
    assert path[3].name == "dummy"

def test_path_after_dummy():
    path = construct_path_to_position(
        MASTER_DOT_SLS, Position(line=15, character=5)
    )

    assert len(path) == 4
    assert isinstance(path[0], Tree)
    assert isinstance(path[1], StateNode)
    assert path[1].identifier == "git -C /srv/salt pull -q"
    assert isinstance(path[2], StateCallNode)
    assert path[2].name == "cron.present"
    assert isinstance(path[3], StateParameterNode)
    assert path[3].name == "dummy"

def test_path_before_target():
    path = construct_path_to_position(
        MASTER_DOT_SLS,
        # before "target: /srv/salt"
        Position(line=19, character=5),
    )

    assert len(path) == 3
    assert isinstance(path[0], Tree)
    assert isinstance(path[1], StateNode)
    assert path[1].identifier == "/srv/git/salt-states"
    assert isinstance(path[2], StateCallNode)
    assert path[2].name == "file.symlink"
