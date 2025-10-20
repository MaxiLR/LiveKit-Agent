"""Top-level package for LiveKit agent utilities."""

from importlib.metadata import PackageNotFoundError, version

for _candidate in ("livekit-agent-backend", "livekit-agent"):
    try:
        __version__ = version(_candidate)
        break
    except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
        continue
else:
    __version__ = "0.0.0"

__all__ = ["__version__"]
