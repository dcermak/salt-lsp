#!/usr/bin/python3
import subprocess
import shlex
import json
import pickle
import tempfile
import os
from typing import Dict

from base_types import StateNameCompletion


if __name__ == "__main__":

    state_completions: Dict[str, StateNameCompletion] = {}

    with tempfile.TemporaryDirectory() as tmpdirname:
        salt_dest = os.path.join(tmpdirname, "salt")
        minion_conf_file = os.path.join(salt_dest, "minion")
        os.mkdir(salt_dest)
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
                ).stdout,
                encoding="utf-8",
            )
        )

        for module in docs["local"]:
            state_completions[module] = StateNameCompletion(
                module, docs["local"][module]
            )

    with open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "states.pickle"
        ),
        "wb",
    ) as states_file:
        pickle.dump(state_completions, states_file)
