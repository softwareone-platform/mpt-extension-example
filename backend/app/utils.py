import base64
import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from yaml import safe_load

from app.config import settings

_JINJA_ENV = Environment(loader=FileSystemLoader(Path(__file__).parent.parent.parent.resolve()))


def get_instance_external_id():
    result = subprocess.run(
        ["cat", "/proc/1/cpuset"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        result.check_returncode()
    except subprocess.CalledProcessError:
        return f"{uuid.getnode():012x}"

    _, container_id = result.stdout.decode()[:-1].rsplit("/", 1)
    if len(container_id) == 64:
        return container_id[:12]

    result = subprocess.run(
        ["grep", "overlay", "/proc/self/mountinfo"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        result.check_returncode()
        mount = result.stdout.decode()
        start_idx = mount.index("upperdir=") + len("upperdir=")
        end_idx = mount.index(",", start_idx)
        dir_path = mount[start_idx:end_idx]
        _, container_id, _ = dir_path.rsplit("/", 2)
        if len(container_id) != 64:
            return f"{uuid.getnode():012x}"
        return container_id[:12]
    except (subprocess.CalledProcessError, ValueError):
        return f"{uuid.getnode():012x}"


def get_meta():
    template = _JINJA_ENV.get_template("meta.yaml")
    return safe_load(template.render(settings=settings))


def get_jwt_token_claims(token: str) -> dict:
    try:
        _, payload, _ = token.split(".")

        # Add padding if needed
        padding = "=" * (-len(payload) % 4)
        payload += padding

        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        return claims
    except (KeyError, ValueError, json.JSONDecodeError, base64.binascii.Error) as exc:
        raise ValueError("Invalid JWT token") from exc


def get_jwt_token_expires(token: str) -> datetime:
    try:
        claims = get_jwt_token_claims(token)
        return datetime.fromtimestamp(claims["exp"], tz=UTC)
    except (KeyError, ValueError) as exc:
        raise ValueError("Invalid JWT token") from exc
