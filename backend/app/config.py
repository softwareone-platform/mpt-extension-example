from dynaconf import Dynaconf, LazySettings
from pathlib import Path

type Settings = LazySettings


settings: Settings = Dynaconf(
    root_path=Path(__file__).parent.parent.parent.resolve(),
    settings_files=["settings.yaml", ".secrets.yaml"],
)
