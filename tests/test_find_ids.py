from lsprotocol.types import (
    Location,
    Range,
    Position,
)

from conftest import open_file, open_workspace


def test_find_id_in_document(salt_client_server, sample_workspace):
    client, server = salt_client_server

    open_workspace(client, f"file://{sample_workspace}")

    base_sls_path = f"{sample_workspace}/opensuse/base.sls"
    base_sls_uri = "file://" + base_sls_path

    open_file(client, base_sls_path)

    assert server.find_id_in_doc_and_includes(
        "bernd", base_sls_uri
    ) == Location(
        uri=base_sls_uri,
        range=Range(
            start=Position(line=0, character=0),
            end=Position(line=5, character=0),
        ),
    )


def test_find_id_in_include(salt_client_server, sample_workspace):
    client, server = salt_client_server

    open_workspace(client, f"file://{sample_workspace}")

    bar_sls_path = f"{sample_workspace}/bar.sls"
    bar_sls_uri = "file://" + bar_sls_path

    open_file(client, bar_sls_path)

    assert server.find_id_in_doc_and_includes(
        "/root/.fishrc", bar_sls_uri
    ) == Location(
        uri="file://" + str(sample_workspace / "quo.sls"),
        range=Range(
            start=Position(line=0, character=0),
            end=Position(line=6, character=0),
        ),
    )


def test_find_id_in_indirect_include(salt_client_server, sample_workspace):
    client, server = salt_client_server

    open_workspace(client, f"file://{sample_workspace}")

    foo_sls_path = f"{sample_workspace}/foo.sls"
    foo_sls_uri = "file://" + foo_sls_path

    open_file(client, foo_sls_path)

    assert server.find_id_in_doc_and_includes(
        "/root/.fishrc", foo_sls_uri
    ) == Location(
        uri="file://" + str(sample_workspace / "quo.sls"),
        range=Range(
            start=Position(line=0, character=0),
            end=Position(line=6, character=0),
        ),
    )
