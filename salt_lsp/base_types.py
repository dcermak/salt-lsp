from typing import Any, List


class StateNameCompletion:
    def __init__(self, state_name: str, state_params: List[Any]) -> None:
        self.state_name = state_name
        self.state_params = {}

        for submod in state_params:
            submod_name = next(iter(submod.keys()))
            self.state_params[submod_name] = submod[submod_name]

        self.state_sub_names = list(self.state_params.keys())

    def provide_subname_completion(self) -> List[str]:
        return self.state_sub_names

    def provide_param_completion(self, submod_name: str) -> List[str]:
        return list(self.state_params[submod_name].keys())
