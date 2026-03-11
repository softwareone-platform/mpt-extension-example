from pathlib import Path

from dynaconf import Dynaconf, LazySettings

type Settings = LazySettings


settings: Settings = Dynaconf(
    root_path=Path(__file__).parent.parent.parent.resolve(),
    envvar_prefix="EXT",
    settings_files=["settings.yaml", ".secrets.yaml"],
)
