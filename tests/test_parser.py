from salt_lsp.utils import construct_path_to_position

from ruamel import yaml
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


SLS_PARSED = yaml.load(MASTER_DOT_SLS, Loader=yaml.RoundTripLoader)


class TestPathToPosition:
    def test_path_to_pkgs_list(self):
        expected_res = [
            "saltmaster.packages",
            "pkg.installed",
            0,
            "pkgs",
        ]
        for line in (3, 4, 5):
            assert (
                construct_path_to_position(
                    SLS_PARSED, Position(line=line, character=7)
                )
                == expected_res
            )

    def test_path_to_require(self):
        assert construct_path_to_position(
            SLS_PARSED, Position(line=8, character=7)
        ) == [
            "saltmaster.packages",
            "pkg.installed",
            1,
            "require",
        ]

    def test_path_to_dummy(self):
        assert construct_path_to_position(
            SLS_PARSED, Position(line=14, character=7)
        ) == [
            "git -C /srv/salt pull -q",
            "cron.present",
            2,
            "dummy",
        ]

    def test_path_after_dummy(self):
        assert construct_path_to_position(
            SLS_PARSED, Position(line=15, character=5)
        ) == [
            "git -C /srv/salt pull -q",
            "cron.present",
        ]

    def test_path_before_target(self):
        assert construct_path_to_position(
            SLS_PARSED,
            # before "target: /srv/salt"
            Position(line=19, character=5),
        ) == [
            "/srv/git/salt-states",
            "file.symlink",
        ]
