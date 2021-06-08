import os

import pytest
from pygls.lsp import types

from salt_lsp.utils import (
    ast_node_to_range,
    get_git_root,
    get_last_element_of_iterator,
    is_valid_file_uri,
    FileUri,
)
from salt_lsp.parser import IncludeNode, Position


def test_last_element_of_range():
    assert get_last_element_of_iterator(range(10)) == 9


def test_last_element_of_empty_range():
    assert get_last_element_of_iterator(range(0)) is None


class TestFileUri:
    def test_file_uri_construction(self):
        path = "/path/to/file"

        assert FileUri(path).path == path
        assert FileUri(f"file://{path}").path == path

    def test_throws_exception_for_invalid_uri(self):
        with pytest.raises(ValueError) as excinfo:
            FileUri("http://foo.bar.xyz")
        assert "Invalid uri scheme http" in str(excinfo.value)


def test_is_valid_file_uri_accepts_paths():
    assert is_valid_file_uri("/path/to/foo")


def test_is_valid_file_uri_accepts_file_uris():
    assert is_valid_file_uri("file:///path/to/foo")


def test_is_valid_file_uri_accepts_rejects_other_uris():
    assert not is_valid_file_uri("https://www.foobar.xyz")


class TestAstNodeToRange:
    def test_returns_none_if_start_none(self):
        node = IncludeNode(end=Position(0, 0))
        assert ast_node_to_range(node) is None

    def test_returns_none_if_end_none(self):
        node = IncludeNode(start=Position(0, 0))
        assert ast_node_to_range(node) is None

    def test_returns_a_lsp_range(self):
        node = IncludeNode(start=Position(0, 1), end=Position(2, 3))
        assert ast_node_to_range(node) == types.Range(
            start=types.Position(line=0, character=1),
            end=types.Position(line=2, character=3),
        )


def test_get_git_root(host, tmp_path):
    os.chdir(tmp_path)
    cwd = os.getcwd()
    try:
        host.run_expect([0], "git init")
        foo = tmp_path / "foo"
        foobar = foo / "bar"
        foobar.mkdir(parents=True)

        assert get_git_root(str(foobar)) == str(tmp_path)
        assert get_git_root(str(foo)) == str(tmp_path)
        assert get_git_root(str(tmp_path)) == str(tmp_path)
        assert get_git_root(str(foobar / "init.sls")) == str(tmp_path)
    except Exception as exc:
        os.chdir(cwd)
        raise exc


def test_get_git_root_outside_of_git_repository(tmp_path):
    assert get_git_root(tmp_path) is None
