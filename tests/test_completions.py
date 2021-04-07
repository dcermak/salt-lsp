from types import SimpleNamespace

from salt_lsp.server import salt_server

from conftest import FILE_NAME_COMPLETER, MODULE_DOCS


TEST_FILE = """saltmaster.packages:
  pkg.installed:
    - pkgs:
      - salt-master

/srv/git/salt-states:
  file.:
    - target: /srv/salt

git -C /srv/salt pull -q:
  cron.:
    - user: root
    - minute: '*/5'
"""


salt_server.post_init(FILE_NAME_COMPLETER)


class TestStateNameCompletion:
    def test_complete_of_file(self):
        txt_doc = {
            "text_document": SimpleNamespace(uri="foo.sls", text=TEST_FILE)
        }
        salt_server.register_file(SimpleNamespace(**txt_doc))

        completions = salt_server.complete_state_name(
            SimpleNamespace(
                **{
                    **txt_doc,
                    "position": SimpleNamespace(line=6, character=7),
                    "context": SimpleNamespace(trigger_character="."),
                }
            )
        )

        expected_completions = [
            (submod_name, MODULE_DOCS[f"file.{submod_name}"])
            for submod_name in FILE_NAME_COMPLETER["file"].state_sub_names
        ]
        assert completions == expected_completions
