# Rules

## Release notes must carry the changelog

Every GitHub release body must include the matching `CHANGELOG.md` section for that version (the `## [x.y.z] - date` block, verbatim). The generated `--generate-notes` output and the `**Full Changelog**` compare link may be appended, but never used as the whole body.

Publishing flow, in order:

1. Bump `PLUGIN_VERSION`, `tools/build_release.py` `VERSION`, `CHANGELOG.md`, `docs/ORCACLOUD_CHANGELOG.md`.
2. Push `main`, then tag `vX.Y.Z` and push the tag.
3. `release.yml` creates a bot release. Delete it: `gh release delete vX.Y.Z --yes`.
4. Recreate from your own credentials with the changelog section in the body:

   ```
   gh release create vX.Y.Z --notes-file <(awk -v v="## [X.Y.Z] " '$0 ~ "^"v {p=1; next} /^## / {p=0} p' CHANGELOG.md) dist/*.whl dist/*.zip SHA256SUMS.txt
   ```

   (Prepend the `**Full Changelog**` compare link to the notes if wanted.)

Only a release created with your credentials triggers `publish-orcacloud.yml`; a bot release publishes nothing to OrcaCloud.
