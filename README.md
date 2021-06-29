# salt-lsp

[![Continous Integration](https://github.com/dcermak/salt-lsp/actions/workflows/ci.yml/badge.svg)](https://github.com/dcermak/salt-lsp/actions/workflows/ci.yml)
[![VSCode Extension Build](https://github.com/dcermak/salt-lsp/actions/workflows/vscode_extension.yml/badge.svg)](https://github.com/dcermak/salt-lsp/actions/workflows/vscode_extension.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/dcermak/salt-lsp)](https://app.codecov.io/gh/dcermak/salt-lsp)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)
[![PyPI](https://img.shields.io/pypi/v/salt-lsp)](https://pypi.org/project/salt-lsp/)
[![Visual Studio Marketplace](https://img.shields.io/visual-studio-marketplace/v/dancermak.salt-lsp)](https://marketplace.visualstudio.com/items?itemName=dancermak.salt-lsp)

Salt Language Server Protocol Server


## Prerequisites

- Python >= 3.8
- [Poetry](https://python-poetry.org/)
- VSCode (required for live testing the server from an editor)


## Server Setup

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

Install the server:
```ShellSession
$ poetry build
$ pip install --user --force-reinstall dist/salt_lsp-0.0.1*whl
```

# Clients

## VSCode

1. Run `yarn install`
2. Start VSCode and open this directory as the server
3. Open the Debug menu (Ctrl + Shift + D)
4. Select "Launch Client" drop down
5. Press F5


## Emacs

You should install [salt-mode](https://github.com/glynnforrest/salt-mode) so
that `sls` files are registered to the salt major mode. The language server must
be installed on your system so that the clients can launch it.

### Using lsp-mode

1. Install & configure [lsp-mode](https://github.com/emacs-lsp/lsp-mode/)
2. Load the file `clients/emacs/salt-lsp.el`
3. Open a sls file and launch `lsp` via `M-x lsp`


### Using eglot

1. Install & configure [eglot](https://github.com/joaotavora/eglot)
2. Evaluate the following snippet:
```elisp
(add-to-list 'eglot-server-programs '(salt-mode . ("python3" "-m" "salt_lsp")))
```
3. Launch eglot via `M-x eglot`
