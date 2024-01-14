/* -------------------------------------------------------------------------
 * Original work Copyright (c) Microsoft Corporation. All rights reserved.
 * Original work licensed under the MIT License.
 * All modifications Copyright (c) Open Law Library. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http: // www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ----------------------------------------------------------------------- */

import {spawn} from "child_process";
import * as net from "net";
import {ExtensionContext, window, workspace, commands} from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  Disposable,
} from "vscode-languageclient/node";

class ProcessError extends Error {
  constructor(public readonly command: string, public readonly returnCode: number|null,
              public readonly stdout: any[], public readonly stderr: any[]) {
    super(`${command} failed with code=${
        returnCode ??
        "null"}, stdout='${stdout.join("\n")}', stderr='${stderr.join("\n")}'`);
  }
}

export function runProcess(command: string, args?: readonly string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args);

    const stdout: any[] = [];
    const stderr: any[] = [];

    child.stdout.on("data", (data) => stdout.push(data));
    child.stderr.on("data", (data) => stderr.push(data));
    child.on("close", (code) => {
      if (code === 0) {
        resolve(stdout.join(""));
      } else {
        reject(new ProcessError(command, code, stdout, stderr));
      }
    });

    child.on("error", (err) => { reject(err); });
  });
}

let client: LanguageClient;

function getClientOptions(): LanguageClientOptions {
  return {
      // Register the server for sls files
    documentSelector : [
      {scheme : "file", language : "sls"},
      {scheme : "untitled", language : "sls"},
    ],
    outputChannelName : "[salt_lsp] SaltStateLanguageServer",
  };
}

function isStartedInDebugMode(): boolean { return process.env.VSCODE_DEBUG_MODE === "true"; }

let clientSocket: net.Socket;

function startLangServerTCP(addr: number): LanguageClient {
  const serverOptions: ServerOptions = () => {
    return new Promise((resolve) => {
      clientSocket = new net.Socket();

      clientSocket.connect(addr, "127.0.0.1", () => {
        resolve({
          reader : clientSocket,
          writer : clientSocket,
        });
      });

      clientSocket.on(
          "close", () => { setTimeout(() => { clientSocket.connect(addr, "127.0.0.1"); }, 1000); });
    });
  };

  return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, getClientOptions());
}

function startLangServer(command: string, args: string[]): LanguageClient {
  const serverOptions: ServerOptions = {
    args,
    command,
  };

  return new LanguageClient(command, serverOptions, getClientOptions());
}


export async function activate(context: ExtensionContext){
  let disposableClient: Disposable;
  const startLSPServer = async () => {
    if (isStartedInDebugMode()) {
      client = startLangServerTCP(2087);
    } else {
      const pythonPath = workspace
        .getConfiguration("python")
        .get<string>("pythonPath");

      if (pythonPath === undefined) {
        try {
          await runProcess("python3", ["--version"]);
        } catch {
          const errMsg =
            "'python.pythonPath' not set and could not launch python. Please install python to be able to use this Language Server";
          await window.showErrorMessage(errMsg);
          throw new Error(errMsg);
        }
      }

      const python = pythonPath ?? "python3";

      try {
        await runProcess(python, ["-m", "salt_lsp", "--stop-after-init"]);
      } catch (exc) {
        const errMsg = `Could not launch the Salt Language Server, got the following error: ${(
          exc as ProcessError
        ).toString()}.

  You might have to install salt_lsp via 'pip install salt_lsp'.`;
        await window.showErrorMessage(errMsg);
        throw new Error(errMsg);
      }

      client = startLangServer(python, ["-m", "salt_lsp"]);
    }
    disposableClient = client
  }

  const restartLanguageServer = function (): Promise<void> {
    return new Promise((resolve) => {
      if (disposableClient) {
        client.stop().then(() => {
          disposableClient.dispose();
          startLSPServer();
          resolve();
        });
      } else {
        startLSPServer();
        resolve();
      }
    });
  }

  var disposableRestart = commands.registerCommand('salt-lsp.restart', () => {
    restartLanguageServer().then(() => {
      window.showInformationMessage('Salt-lsp server restarted.');
    });
  });
  context.subscriptions.push(disposableRestart);
  await startLSPServer()
}

export function deactivate(): Thenable<void> { return client ? client.stop() : Promise.resolve(); }
