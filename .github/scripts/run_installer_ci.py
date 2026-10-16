#!/usr/bin/env python3
"""Run one deterministic shard of the repository's native installer tests."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    import pytest


ROOT = Path(__file__).resolve().parents[2]
NATIVE_TEST_PATHS = (
    "tests/scripts/test_installer_security.py",
    "tests/scripts/test_privacy_outputs.py",
)
SELECTION_ALGORITHM = "canonical-relative-nodeid-sorted-round-robin-v1"
RUNNER_PATH = ".github/scripts/run_installer_ci.py"


class RunnerEnvironmentError(RuntimeError):
    """Raised when repository CI prerequisites are unavailable."""


class ShardConfigurationError(ValueError):
    """Raised when a shard cannot select an exact, nonempty test partition."""


@dataclass(frozen=True)
class ShardPlan:
    """A validated deterministic partition of canonical pytest nodeids."""

    collected: tuple[str, ...]
    selected: tuple[str, ...]
    deselected: tuple[str, ...]


def validate_source_checkout(root: Path = ROOT) -> None:
    """Require the complete repository sources before importing pytest."""

    required_paths = (
        Path("pyproject.toml"),
        Path("requirements-dev.lock"),
        Path(RUNNER_PATH),
        *(Path(path) for path in NATIVE_TEST_PATHS),
    )
    missing = [path.as_posix() for path in required_paths if not (root / path).is_file()]
    if missing:
        raise RunnerEnvironmentError(
            "complete repository source checkout required; missing: "
            + ", ".join(missing)
        )


def load_pytest() -> Any:
    """Load the reviewed CI test dependency with an actionable error."""

    try:
        return importlib.import_module("pytest")
    except ModuleNotFoundError as exc:
        if exc.name != "pytest":
            raise
        raise RunnerEnvironmentError(
            "pytest is required for native installer CI; install the reviewed "
            "exact-hash dependencies from requirements-dev.lock"
        ) from exc


def canonical_nodeid(nodeid: str) -> str:
    """Return a repository-relative, slash-normalized pytest nodeid."""

    path_text, separator, test_suffix = nodeid.partition("::")
    path = PurePosixPath(path_text.replace("\\", "/"))
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ShardConfigurationError(f"unsafe pytest nodeid path: {nodeid!r}")
    canonical_path = path.as_posix()
    if canonical_path not in NATIVE_TEST_PATHS:
        raise ShardConfigurationError(
            f"pytest collected a path outside the native installer inventory: {canonical_path}"
        )
    return canonical_path + (separator + test_suffix if separator else "")


def build_shard_plan(
    nodeids: Sequence[str], *, shard_index: int, shard_count: int
) -> ShardPlan:
    """Validate and partition nodeids by sorted-position round robin."""

    if shard_count <= 0:
        raise ShardConfigurationError("shard count must be a positive integer")
    if shard_index < 0 or shard_index >= shard_count:
        raise ShardConfigurationError(
            f"shard index must be between 0 and {shard_count - 1}"
        )

    collected = tuple(sorted(canonical_nodeid(nodeid) for nodeid in nodeids))
    if not collected:
        raise ShardConfigurationError("pytest collected no native installer tests")
    if len(set(collected)) != len(collected):
        raise ShardConfigurationError(
            "pytest collected duplicate native installer nodeids"
        )

    selected = collected[shard_index::shard_count]
    if not selected:
        raise ShardConfigurationError(
            "the requested shard selected no native installer tests"
        )
    selected_set = set(selected)
    deselected = tuple(nodeid for nodeid in collected if nodeid not in selected_set)

    if selected_set.intersection(deselected):
        raise ShardConfigurationError("selected and deselected nodeids overlap")
    if selected_set.union(deselected) != set(collected):
        raise ShardConfigurationError(
            "selected and deselected nodeids do not reproduce the full inventory"
        )
    if len(selected) + len(deselected) != len(collected):
        raise ShardConfigurationError(
            "selected and deselected counts do not reproduce the full inventory"
        )

    return ShardPlan(
        collected=collected,
        selected=selected,
        deselected=deselected,
    )


class InstallerShardPlugin:
    """Select a shard during collection and emit an exact inventory manifest."""

    def __init__(
        self,
        *,
        shard_index: int,
        shard_count: int,
        output: Path,
        collect_only: bool,
        pytest_module: Any,
    ) -> None:
        self.shard_index = shard_index
        self.shard_count = shard_count
        self.output = output
        self.collect_only = collect_only
        self.pytest = pytest_module
        self.plan: ShardPlan | None = None
        self.validation_error: str | None = None

    def pytest_collection_modifyitems(
        self, config: pytest.Config, items: list[pytest.Item]
    ) -> None:
        try:
            self.plan = build_shard_plan(
                [item.nodeid for item in items],
                shard_index=self.shard_index,
                shard_count=self.shard_count,
            )
        except ShardConfigurationError as exc:
            self.validation_error = str(exc)
            raise self.pytest.UsageError(str(exc)) from exc

        selected_nodeids = set(self.plan.selected)
        selected_items: list[pytest.Item] = []
        deselected_items: list[pytest.Item] = []
        for item in items:
            canonical = canonical_nodeid(item.nodeid)
            destination = (
                selected_items if canonical in selected_nodeids else deselected_items
            )
            destination.append(item)

        if (
            len(selected_items) != len(self.plan.selected)
            or len(deselected_items) != len(self.plan.deselected)
        ):
            self.validation_error = (
                "pytest item partition does not match the shard plan"
            )
            raise self.pytest.UsageError(self.validation_error)

        items[:] = selected_items
        if deselected_items:
            config.hook.pytest_deselected(items=deselected_items)

    def pytest_sessionfinish(
        self, session: pytest.Session, exitstatus: int | pytest.ExitCode
    ) -> None:
        document: dict[str, object] = {
            "schema_version": "1.0.0",
            "runner": RUNNER_PATH,
            "test_paths": list(NATIVE_TEST_PATHS),
            "mode": "collect-only" if self.collect_only else "execute",
            "selection": {
                "algorithm": SELECTION_ALGORITHM,
                "shard_index": self.shard_index,
                "shard_count": self.shard_count,
                "execution_order": "original-pytest-collection-order",
            },
            "pytest_exit_code": int(exitstatus),
            "validation_status": "valid" if self.plan is not None else "invalid",
        }
        if self.plan is not None:
            document.update(
                {
                    "counts": {
                        "collected": len(self.plan.collected),
                        "selected": len(self.plan.selected),
                        "deselected": len(self.plan.deselected),
                    },
                    "collected_nodeids": list(self.plan.collected),
                    "selected_nodeids": list(self.plan.selected),
                    "deselected_nodeids": list(self.plan.deselected),
                }
            )
        else:
            document["validation_error"] = (
                self.validation_error or "collection did not complete"
            )

        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_name(f".{self.output.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Collect and validate this shard without executing its tests.",
    )
    args = parser.parse_args(argv)
    if args.shard_count <= 0:
        parser.error("--shard-count must be a positive integer")
    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        parser.error("--shard-index must be within [0, --shard-count)")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_source_checkout()
        pytest_module = load_pytest()
    except RunnerEnvironmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    plugin = InstallerShardPlugin(
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        output=args.output.resolve(),
        collect_only=args.collect_only,
        pytest_module=pytest_module,
    )
    pytest_args = [*NATIVE_TEST_PATHS, "-v", "--tb=short"]
    if args.collect_only:
        pytest_args.append("--collect-only")

    previous_cwd = Path.cwd()
    try:
        os.chdir(ROOT)
        return int(pytest_module.main(pytest_args, plugins=[plugin]))
    finally:
        os.chdir(previous_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
