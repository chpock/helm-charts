# Thanos Helm chart

This chart deploys Thanos components on Kubernetes. Package version `18.0.0` starts this repository's version series; it is based on Bitnami chart `17.6.0` and deploys Thanos `0.39.2`. The package version change does not upgrade Thanos. The import preserves the vendor templates, defaults, dependencies, and image references.

## Published packages

For a version listed on the [GitHub Releases page](https://github.com/chpock/helm-charts/releases), install `oci://ghcr.io/chpock/helm-charts/thanos` instead of the local `charts/thanos` directory and pass `--version <published-version>`. The package includes its chart dependencies. The image and storage requirements below still apply.

## Installing from source

Use Helm 3.8 or later and Kubernetes 1.23 or later. Components that use persistent volumes need suitable storage. The cluster also needs access to the container images of the components you enable. Docker Hub returned HTTP 404 for an anonymous request for the default image manifest, `docker.io/bitnami/thanos:0.39.2-debian-12-r2`. Building the chart does not pull that image. Before deploying, verify access from your cluster and configure an accessible, compatible image under `image` in your values file if necessary.

From the root of this repository:

```sh
helm dependency build charts/thanos
helm template monitoring charts/thanos --namespace monitoring
helm install monitoring charts/thanos --namespace monitoring --create-namespace
```

The first command fetches `common` and `minio` at the versions recorded in `Chart.lock`. The second lets you inspect the manifests without installing them. To supply your own settings, pass `-f my-values.yaml` to both `template` and `install`. Use `helm show values charts/thanos` to read the defaults and parameter descriptions.

## Upgrading and identifying the base

Read the [downstream changelog](CHANGELOG.md), rebuild dependencies after changing the source version, and render the chart with the values, release name, and namespace used by your deployment. To upgrade the release above using your own values file:

```sh
helm upgrade monitoring charts/thanos --namespace monitoring -f my-values.yaml
```

Use `helm show chart` on the chart directory or the `.tgz` to read the upstream commit and chart version from its annotations. The Git checkout also includes the original Bitnami instructions and release history under `upstream/`. That directory is excluded from the Helm package; the vendor license is included as `LICENSE`.

## Attribution

The upstream chart is distributed by Bitnami. Its original trademark notice reads:

> Trademarks: This software listing is packaged by Bitnami. The respective trademarks mentioned in the offering are owned by the respective companies, and use of them does not imply any affiliation or endorsement.
