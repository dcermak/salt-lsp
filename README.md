# salt-lsp

[![Continous Integration](https://github.com/dcermak/salt-lsp/actions/workflows/ci.yml/badge.svg)](https://github.com/dcermak/salt-lsp/actions/workflows/ci.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/dcermak/salt-lsp)](https://app.codecov.io/gh/dcermak/salt-lsp)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)

Salt Language Server Protocol Server


## Prerequisites

- Python >= 3.8
- [Poetry](https://python-poetry.org/)
- VSCode (required for live testing the server from an editor)


## Setup

Install the dependencies:

```ShellSession
$ poetry install
```

Create the completion classes once:

```ShellSession
$ poetry run dump_state_name_completions
```

Start the server:

```ShellSession
$ poetry run salt_lsp_server --tcp
```

Launch the client:

1. Run `yarn install`
2. Start VSCode and open this directory as the server
3. Open the Debug menu (Ctrl + Shift + D)
4. Select "Launch Client" drop down
5. Press F5
