#!/usr/bin/env python3
import subprocess
import shlex
import json
import pickle
import tempfile
from os import mkdir
from os.path import join, abspath, dirname
from typing import Dict

from salt_lsp.base_types import StateNameCompletion


if __name__ == "__main__":

    state_completions: Dict[str, StateNameCompletion] = {}

    with tempfile.TemporaryDirectory() as tmpdirname:
        salt_dest = join(tmpdirname, "salt")
        minion_conf_file = join(salt_dest, "minion")
        mkdir(salt_dest)
        with open(minion_conf_file, "w") as minion_file:
            minion_file.write(f"root_dir: {tmpdirname}")

        docs = json.loads(
            str(
                subprocess.run(
                    shlex.split(
                        f"salt-call --local -c {salt_dest} --out json "
                        "baredoc.list_states"
                    ),
                    capture_output=True,
                    check=True,
                ).stdout,
                encoding="utf-8",
            )
        )

        for module in docs["local"]:
            state_completions[module] = StateNameCompletion(
                module, docs["local"][module]
            )

    with open(
        join(dirname(abspath(__file__)), "data", "states.pickle"),
        "wb",
    ) as states_file:
        pickle.dump(state_completions, states_file)
