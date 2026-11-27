<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-FileCopyrightText: 2026 verared contributors -->

# Diagnosis: first Gerarion Time npm tag

The tag `gerarion-time-v0.1.0-alpha.1` resolves to
`20b3b3fae1367bd35274897b083fe4badeaf0d7a`. The publication workflow exists
at that commit, is active, and matches the tag without a `paths` filter.

[Run 46024350811](https://github.com/verared/gerarion/actions/runs/46024350811)
triggered on the tag push. The tag-version check and Python installation
passed. The `npm ci` step failed; the build, tests and `npm publish` steps
were skipped. This run does not establish anything about `NPM_TOKEN` validity.

Public job annotations expose only `Process completed with exit code 1`.
Full logs require repository authorization, unavailable during diagnosis.
In a clean export of the tag on Node 24.22.3, npm 11.21.3 reproduces:

```text
npm error code EUSAGE
npm error `npm ci` can only install packages when your package.json and package-lock.json or npm-shrinkwrap.json are in sync.
npm error Missing: @esbuild/aix-ppc64@0.28.2 from lock file
npm error Missing: @cloudflare/workerd-darwin-64@1.20260730.1 from lock file
```

The committed lockfile omitted optional platform variants of esbuild,
sharp/libvips and workerd. npm 10.9.9 accepted that incomplete lock locally;
the CI workflow used `npm install`, which did not exercise the publication
workflow's stricter clean-install gate.

The correction completes the platform entries without upgrading the already
locked versions, changes all package CI installs to `npm ci`, and prints Node
and npm versions in the publication workflow for future diagnostics.
Keep the existing tag unchanged. A failed-job rerun uses the old tagged
workflow and lockfile; after merging this fix, use a new package version/tag
or deliberately retarget an unpublished tag only with owner approval.
