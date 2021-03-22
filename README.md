# salt-lsp

Salt Language Server Protocol Server


## Setup

Setup & start the server:

```ShellSession
$ python3 -m venv .env3
$ . .env3/bin/activate
$ pip install -r requirements.txt
$ python3 salt-lsp/__main__.py --tcp
```

Launch the client:

1. Run `yarn install`
2. Start VSCode and open this directory as the server
3. Open the Debug menu (Ctrl + Shift + D)
4. Select "Launch Client" drop down
5. Press F5
