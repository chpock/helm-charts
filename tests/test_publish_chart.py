import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("scripts/publish-chart.sh").resolve()


class RegistryPublication(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "example-1.0.0+build.tgz"
        self.archive.write_bytes(b"validated chart package")
        self.env = dict(
            os.environ,
            PATH=f"{self.root}:{os.environ['PATH']}",
            GITHUB_REPOSITORY="Owner/Charts",
            GITHUB_ACTOR="tester",
            GH_TOKEN="test",
            GITHUB_REF_NAME="release/example/1.0.0+build",
        )
        self.tool(
            "curl",
            """
case "${!#}" in
  https://ghcr.io/token) echo '{"token":"registry-token"}';;
  https://ghcr.io/v2/owner/charts/example/manifests/1.0.0_build)
    if [[ $STATUS == existing-index ]]; then
      accept=''
      args=("$@")
      for arg in "${args[@]}"; do [[ $arg != 'Accept: '* ]] || accept=$arg; done
      if [[ $accept == *"$INDEX_TYPE"* ]]; then
        BODY='{"schemaVersion":2,"manifests":[]}'; STATUS=200
      else
        BODY='{"errors":[{"code":"MANIFEST_UNKNOWN"}]}'; STATUS=404
      fi
    fi
    while [[ $1 != --output ]]; do shift; done
    printf '%s' "$BODY" > "$2"
    printf '%s' "$STATUS";;
  *) exit 2;;
esac
""",
        )
        self.tool("helm", 'printf "%s\\n" "$*" >> helm-calls\n')

    def tool(self, name, body):
        path = self.root / name
        path.write_text("#!/usr/bin/env bash\nset -eu\n" + body)
        path.chmod(0o755)

    def publish(self, status, body):
        result = subprocess.run(
            ["bash", SCRIPT, self.archive],
            cwd=self.root,
            capture_output=True,
            env=dict(self.env, STATUS=str(status), BODY=body),
            text=True,
        )
        log = self.root / "helm-calls"
        return result, log.read_text().splitlines() if log.exists() else []

    def test_only_confirmed_absence_allows_a_push(self):
        result, calls = self.publish(404, '{"errors":[{"code":"MANIFEST_UNKNOWN"}]}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            [
                "registry login ghcr.io --username tester --password-stdin",
                f"push {self.archive} oci://ghcr.io/owner/charts",
            ],
        )

    def test_fail_closed_without_a_write(self):
        for status, body in [
            (401, "{}"),
            (403, "{}"),
            (500, "{}"),
            (404, "{}"),
            (404, ""),
            (404, '{"errors":[{"code":"DENIED"}]}'),
            (200, '{"layers":[]}'),
        ]:
            with self.subTest(status=status, body=body):
                result, calls = self.publish(status, body)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_existing_manifest_lists_are_not_mistaken_for_free_tags(self):
        for media in [
            "application/vnd.oci.image.index.v1+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.docker.distribution.manifest.v2+json",
        ]:
            with self.subTest(media=media):
                self.env["INDEX_TYPE"] = media
                result, calls = self.publish("existing-index", "")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_retry_does_not_push_the_same_archive_again(self):
        layer = {
            "mediaType": "application/vnd.cncf.helm.chart.content.v1.tar+gzip",
            "digest": "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest(),
        }
        manifest = {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"mediaType": "application/vnd.cncf.helm.config.v1+json"},
            "layers": [layer],
        }
        for include_media in (True, False):
            with self.subTest(manifest_media_type_present=include_media):
                body = {
                    k: v
                    for k, v in manifest.items()
                    if k != "mediaType" or include_media
                }
                result, calls = self.publish(200, json.dumps(body))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, [])
        result, calls = self.publish(
            200,
            json.dumps(
                {
                    **manifest,
                    "config": {"mediaType": "application/vnd.oci.image.config.v1+json"},
                }
            ),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.archive.write_bytes(b"different bytes for the same version")
        result, calls = self.publish(200, json.dumps(manifest))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
