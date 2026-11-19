# Builds and releases

Each release belongs to one chart. Its Git tag is `release/<chart-name>/<package-version>`. For example, `release/thanos/1.0.0` selects Thanos; it neither sets the application version nor releases any other chart. The following describes the release workflow contract. Automated publication is not yet configured.

## Preparing a release

1. Set `version` in `charts/<name>/Chart.yaml` to the package version. A tag confirms the version already in Git; the build must not substitute a run number or override the version from the tag.
2. In `charts/<name>/CHANGELOG.md`, move the relevant entries from `Unreleased` into a section with the exact release version, for example `## 1.0.0`. Keep earlier sections. Describe what users will see and any action required when upgrading.
3. Tag the commit that contains both the correct version and the finished notes. The release notes come **only from the matching section of the downstream changelog at that tag**, not from `upstream/` or a repository-wide list of PRs.

## Checking a package

Check affected charts on pull requests. If shared build logic changes, include all charts that use it. Before publishing, repeat the checks against the selected chart at the tagged commit.

- For Thanos, run `helm dependency build charts/thanos` using the committed `Chart.lock`. Without the lock, `build` resolves new versions like `helm dependency update`; stop the release build rather than silently using them. A lock file cannot guarantee that a vendor still serves the dependency archives.
- Run `helm lint`, render the chart with settings that exercise the changes, and build the `.tgz` with `helm package`. Inspect the **archive itself**: verify the package name and version, upstream coordinates, dependencies, license, and required notices. The chart-root `README.md` and `CHANGELOG.md` must be ours. No files from the chart's `upstream/` directory should be present.
- Successful rendering does not prove that Kubernetes can pull the workload images. Before claiming a working default installation, test it with the same image access a consumer will have.

## Publishing by tag

The shared release workflow must select exactly one chart, match its name and version to the tag, and find exactly one nonempty changelog section for that version. An unknown chart, mismatched version, failed package check, or ambiguous release notes must stop publication.

Publish only the validated package for the selected chart. Create a GitHub Release for the same Git tag using the extracted changelog section. Do not overwrite a published package version: if the package was uploaded but creating the GitHub Release failed, retry only the unfinished step. For the first release, pull the package as an intended consumer, inspect and render it, and compare the GitHub Release body with the tagged changelog section.

## Where to obtain packages

The publication endpoint and its visibility (public or private) have not been chosen. The proposed transport is OCI in GitHub Container Registry: it uses the name and version from `Chart.yaml` and does not need an `index.yaml`. Consumers that require `helm repo add` need a classic HTTP chart repository with an `index.yaml` instead. Until an endpoint is selected and the first package verified, there is no published install URL.
