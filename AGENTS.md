# Repository instructions

Write all repository documentation in English, including chart READMEs and changelogs.

## Read the guide that matches the task

- Repository scope or chart availability: [repository overview](docs/README.md).
- Chart names, file placement, or package contents: [chart layout](docs/chart-layout.md).
- Imports, provenance, versioning, backports, or a new upstream base: [maintenance](docs/maintenance.md).
- Build checks, release CI, tags, or release notes: [releases](docs/releases.md).
- Chart-specific installation, configuration, or upgrades: `charts/<chart>/README.md`. For comparison with the original vendor instructions, consult `charts/<chart>/upstream/`.

## Before completing a change

- For every chart affected by a feature or fix, check `Unreleased` in `charts/<chart>/CHANGELOG.md`. Add or correct the entry until it describes the change for users. Work that changes no chart behavior needs no chart entry.
- If installation, settings, defaults, or upgrades changed, update the affected chart's README. If a shared layout, maintenance, or release procedure changed, update the corresponding guide in `docs/`. Apply both checks when a task affects both.
