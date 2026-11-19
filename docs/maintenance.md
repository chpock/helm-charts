# Imports and updates

## Upstream base and chart versions

The **base** is the exact vendor commit against which we maintain our chart. It is neither the last commit reviewed nor the most recent fix backported. Record the vendor repository URL, the chart's path within it, the full commit SHA, and the version in the vendor's `Chart.yaml` at that commit.

Store these coordinates in `Chart.yaml` annotations so consumers can inspect them with `helm show chart` even without a checkout. This excerpt illustrates the fields; the package version is an example, not a release. Preserve the vendor's existing annotations when adding ours.

```yaml
name: thanos
version: "1.0.0"       # Downstream package version (example)
appVersion: "0.39.2"   # Thanos application version
annotations:
  chpock.github.io/upstream-repository: "https://github.com/bitnami/charts"
  chpock.github.io/upstream-path: "bitnami/thanos"
  chpock.github.io/upstream-commit: "2aac71a990b7e7c9a882bdce59855022894ac361"
  chpock.github.io/upstream-chart-version: "17.6.0"
```

The proposed convention is to version the downstream chart independently using SemVer. A template fix can change `version` without changing `appVersion` or the upstream base. Build metadata such as `+patch.2` has no precedence over `+patch.1`; `-patch.1` denotes a prerelease. `Chart.lock` serves a separate purpose: it records dependency versions, not the upstream source commit or downstream package version.

## First import

1. Select a specific vendor commit instead of a moving branch. Copy the chart directory unmodified in a dedicated commit. Record the repository, path, full SHA, and upstream chart version in the commit message. Compare the result with the vendor directory (when Git object formats match, compare the subtree IDs).
2. In the next commit, [separate our documents from the originals](chart-layout.md), add the base metadata, identify the downstream maintainer, and document how to install **our package**. Check for license texts and notices outside the chart directory: for Bitnami Thanos, `LICENSE.md` is at the vendor repository root. Retain applicable notices and mark modified files as the license requires.
3. Make functional changes directly in the working chart. Keep the clean import separate from subsequent commits so the original snapshot remains available even if the vendor repository disappears.

## Reviewing and applying upstream changes

In the **vendor checkout**, set `BASE` to the recorded upstream commit and `TARGET` to the later commit you want to review. For Thanos:

```sh
git log --reverse "${BASE}..${TARGET}" -- bitnami/thanos
git diff "$BASE" "$TARGET" -- bitnami/thanos
```

The first command lists commits touching the chart. The second shows the net difference between the two snapshots. Read the full commit when a change also affects shared code, a dependency, or a license outside the chart directory. Do not copy a new vendor tree over the working chart: doing so could overwrite our templates and documentation.

| Operation | What to record |
| --- | --- |
| Backport one fix | Reference the exact upstream SHA in the downstream commit. Leave the base SHA, base chart version, and `upstream/` snapshot unchanged. |
| Adopt a new base | Review the entire range. Record the range and deliberate differences in the sync commit. In the same change, update the base SHA and upstream chart version and refresh the retained `upstream/` files from that snapshot. |

If changes were only reviewed or deferred, say so in the commit or PR rather than treating the last reviewed SHA as the new base. In both cases, verify local fixes still work, incorporate applicable instructions in our README, and describe user-visible effects in our `CHANGELOG.md`. The release notes are not a list of skipped commits.
