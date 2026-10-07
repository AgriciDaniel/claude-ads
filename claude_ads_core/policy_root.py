"""Resolve installed control-plane resources without trusting the working directory."""

from __future__ import annotations

from pathlib import Path


class PolicyRootError(ValueError):
    """Raised when the canonical control-plane root cannot be resolved."""


def _validate_policy_root(root: Path) -> Path:
    resolved = root.expanduser().resolve()
    manifests = resolved / "control-plane" / "manifests"
    if not manifests.is_dir():
        raise PolicyRootError(
            f"policy root {resolved} does not contain control-plane/manifests"
        )
    return resolved


def resolve_policy_root(
    explicit: str | Path | None = None,
    *,
    module_path: str | Path | None = None,
) -> Path:
    """Return the source or standalone runtime root.

    Supported automatic layouts are ``ROOT/claude_ads_core`` for a source or
    wheel checkout and ``ROOT/scripts/claude_ads_core`` for a standalone skill.
    The ambient current working directory is deliberately ignored.
    """

    if explicit is not None:
        if isinstance(explicit, str) and not explicit.strip():
            raise PolicyRootError("--policy-root must be a non-empty path")
        return _validate_policy_root(Path(explicit))

    module_dir = Path(module_path or __file__).resolve().parent
    root = module_dir.parent.parent if module_dir.parent.name == "scripts" else module_dir.parent
    try:
        return _validate_policy_root(root)
    except PolicyRootError as exc:
        raise PolicyRootError(
            "cannot locate control-plane resources from the installed runtime; "
            "supply --policy-root ROOT"
        ) from exc
