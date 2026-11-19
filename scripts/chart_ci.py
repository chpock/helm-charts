"""Build the chart(s) selected by a pull request, branch update, or release tag."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


CHARTS = Path("charts")
NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NUMBER = r"(?:0|[1-9][0-9]*)"
PRE = rf"(?:{NUMBER}|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)"
VERSION = rf"{NUMBER}\.{NUMBER}\.{NUMBER}(?:-{PRE}(?:\.{PRE})*)?(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def yaml(data):
    return json.loads(subprocess.check_output(["yq", "-o=json", ".", "-"], input=data))


def release_chart(root, tag):
    match = re.fullmatch(rf"release/({NAME})/({VERSION})", tag)
    if match is None:
        raise ValueError(f"Invalid release tag: {tag}")
    name, version = match.groups()
    chart = root / name
    require((chart / "Chart.yaml").is_file(), f"Unknown chart: {name}")
    meta = yaml((chart / "Chart.yaml").read_bytes())
    require(
        (name, version) == (meta["name"], meta["version"]),
        f"{tag} does not match Chart.yaml",
    )
    return chart


def notes(text, version):
    sections = []
    current = None
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if not fence and re.match(r"^##(?:\s|$)", line):
            current = None
            if line.rstrip() == f"## {version}":
                current = []
                sections.append(current)
        elif current is not None:
            current.append(line)
        if marker:
            run, rest = marker.groups()
            if not fence:
                fence = run
            elif run.startswith(fence) and not rest.strip():
                fence = ""
    require(len(sections) == 1, f"Expected exactly one ## {version} changelog section")
    body = "\n".join(sections[0]).strip("\n")
    require(body.strip(), f"Empty ## {version} changelog section")
    return body + "\n"


def affected(paths, available):
    names = set()
    for path in paths:
        if path.startswith("tests/values/"):
            names.add(path.removeprefix("tests/values/").split("/", 1)[0])
        elif path.startswith(("scripts/", "tests/", ".github/workflows/")):
            return sorted(available)
        elif path.startswith("charts/"):
            names.add(path.split("/", 2)[1])
    return sorted(names & available)


def selected(base):
    available = {p.name for p in CHARTS.glob("*") if p.is_dir()}
    # A new branch or a force push can lack a reachable comparison commit.
    if (
        not base
        or set(base) == {"0"}
        or subprocess.run(
            ["git", "cat-file", "-e", f"{base}^{{commit}}"], stderr=subprocess.DEVNULL
        ).returncode
    ):
        return sorted(available)
    changes = subprocess.check_output(
        ["git", "diff", "--name-only", "--no-renames", "-z", base, "HEAD", "--"]
    )
    return affected(changes.decode(errors="surrogateescape").split("\0"), available)


def check_package(chart, archive, source):
    name = chart.name
    with tarfile.open(archive, "r:gz") as tar:
        members = set(tar.getnames())

        def read(member):
            path = f"{name}/{member}"
            require(path in members, f"Missing {path} in package")
            stream = tar.extractfile(path)
            if stream is None or not tar.getmember(path).isfile():
                raise ValueError(f"Expected a regular file: {path}")
            return stream.read()

        meta = yaml(read("Chart.yaml"))
        for key in ("name", "version", "appVersion", "annotations"):
            require(
                meta.get(key) == source.get(key), f"Packaged {key} differs from source"
            )
        ann = meta.get("annotations", {})
        for key in ("repository", "path", "commit", "chart-version"):
            value = ann.get("chpock.github.io/upstream-" + key)
            require(isinstance(value, str) and value.strip(), f"Missing upstream {key}")
            if key == "commit":
                require(
                    re.fullmatch(r"[0-9a-f]{40}", value),
                    "Expected full upstream Git SHA",
                )
        require(
            not any(
                p == f"{name}/upstream" or p.startswith(f"{name}/upstream/")
                for p in members
            ),
            "Vendor reference directory included in package",
        )
        legal = [
            p
            for p in chart.iterdir()
            if p.is_file() and p.stem.upper() in ("LICENSE", "NOTICE", "COPYING")
        ]
        require(
            any(p.stem.upper() in ("LICENSE", "COPYING") for p in legal),
            f"Missing license in {chart}",
        )
        for path in [chart / "README.md", chart / "CHANGELOG.md", *legal]:
            require(
                read(path.name) == path.read_bytes(), f"Incorrect packaged {path.name}"
            )
        if (chart / "Chart.lock").exists():
            lock = yaml((chart / "Chart.lock").read_bytes())
            require(
                yaml(read("Chart.lock")) == lock,
                "Packaged dependency lock differs from source",
            )
            for dep in lock["dependencies"]:
                actual = yaml(read(f"charts/{dep['name']}/Chart.yaml"))
                require(
                    (actual["name"], actual["version"])
                    == (dep["name"], dep["version"]),
                    f"Wrong packaged version of {dep['name']}",
                )


def build(chart, out):
    manifest = chart / "Chart.yaml"
    require(manifest.is_file(), f"Missing {manifest}")
    meta = yaml(manifest.read_bytes())
    require(
        re.fullmatch(NAME, chart.name) and meta["name"] == chart.name,
        f"Invalid chart directory: {chart}",
    )
    require(
        re.fullmatch(VERSION, str(meta["version"])),
        f"Invalid chart version: {meta['version']}",
    )
    with tempfile.TemporaryDirectory() as temp:
        src = Path(temp) / chart.name
        shutil.copytree(chart, src)
        if meta.get("dependencies") and chart.name == "thanos":
            require(
                (src / "Chart.lock").is_file(),
                f"Missing {chart}/Chart.lock; refusing to resolve new versions",
            )
        if (src / "Chart.lock").is_file():
            subprocess.run(["helm", "dependency", "build", src], check=True)
        subprocess.run(["helm", "lint", "--strict", src], check=True)
        subprocess.run(["helm", "package", src, "--destination", out], check=True)
    archive = out / f"{chart.name}-{meta['version']}.tgz"
    check_package(chart, archive, meta)
    for args in [
        [],
        *(
            ["-f", p]
            for p in sorted((Path("tests/values") / chart.name).glob("*.yaml"))
        ),
    ]:
        subprocess.run(
            ["helm", "template", "monitoring", archive, *args],
            stdout=subprocess.DEVNULL,
            check=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ci").add_argument("--base")
    release = commands.add_parser("release")
    release.add_argument("tag")
    release.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "release":
        chart = release_chart(CHARTS, args.tag)
        body = notes((chart / "CHANGELOG.md").read_text(), args.tag.split("/")[2])
        args.output.mkdir(parents=True, exist_ok=True)
        build(chart, args.output)
        (args.output / "notes.md").write_text(body)
    else:
        charts = selected(args.base)
        print("Charts to check:", ", ".join(charts) or "(none)", flush=True)
        with tempfile.TemporaryDirectory() as out:
            for name in charts:
                build(CHARTS / name, Path(out))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
