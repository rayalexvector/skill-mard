"""Exercise an installed copy from an unrelated directory using synthetic media."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import pymupdf
from PIL import Image


class InstallationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mard install ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = Path(__file__).resolve().parents[1]
        self.installed = self.root / "custom skill location"
        for folder in ("scripts", "references"):
            shutil.copytree(source / folder, self.installed / folder)
        self.work = self.root / "unrelated working directory"
        self.work.mkdir()
        self.env = os.environ.copy()
        self.env.pop("MARD221_PALETTE", None)
        self.input = self.work / "white.png"
        Image.new("RGB", (12, 8), "white").save(self.input)

    def run_generator(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, str(self.installed / "scripts/mard221_printable_pattern.py"),
             str(self.input), "--size", "12x8", "--section-size", "10",
             "--output-prefix", str(self.work / "output/pattern"), *args],
            cwd=self.work, env=self.env, capture_output=True, text=True, timeout=90,
        )
        if not success:
            self.assertNotEqual(result.returncode, 0)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_default_palette_and_deliverables(self):
        result = self.run_generator()
        self.assertEqual((result["width"], result["height"], result["beads"]), ("12", "8", "96"))
        with Path(result["counts"]).open(encoding="utf-8-sig", newline="") as stream:
            counts = list(csv.DictReader(stream))
        self.assertEqual(sum(int(row["count"]) for row in counts), 96)
        for key in ("page1", "preview"):
            with Image.open(result[key]) as image:
                image.verify()
        with pymupdf.open(result["pdf"]) as document:
            self.assertEqual(document.page_count, 3)  # Cover plus two sections.
            for page in document:
                png = page.get_pixmap(matrix=pymupdf.Matrix(0.25, 0.25)).tobytes("png")
                self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_blank_white_is_opt_in(self):
        result = self.run_generator("--blank-white")
        self.assertEqual(result["beads"], "0")
        with pymupdf.open(result["pdf"]) as document:
            self.assertEqual(document.page_count, 3)

    def test_missing_override_fails_and_cli_takes_precedence(self):
        self.env["MARD221_PALETTE"] = str(self.root / "missing.json")
        failed = self.run_generator(success=False)
        self.assertIn("FileNotFoundError", failed.stderr)
        result = self.run_generator("--palette", str(self.installed / "references/mard221_palette.json"))
        self.assertEqual(result["beads"], "96")


if __name__ == "__main__":
    unittest.main()
