import copy
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from scripts import chart_ci as ci


class ReleaseContracts(unittest.TestCase):
    def test_tag_selects_only_its_exact_directory_name_and_version(self):
        with tempfile.TemporaryDirectory() as root:
            chart = Path(root) / "one"
            chart.mkdir()
            manifest = chart / "Chart.yaml"
            manifest.write_text("name: one\nversion: 2.0.1\n")
            self.assertEqual(ci.release_chart(Path(root), "release/one/2.0.1"), chart)
            for tag in [
                "release/one/2.0.0",
                "release/two/2.0.1",
                "release/../2.0.1",
                "release/one/2.0.1/extra",
                "release/one/v2.0.1",
            ]:
                with self.subTest(tag=tag), self.assertRaises(ValueError):
                    ci.release_chart(Path(root), tag)
            manifest.write_text("name: two\nversion: 2.0.1\n")
            with self.assertRaises(ValueError):
                ci.release_chart(Path(root), "release/one/2.0.1")

    def test_only_the_matching_real_section_is_released(self):
        log = "## Unreleased\nnext\n\n## 2.0.1\n\n- updated\n### Upgrade\nkeep\n```md\n## Example\n```\n\n## 2.0.0\nold\n"
        self.assertEqual(
            ci.notes(log, "2.0.1"),
            "- updated\n### Upgrade\nkeep\n```md\n## Example\n```\n",
        )
        for invalid in [
            "## Unreleased\nnext",
            "## 2.0.1\n\n## 2.0.0\nold",
            log + "\n## 2.0.1\nagain",
            "```md\n## 2.0.1\nexample\n```",
        ]:
            with self.subTest(log=invalid), self.assertRaises(ValueError):
                ci.notes(invalid, "2.0.1")

    def test_selection_checks_shared_inputs_and_skips_unrelated_or_deleted_charts(self):
        available = {"one", "two"}
        self.assertEqual(ci.affected(["docs/releases.md"], available), [])
        self.assertEqual(
            ci.affected(
                ["charts/gone/values.yaml", "charts/two/values.yaml"], available
            ),
            ["two"],
        )
        self.assertEqual(
            ci.affected(["tests/values/two/storegateway.yaml"], available), ["two"]
        )
        for path in [
            "scripts/chart_ci.py",
            ".github/workflows/ci.yaml",
            "tests/test_chart_ci.py",
        ]:
            self.assertEqual(ci.affected([path], available), ["one", "two"])

    def test_archive_checks_the_shipped_files_not_just_the_source(self):
        manifest = {
            "name": "one",
            "version": "1.0.0",
            "annotations": {
                "chpock.github.io/upstream-" + k: v
                for k, v in [
                    ("commit", "a" * 40),
                    ("repository", "https://example.org/repo"),
                    ("path", "one"),
                    ("chart-version", "9.0.0"),
                ]
            },
        }
        import json

        with tempfile.TemporaryDirectory() as root:
            chart = Path(root) / "one"
            chart.mkdir()
            files = {
                "README.md": b"downstream readme",
                "CHANGELOG.md": b"our releases",
                "LICENSE": b"license",
            }
            for k, v in files.items():
                (chart / k).write_bytes(v)

            def check(change):
                contents = {
                    **files,
                    "Chart.yaml": json.dumps(manifest).encode(),
                    **change,
                }
                out = chart.parent / "one.tgz"
                with tarfile.open(out, "w:gz") as tar:
                    for k, v in contents.items():
                        if v is None:
                            continue
                        m = tarfile.TarInfo("one/" + k)
                        m.size = len(v)
                        tar.addfile(m, io.BytesIO(v))
                ci.check_package(chart, out, manifest)

            check({})
            wrong = copy.deepcopy(manifest)
            wrong["version"] = "2.0.0"
            for delta in [
                {"upstream/README.md": b"vendor"},
                {"CHANGELOG.md": None},
                {"README.md": b"vendor"},
                {"LICENSE": None},
                {"Chart.yaml": json.dumps(wrong).encode()},
            ]:
                with self.subTest(delta=delta), self.assertRaises(ValueError):
                    check(delta)
