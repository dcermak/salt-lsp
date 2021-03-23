from types import SimpleNamespace
from salt_lsp.server import salt_server
from salt_lsp.base_types import StateNameCompletion


TEST_FILE = """/etc/systemd/system/foo.service:
  file.:
"""

FILE_NAME_COMPLETER = {
    "file": StateNameCompletion(
        "file",
        [
            {
                "hardlink": {
                    "name": None,
                    "target": None,
                    "force": False,
                    "makedirs": False,
                    "user": None,
                    "group": None,
                    "dir_mode": None,
                    "kwargs": "kwargs",
                }
            },
            {
                "symlink": {
                    "name": None,
                    "target": None,
                    "force": False,
                    "backupname": None,
                    "makedirs": False,
                    "user": None,
                    "group": None,
                    "mode": None,
                    "win_owner": None,
                    "win_perms": None,
                    "win_deny_perms": None,
                    "win_inheritance": None,
                    "kwargs": "kwargs",
                }
            },
            {"absent": {"name": None, "kwargs": "kwargs"}},
            {
                "tidied": {
                    "name": None,
                    "age": 0,
                    "matches": None,
                    "rmdirs": False,
                    "size": 0,
                    "kwargs": "kwargs",
                }
            },
            {"exists": {"name": None, "kwargs": "kwargs"}},
            {"missing": {"name": None, "kwargs": "kwargs"}},
            {
                "managed": {
                    "name": None,
                    "source": None,
                    "source_hash": "",
                    "source_hash_name": None,
                    "keep_source": True,
                    "user": None,
                    "group": None,
                    "mode": None,
                    "attrs": None,
                    "template": None,
                    "makedirs": False,
                    "dir_mode": None,
                    "context": None,
                    "replace": True,
                    "defaults": None,
                    "backup": "",
                    "show_changes": True,
                    "create": True,
                    "contents": None,
                    "tmp_dir": "",
                    "tmp_ext": "",
                    "contents_pillar": None,
                    "contents_grains": None,
                    "contents_newline": True,
                    "contents_delimiter": ":",
                    "encoding": None,
                    "encoding_errors": "strict",
                    "allow_empty": True,
                    "follow_symlinks": True,
                    "check_cmd": None,
                    "skip_verify": False,
                    "selinux": None,
                    "win_owner": None,
                    "win_perms": None,
                    "win_deny_perms": None,
                    "win_inheritance": True,
                    "win_perms_reset": False,
                    "verify_ssl": True,
                    "kwargs": "kwargs",
                }
            },
            {
                "directory": {
                    "name": None,
                    "user": None,
                    "group": None,
                    "recurse": None,
                    "max_depth": None,
                    "dir_mode": None,
                    "file_mode": None,
                    "makedirs": False,
                    "clean": False,
                    "require": None,
                    "exclude_pat": None,
                    "follow_symlinks": False,
                    "force": False,
                    "backupname": None,
                    "allow_symlink": True,
                    "children_only": False,
                    "win_owner": None,
                    "win_perms": None,
                    "win_deny_perms": None,
                    "win_inheritance": True,
                    "win_perms_reset": False,
                    "kwargs": "kwargs",
                }
            },
            {
                "recurse": {
                    "name": None,
                    "source": None,
                    "keep_source": True,
                    "clean": False,
                    "require": None,
                    "user": None,
                    "group": None,
                    "dir_mode": None,
                    "file_mode": None,
                    "sym_mode": None,
                    "template": None,
                    "context": None,
                    "replace": True,
                    "defaults": None,
                    "include_empty": False,
                    "backup": "",
                    "include_pat": None,
                    "exclude_pat": None,
                    "maxdepth": None,
                    "keep_symlinks": False,
                    "force_symlinks": False,
                    "win_owner": None,
                    "win_perms": None,
                    "win_deny_perms": None,
                    "win_inheritance": True,
                    "kwargs": "kwargs",
                }
            },
            {
                "retention_schedule": {
                    "name": None,
                    "retain": None,
                    "strptime_format": None,
                    "timezone": None,
                }
            },
            {
                "line": {
                    "name": None,
                    "content": None,
                    "match": None,
                    "mode": None,
                    "location": None,
                    "before": None,
                    "after": None,
                    "show_changes": True,
                    "backup": False,
                    "quiet": False,
                    "indent": True,
                    "create": False,
                    "user": None,
                    "group": None,
                    "file_mode": None,
                }
            },
            {
                "replace": {
                    "name": None,
                    "pattern": None,
                    "repl": None,
                    "count": 0,
                    "flags": 8,
                    "bufsize": 1,
                    "append_if_not_found": False,
                    "prepend_if_not_found": False,
                    "not_found_content": None,
                    "backup": ".bak",
                    "show_changes": True,
                    "ignore_if_missing": False,
                    "backslash_literal": False,
                }
            },
            {
                "keyvalue": {
                    "name": None,
                    "key": None,
                    "value": None,
                    "key_values": None,
                    "separator": "=",
                    "append_if_not_found": False,
                    "prepend_if_not_found": False,
                    "search_only": False,
                    "show_changes": True,
                    "ignore_if_missing": False,
                    "count": 1,
                    "uncomment": None,
                    "key_ignore_case": False,
                    "value_ignore_case": False,
                }
            },
            {
                "blockreplace": {
                    "name": None,
                    "marker_start": "#-- start managed zone --",
                    "marker_end": "#-- end managed zone --",
                    "source": None,
                    "source_hash": None,
                    "template": "jinja",
                    "sources": None,
                    "source_hashes": None,
                    "defaults": None,
                    "context": None,
                    "content": "",
                    "append_if_not_found": False,
                    "prepend_if_not_found": False,
                    "backup": ".bak",
                    "show_changes": True,
                    "append_newline": None,
                    "insert_before_match": None,
                    "insert_after_match": None,
                }
            },
            {
                "comment": {
                    "name": None,
                    "regex": None,
                    "char": "#",
                    "backup": ".bak",
                }
            },
            {
                "uncomment": {
                    "name": None,
                    "regex": None,
                    "char": "#",
                    "backup": ".bak",
                }
            },
            {
                "append": {
                    "name": None,
                    "text": None,
                    "makedirs": False,
                    "source": None,
                    "source_hash": None,
                    "template": "jinja",
                    "sources": None,
                    "source_hashes": None,
                    "defaults": None,
                    "context": None,
                    "ignore_whitespace": True,
                }
            },
            {
                "prepend": {
                    "name": None,
                    "text": None,
                    "makedirs": False,
                    "source": None,
                    "source_hash": None,
                    "template": "jinja",
                    "sources": None,
                    "source_hashes": None,
                    "defaults": None,
                    "context": None,
                    "header": None,
                }
            },
            {
                "patch": {
                    "name": None,
                    "source": None,
                    "source_hash": None,
                    "source_hash_name": None,
                    "skip_verify": False,
                    "template": None,
                    "context": None,
                    "defaults": None,
                    "options": "",
                    "reject_file": None,
                    "strip": None,
                    "saltenv": None,
                    "kwargs": "kwargs",
                }
            },
            {
                "touch": {
                    "name": None,
                    "atime": None,
                    "mtime": None,
                    "makedirs": False,
                }
            },
            {
                "copy": {
                    "name": None,
                    "source": None,
                    "force": False,
                    "makedirs": False,
                    "preserve": False,
                    "user": None,
                    "group": None,
                    "mode": None,
                    "subdir": False,
                    "kwargs": "kwargs",
                }
            },
            {
                "rename": {
                    "name": None,
                    "source": None,
                    "force": False,
                    "makedirs": False,
                    "kwargs": "kwargs",
                }
            },
            {
                "accumulated": {
                    "name": None,
                    "filename": None,
                    "text": None,
                    "kwargs": "kwargs",
                }
            },
            {
                "serialize": {
                    "name": None,
                    "dataset": None,
                    "dataset_pillar": None,
                    "user": None,
                    "group": None,
                    "mode": None,
                    "backup": "",
                    "makedirs": False,
                    "show_changes": True,
                    "create": True,
                    "merge_if_exists": False,
                    "encoding": None,
                    "encoding_errors": "strict",
                    "serializer": None,
                    "serializer_opts": None,
                    "deserializer_opts": None,
                    "kwargs": "kwargs",
                }
            },
            {
                "mknod": {
                    "name": None,
                    "ntype": None,
                    "major": 0,
                    "minor": 0,
                    "user": None,
                    "group": None,
                    "mode": "0600",
                }
            },
            {
                "mod_run_check_cmd": {
                    "cmd": None,
                    "filename": None,
                    "kwargs": "check_cmd_opts",
                }
            },
            {
                "decode": {
                    "name": None,
                    "encoded_data": None,
                    "contents_pillar": None,
                    "encoding_type": "base64",
                    "checksum": "md5",
                }
            },
            {
                "shortcut": {
                    "name": None,
                    "target": None,
                    "arguments": None,
                    "working_dir": None,
                    "description": None,
                    "icon_location": None,
                    "force": False,
                    "backupname": None,
                    "makedirs": False,
                    "user": None,
                    "kwargs": "kwargs",
                }
            },
            {
                "cached": {
                    "name": None,
                    "source_hash": "",
                    "source_hash_name": None,
                    "skip_verify": False,
                    "saltenv": "base",
                }
            },
            {"not_cached": {"name": None, "saltenv": "base"}},
        ],
    )
}

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
                    "position": SimpleNamespace(line=1, character=7),
                    "context": SimpleNamespace(trigger_character="."),
                }
            )
        )

        assert completions == FILE_NAME_COMPLETER["file"].state_sub_names
