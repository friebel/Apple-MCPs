import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast

SafetyMode = Literal["safe_readonly", "safe_manage", "full_access"]
VALID_SAFETY_MODES = frozenset({"safe_readonly", "safe_manage", "full_access"})

DEFAULT_SCRIPT_TIMEOUT_SECONDS = 120
MIN_SCRIPT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class Settings:
    server_name: str
    version: str
    safety_mode: SafetyMode
    log_level: str
    transport: str
    host: str
    port: int
    script_path: Path
    script_timeout_seconds: int
    allowed_roots: tuple[Path, ...]


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_timeout(value: str | None) -> int:
    parsed = _parse_int(value, DEFAULT_SCRIPT_TIMEOUT_SECONDS)
    return parsed if parsed >= MIN_SCRIPT_TIMEOUT_SECONDS else DEFAULT_SCRIPT_TIMEOUT_SECONDS


def _default_roots() -> tuple[Path, ...]:
    home = Path.home()
    candidates = (
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "Library" / "Mobile Documents" / "com~apple~CloudDocs",
    )
    existing = [path for path in candidates if path.exists()]
    return tuple(existing or [home / "Downloads"])


def _parse_roots(value: str | None) -> tuple[Path, ...]:
    # Spreadsheets are opened and exported only inside these folders. With no
    # Numbers setting this follows the Files server's allowed roots, then the
    # same defaults, so the unified server keeps one set of allowed folders.
    roots = tuple(Path(raw.strip()).expanduser() for raw in (value or "").split(",") if raw.strip())
    return roots or _default_roots()


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    package_dir = Path(__file__).resolve().parent
    raw_safety_mode = os.environ.get("APPLE_NUMBERS_MCP_SAFETY_MODE", "full_access").strip()
    if raw_safety_mode not in VALID_SAFETY_MODES:
        raw_safety_mode = "safe_readonly"

    return Settings(
        server_name="Apple Numbers MCP",
        version="1.1.6",
        safety_mode=cast(SafetyMode, raw_safety_mode),
        log_level=os.environ.get("APPLE_NUMBERS_MCP_LOG_LEVEL", "INFO").strip().upper() or "INFO",
        transport=os.environ.get("APPLE_NUMBERS_MCP_TRANSPORT", "stdio").strip() or "stdio",
        host=os.environ.get("APPLE_NUMBERS_MCP_HOST", "127.0.0.1"),
        port=_parse_int(os.environ.get("APPLE_NUMBERS_MCP_PORT"), 8000),
        script_path=package_dir / "scripts" / "numbers.js",
        script_timeout_seconds=_parse_timeout(os.environ.get("APPLE_NUMBERS_MCP_SCRIPT_TIMEOUT_SECONDS")),
        allowed_roots=_parse_roots(
            os.environ.get("APPLE_NUMBERS_MCP_ALLOWED_ROOTS") or os.environ.get("APPLE_FILES_MCP_ALLOWED_ROOTS")
        ),
    )
