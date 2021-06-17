import subprocess
import shlex
import json
import pathlib
import pickle
import tempfile
from os.path import abspath, dirname
from typing import Dict

from salt_lsp.base_types import StateNameCompletion


def dump_state_name_completions() -> None:
    state_completions: Dict[str, StateNameCompletion] = {}

    with tempfile.TemporaryDirectory() as tmpdirname:
        salt_dest = pathlib.Path(tmpdirname) / "salt"
        salt_dest.mkdir()

        with open(salt_dest / "minion", "w") as minion_file:
            minion_file.write(f"root_dir: {tmpdirname}")

        mod_list, docs = (
            json.loads(
                str(
                    subprocess.run(
                        shlex.split(
                            f"salt-call --local -c {salt_dest} --out json "
                            f"baredoc.{mod_name}"
                        ),
                        capture_output=True,
                        check=True,
                    ).stdout,
                    encoding="utf-8",
                )
            )
            for mod_name in ("list_states", "state_docs")
        )

        for module in mod_list["local"]:
            state_completions[module] = StateNameCompletion(
                module, mod_list["local"][module], docs["local"]
            )

    dest_dir = pathlib.Path(dirname(abspath(__file__))) / "data"
    if not dest_dir.exists():
        dest_dir.mkdir()

    with open(dest_dir / "states.pickle", "wb") as states_file:
        pickle.dump(state_completions, states_file)
