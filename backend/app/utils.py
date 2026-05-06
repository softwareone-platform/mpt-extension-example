import base64
import hashlib
import json
import os
import socket
import subprocess
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from yaml import safe_load

from app.config import settings

_JINJA_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent.parent.resolve()),
    undefined=StrictUndefined,
)


@lru_cache(maxsize=1)
def get_instance_external_id() -> str:
    hostname = (os.environ.get("HOSTNAME") or socket.gethostname() or "").lower()
    if len(hostname) == 12 and all(c in "0123456789abcdef" for c in hostname.lower()):
        return hostname

    try:
        with open("/proc/1/cpuset") as f:
            tail = f.read().strip().rsplit("/", 1)[-1]
        if len(tail) == 64:
            return tail[:12]
    except OSError:
        pass

    try:
        result = subprocess.run(
            ["grep", "overlay", "/proc/self/mountinfo"],
            capture_output=True, stdin=subprocess.DEVNULL, check=True,
        )
        mount = result.stdout.decode()
        start = mount.index("upperdir=") + len("upperdir=")
        end = mount.index(",", start)
        cid = mount[start:end].rsplit("/", 2)[1]
        if len(cid) == 64:
            return cid[:12]
    except (subprocess.CalledProcessError, ValueError, OSError):
        pass

    seed = hostname or os.environ.get("HOSTNAME", "") or "unknown-host"
    return hashlib.sha256(seed.encode()).hexdigest()[:12]


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
