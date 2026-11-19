# Builds and releases

Each release belongs to one chart. Its Git tag is `release/<chart-name>/<package-version>`. For example, `release/thanos/1.0.0` selects Thanos; it neither sets the application version nor releases any other chart. [Release chart](../.github/workflows/release.yaml) runs when a matching tag is first pushed; updating a branch does not publish a package.

## Preparing a release

1. Set `version` in `charts/<name>/Chart.yaml` to the package version. A tag confirms the version already in Git; the build must not substitute a run number or override the version from the tag.
2. In `charts/<name>/CHANGELOG.md`, move the relevant entries from `Unreleased` into a section with the exact release version, for example `## 1.0.0`. Keep earlier sections. Describe what users will see and any action required when upgrading.
3. Tag the commit that contains both the correct version and the finished notes. The release notes come **only from the matching section of the downstream changelog at that tag**, not from `upstream/` or a repository-wide list of PRs.

## Checking a package

[Chart CI](../.github/workflows/ci.yaml) runs on pull requests and pushes to `main`. It checks charts with changed sources or render cases, or all charts when a shared workflow, build script, or test changes. Before publishing, the release workflow runs the same package checks for the tagged chart alone. To check all charts locally, run `python3 scripts/chart_ci.py ci` from the repository root with Helm and `yq` v4 on `PATH`. Additional render cases belong in `tests/values/<chart>/*.yaml`.

- For Thanos, run `helm dependency build charts/thanos` using the committed `Chart.lock`. Without the lock, `build` resolves new versions like `helm dependency update`; stop the release build rather than silently using them. A lock file cannot guarantee that a vendor still serves the dependency archives.
- Run `helm lint`, render the chart with settings that exercise the changes, and build the `.tgz` with `helm package`. Inspect the **archive itself**: verify the package name and version, upstream coordinates, dependencies, license, and required notices. The chart-root `README.md` and `CHANGELOG.md` must be ours. No files from the chart's `upstream/` directory should be present.
- Successful rendering does not prove that Kubernetes can pull the workload images. Before claiming a working default installation, test it with the same image access a consumer will have.

## Publishing by tag

1. **Build:** validate the tag, chart directory, `Chart.yaml` name and exact version, and a single nonempty `## <version>` changelog section. Build and check the package before handing the `.tgz` and extracted notes to the next jobs as a workflow artifact. To rehearse this step without publishing, run `python3 scripts/chart_ci.py release release/<chart>/<version> /path/to/empty-output-directory` on the prepared revision.
2. **Publish:** use the repository's `GITHUB_TOKEN` with `packages: write` to push the checked archive to `oci://ghcr.io/chpock/helm-charts`. If the tag exists, accept it only when its chart layer matches the validated archive byte for byte. A different package, a registry error, or insufficient access stops the job. Keep this workflow the only writer for these package names; GHCR tags are not intrinsically immutable. Protect `release/**` with GitHub tag rulesets: allow only trusted maintainers to create tags and disallow updates and deletions. Before either publishing the package or creating the GitHub Release, the workflow checks that the remote tag still resolves to the commit used to build the archive.
3. **Release:** from a separate runner, pull the package anonymously, compare it with the validated `.tgz`, and render it. Only then create the GitHub Release and verify its notes against the tagged changelog section. This job has no package write permission.

**First publication of each chart:** GHCR creates new packages as **private**, even for public repositories. After the first successful push, a package administrator must set `helm-charts/<chart>` to **Public** in its GitHub package settings. If anonymous verification has already failed, use **Re-run failed jobs** on the same run. This reuses the original archive and notes without rebuilding or overwriting the package. Use the same retry procedure after a transient failure to create the GitHub Release. If a package of that name already exists, grant the repository Actions access before publishing.

## Where to obtain packages

Use `oci://ghcr.io/chpock/helm-charts/<chart>` with an exact published version. Look for `release/<chart>/<version>` on the [GitHub Releases page](https://github.com/chpock/helm-charts/releases). For example, after Thanos `18.0.0` is released:

```sh
helm pull oci://ghcr.io/chpock/helm-charts/thanos --version 18.0.0
```

OCI does not use `helm repo add` or an `index.yaml`. A chart with only `Unreleased` notes is not ready for publication.
