# Build inputs and publication

Run commands from the web repository root. Builds need Python 3.10+ and its standard library only.
The current inputs deliberately block publication while contact, owner, policy, and screenshot
approval details remain incomplete. Source code can be pushed without deploying the website.

## Identity snapshot


Docs owns release identity. Edit and review `Docs/release/identity.json` there, then refresh this
repository's allowlisted public snapshot and inspect the diff:

```sh
python3 build.py --refresh-identity ../Docs/release/identity.json
python3 build.py
```

The snapshot includes public name, availability, contact, owner, and website URLs; it excludes
App Store version identifiers and other internal release fields. Refreshing never approves privacy
or screenshots. Build output does not include the JSON input files.

For a one-off review without changing the snapshot, the existing override remains available:

```sh
python3 build.py --identity /path/to/reviewed-identity.json
python3 build.py --screenshot /path/to/real-reader.png
```

A supplied screenshot must exist and be a PNG. A missing default screenshot is now an error,
not a placeholder. Hero overrides are local review inputs and are refused by `--publish-check`;
update the checked-in assets and review their manifest for publication.

## Website policy and screenshot review

`inputs/policy.json` owns the hosting/retention values and website approval flags.
`inputs/screenshots.json` owns capture provenance (source and review history), exact image hashes,
and per-capture/per-frame approval flags. Keep both files in Git; they contain public build inputs,
not secrets. See [screenshot maintenance](assets.md) for image refresh instructions.

## Publication checks


```sh
python3 -m unittest discover -s tests -v
python3 build.py --publish-check
```

The second command is expected to fail with current inputs. Before it can pass, supply and review:

- Public name confirmation, final domain, monitored support email, legal owner, and territories in Docs.
- Final HTTPS marketing, support, and privacy URLs, then refresh the snapshot. Keep `support.html`
  and `privacy.html` paths under the chosen Pages project base path.
- Hosting provider, actual hosting request-log handling, support-message retention, and policy date.
  Do not invent a hosting retention period or treat it as controlled by this website.
- `privacy_approved` only after the app data-flow review and owner policy review are complete.
- Per-asset and per-frame `publication_ready`, plus `screenshots_approved`, after publication review.

A store URL is optional for a prelaunch website. Add it to Docs only after verifying the app listing
is publicly available. It must be an HTTPS `apps.apple.com` app listing; otherwise the build fails.
Without it, the page honestly says “Coming soon to the App Store”.

The builder also refuses missing/changed assets, broken internal links or anchors, root-relative
paths that break project sites, external assets, and unfinished public copy. A complete approved
build removes preview markers. These website checks do not establish app release readiness.

## GitHub Pages setup

The `.github/workflows/pages.yml` workflow is prepared for this **web repository as the repository
root**, not the multi-repository workspace parent. It follows
[GitHub's custom workflow guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

When publication is separately requested:

1. Confirm the repository and final Pages URL, fill the public inputs above, and rerun local checks.
2. Push this repository's sources and assets, excluding ignored `build/` and local caches.
3. In repository Settings → Pages, choose GitHub Actions as the publishing source. Configure the
   `github-pages` environment to allow the intended release branch.
4. Manually run **Publish verified website to GitHub Pages** from that branch.

The workflow has no push or schedule trigger. It runs website tests, builds with `--publish-check`,
then uploads only `build/` and deploys that artifact. Deployment waits for a successful build;
Pages write and identity-token permissions are limited to the deployment job. Relative assets
and navigation work under both a root URL and a `/repository/` project URL. `.nojekyll` is emitted.

No Git remote, push, repository setting, or live deployment was changed during local preparation.
