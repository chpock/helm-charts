# Helm chart repository

This repository maintains third-party Helm charts with local changes. Each chart has its own version, changelog, and release cycle. Changes from the vendor's original chart (the **upstream** chart) are selected and applied by hand; updating one chart does not require releasing the others.

- [Chart layout](chart-layout.md): where to find the chart sources, downstream instructions, and original vendor documents; what goes into a package.
- [Imports and updates](maintenance.md): how to preserve the original snapshot, record its version, port an individual fix, or move to a new upstream base.
- [Builds and releases](releases.md): how to prepare the changelog, check the package, and select a chart for publication with a Git tag.

Repository-wide guides live in `docs/`. Each chart keeps its sources and installation instructions together in `charts/<name>/`. The proposed GitHub Actions workflows are shared across charts: `.github/workflows/ci.yaml` for checks and `.github/workflows/release.yaml` for tag-triggered publication.

## Available charts

- [Thanos](../charts/thanos/README.md) is based on the Bitnami chart and can be installed from source. Automated package publication is not yet configured.
