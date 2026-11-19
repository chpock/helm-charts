#!/usr/bin/env bash
# Publish the validated archive. The workflow is the sole writer for its GHCR tags.
set -euo pipefail

archive=$1
chart=${GITHUB_REF_NAME#release/}
name=${chart%/*}
version=${chart##*/}
repository=${GITHUB_REPOSITORY,,}/$name
[[ $(basename "$archive") == "$name-$version.tgz" ]]

bearer=$(curl --fail --silent --show-error --user "$GITHUB_ACTOR:$GH_TOKEN" \
  --get --data-urlencode service=ghcr.io --data-urlencode "scope=repository:$repository:pull,push" \
  https://ghcr.io/token | jq -ers '.[0].token | select(type == "string" and length > 0)')
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
# Helm encodes SemVer build metadata (+) as an underscore in OCI tags.
# GHCR can return MANIFEST_UNKNOWN for an existing index excluded by Accept.
accept='application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json'
accept+=', application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json'
status=$(curl --silent --show-error --output "$manifest" --write-out '%{http_code}' \
  --header "Authorization: Bearer $bearer" --header "Accept: $accept" \
  "https://ghcr.io/v2/$repository/manifests/${version//+/_}")
case $status in
  200)
    digest="sha256:$(sha256sum "$archive" | cut -d' ' -f1)"
    if jq -es --arg digest "$digest" \
      'length == 1 and (.[0] | (.mediaType // "application/vnd.oci.image.manifest.v1+json") == "application/vnd.oci.image.manifest.v1+json"
        and .config.mediaType == "application/vnd.cncf.helm.config.v1+json"
        and ([.layers[] | select(.mediaType == "application/vnd.cncf.helm.chart.content.v1.tar+gzip") | .digest] == [$digest]))' \
      "$manifest" >/dev/null; then
      echo 'The validated package is already published; skipping push.'
      exit 0
    fi
    echo "Refusing to replace $repository:$version" >&2; exit 1 ;;
  404)
    jq -es 'length == 1 and (.[0].errors | length > 0 and all(.[]; .code == "MANIFEST_UNKNOWN" or .code == "NAME_UNKNOWN"))' \
      "$manifest" >/dev/null || { echo 'Unexpected registry 404 response' >&2; exit 1; } ;;
  *) echo "Cannot verify GHCR tag availability (HTTP $status); not publishing" >&2; exit 1 ;;
esac

printf '%s' "$GH_TOKEN" | helm registry login ghcr.io --username "$GITHUB_ACTOR" --password-stdin
helm push "$archive" "oci://ghcr.io/${GITHUB_REPOSITORY,,}"
