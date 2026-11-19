# Thanos chart changelog

## Unreleased

## 18.0.0

- First release of the downstream Thanos chart. Chart `18.0.0` is based on Bitnami chart `17.6.0`; the Thanos application remains at `0.39.2`. The templates, default values, and image references are unchanged.
- Pull the chart and its bundled dependencies with `helm pull oci://ghcr.io/chpock/helm-charts/thanos --version 18.0.0`. The package includes installation instructions; `helm show chart` reports the upstream commit and chart version.
- Before installing, verify that your cluster can pull `docker.io/bitnami/thanos:0.39.2-debian-12-r2`, or configure a compatible image your cluster can access. Docker Hub returned HTTP 404 for an anonymous request for the default image manifest.
