import pytest

from salt_lsp.base_types import StateNameCompletion


MODULE_DOCS = {
    "file": "doc of file",
    "file.absent": "Make sure that the named file or directory is absent. If it exists, it will\nbe deleted. This will work to reverse any of the functions in the file\nstate module. If a directory is supplied, it will be recursively deleted.\n\nname\n    The path which should be deleted",
    "file.accumulated": "file accumulated docs",
    "file.append": "file append details",
    "file.blockreplace": "",
    "file.cached": "",
    "file.comment": "",
    "file.copy": "",
    "file.decode": "",
    "file.directory": "",
    "file.exists": "Verify that the named file or directory is present or exists.\nEnsures pre-requisites outside of Salt's purview\n(e.g., keytabs, private keys, etc.) have been previously satisfied before\ndeployment.\n\nThis function does not create the file if it doesn't exist, it will return\nan error.\n\nname\n    Absolute path which must exist",
    "file.hardlink": "",
    "file.keyvalue": "",
    "file.line": "",
    "file.managed": "",
    "file.missing": "Verify that the named file or directory is missing, this returns True only\nif the named file is missing but does not remove the file if it is present.\n\nname\n    Absolute path which must NOT exist",
    "file.mknod": "",
    "file.mod_run_check_cmd": "Execute the check_cmd logic.\n\nReturn a result dict if ``check_cmd`` succeeds (check_cmd == 0)\notherwise return True",
    "file.not_cached": "",
    "file.patch": "",
    "file.prepend": "",
    "file.recurse": "",
    "file.rename": 'If the source file exists on the system, rename it to the named file. The\nnamed file will not be overwritten if it already exists unless the force\noption is set to True.\n\nname\n    The location of the file to rename to\n\nsource\n    The location of the file to move to the location specified with name\n\nforce\n    If the target location is present then the file will not be moved,\n    specify "force: True" to overwrite the target file\n\nmakedirs\n    If the target subdirectories don\'t exist create them',
    "file.replace": "",
    "file.retention_schedule": "",
    "file.serialize": "",
    "file.shortcut": "",
    "file.symlink": "Just a dummy documentation of file.symlink",
    "file.tidied": "",
    "file.touch": "",
    "file.uncomment": "",
}


FILE_PARAMS = [
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
]


FILE_NAME_COMPLETER = {
    "file": StateNameCompletion(
        "file",
        FILE_PARAMS,
        MODULE_DOCS,
    )
}


@pytest.fixture
def file_name_completer():
    return {
        "file": StateNameCompletion(
            "file",
            FILE_PARAMS,
            MODULE_DOCS,
        )
    }
