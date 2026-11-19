# Chart layout

Each Helm chart is maintained and released independently. For example, `helm package` takes `charts/thanos/`, not the repository's entire `charts/` directory. The working tree contains the chart with our changes applied; building it does not require applying patches to another copy of the vendor chart.

```text
charts/
  thanos/
    Chart.yaml           # Package name and version, application version, upstream source
    Chart.lock           # Locked versions of the Thanos chart's dependencies
    values.yaml          # Defaults for our chart
    templates/
    .helmignore          # Includes the /upstream/ rule
    README.md            # Downstream installation and upgrade instructions
    CHANGELOG.md         # Downstream release history and source of release notes
    LICENSE              # License distributed with the chart
    upstream/            # Unmodified reference files, tracked in Git but not packaged
      README.md
      CHANGELOG.md
```

## Downstream documentation and vendor originals

The chart-root `README.md` and `CHANGELOG.md` describe **our package**. The README explains installation, configuration, and upgrades. The changelog tells users what changes with each release. Both files belong in the `.tgz`.

Keep unmodified vendor documents from the recorded base commit under `upstream/`. Other original files may go there if they are useful for reference but not required to run or distribute the chart. They remain available in a normal clone even if the vendor repository disappears. This directory is not a second working copy of the chart.

Add `/upstream/` to the chart's `.helmignore`. For Bitnami Thanos, remove the inherited `CHANGELOG.md` exclusion: that name now belongs to **our** changelog. The license, required attribution notices, and files used by the chart must not exist only in the excluded directory.

## Other vendors and chart dependencies

Place the next chart alongside Thanos under `charts/<name>/`. The contents depend on the chart; some vendors include `crds/`, `values.schema.json`, or bundled subcharts. Do not confuse the repository's `charts/` directory with `charts/thanos/charts/`: Helm uses the latter for **dependencies of Thanos**, not independently released charts.

The proposed naming convention uses the same published name for the directory, `Chart.yaml.name`, and the middle component of `release/<name>/<version>`. If two vendors supply charts with the same name, choose a distinct public name or separate namespaces for tags and packages before importing the second one. A vendor directory alone would not disambiguate a release tag.
