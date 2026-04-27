"""
Regression tests for issue #30: path traversal via --output-dir in batch mode.

https://github.com/AgriciDaniel/claude-ads/issues/30

scripts/generate_image.py sanitises filenames inside batch jobs (Path(...).name)
but did not validate the --output-dir argument itself, so a path like
"/tmp/../../etc/cron.d" resolved outside the working directory would be
created and written to.

These tests pin the behaviour of the new _validate_output_dir() helper:
  - reject paths that resolve outside the working directory
  - allow paths that resolve inside it
  - honour the CLAUDE_ADS_OUTPUT_BASE env var as an explicit override

Run with:
    python -m unittest tests.test_output_dir_validation
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_image import _validate_output_dir  # noqa: E402


class ValidateOutputDirTest(unittest.TestCase):
    def test_rejects_relative_traversal(self):
        with self.assertRaises(ValueError):
            _validate_output_dir("../../etc")

    def test_rejects_traversal_with_absolute_prefix(self):
        # Reporter's exact example from issue #30
        with self.assertRaises(ValueError):
            _validate_output_dir("/tmp/../../etc/cron.d")

    def test_rejects_absolute_outside_cwd(self):
        with self.assertRaises(ValueError):
            _validate_output_dir("/etc/cron.d")

    def test_allows_relative_within_cwd(self):
        result = _validate_output_dir("./ad-assets")
        self.assertTrue(
            str(result).startswith(str(Path.cwd().resolve())),
            f"Expected {result} to be under {Path.cwd().resolve()}",
        )

    def test_allows_dot(self):
        result = _validate_output_dir(".")
        self.assertEqual(result, Path(".").resolve())

    def test_env_var_overrides_base(self):
        with tempfile.TemporaryDirectory() as base:
            with mock.patch.dict(os.environ, {"CLAUDE_ADS_OUTPUT_BASE": base}):
                target = str(Path(base) / "ads")
                result = _validate_output_dir(target)
                self.assertTrue(
                    str(result).startswith(str(Path(base).resolve())),
                    f"Expected {result} under override base {Path(base).resolve()}",
                )

    def test_env_var_does_not_allow_escape_above_override(self):
        with tempfile.TemporaryDirectory() as base:
            with mock.patch.dict(os.environ, {"CLAUDE_ADS_OUTPUT_BASE": base}):
                with self.assertRaises(ValueError):
                    _validate_output_dir(str(Path(base) / ".." / "escaped"))


if __name__ == "__main__":
    unittest.main()
