from dataclasses import dataclass
from pathlib import Path


@dataclass
class P4Params:
    initial_compiled_script_host_path: str | None = None
    run_nic: bool = True

    @property
    def host_script_path(self) -> Path | None:
        if self.initial_compiled_script_host_path is None:
            return None
        return Path(self.initial_compiled_script_host_path)
