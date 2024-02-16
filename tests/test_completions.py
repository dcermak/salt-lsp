from types import SimpleNamespace

from lsprotocol.types import TextDocumentItem

from conftest import MODULE_DOCS


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


def test_complete_of_file(salt_client_server, file_name_completer):
    _, server = salt_client_server
    txt_doc = {
        "text_document": TextDocumentItem(
            uri="foo.sls", text=TEST_FILE, version=0, language_id="sls"
        ),
    }
    server.workspace.put_text_document(txt_doc["text_document"])

    completions = server.complete_state_name(
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
        for submod_name in file_name_completer["file"].state_sub_names
    ]
    assert completions == expected_completions
