# Build inputs and publication

Run commands from the web repository root. Builds need Python 3.10+ and its standard library only.
Owner contact details, worldwide territory intent, privacy approval, and screenshot/frame approvals
were recorded on October 17, 2026. GitHub's Pages API confirmed the default project URL and no
custom domain. Source code can be pushed without deploying the website.

## Configured public addresses

These addresses become available after a successful deployment:

- Home / marketing: https://daniv3r.github.io/teleprompter-web/
- Support: https://daniv3r.github.io/teleprompter-web/support.html
- Privacy: https://daniv3r.github.io/teleprompter-web/privacy.html
- Terms: https://daniv3r.github.io/teleprompter-web/terms.html

Public support contact: fun-tapper-6s@icloud.com. Legal owner: Daniil Veramei.
`Worldwide` records the owner's all-countries intent; this website update does not change App Store
territory settings. No App Store download URL is supplied yet.

Hosting is GitHub Pages. GitHub confirms security logging of visitor IP addresses; its cited
privacy policy does not give a fixed Pages-specific retention period. The site explains that
GitHub controls these records, rather than inventing a deletion schedule. Sources:
[Pages data collection](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#data-collection)
and [GitHub retention policy](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement#security-and-retention).

The owner chose to retain support emails and attachments while resolving the request, then delete
them within 30 days after resolution. This is an inbox-handling policy, not an automated website
deletion feature. Owner approval is recorded for current privacy text, screenshots, and device
artwork. It does not create new app runtime or final-build verification evidence.

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

The second command must pass before publication. Keep these inputs reviewed and current:

- Public name confirmation, final domain, monitored support email, legal owner, and territories in Docs.
- Final HTTPS marketing, support, and privacy URLs, then refresh the snapshot. Keep `support.html`
  and `privacy.html` paths under the chosen Pages project base path.
- Hosting provider, actual hosting request-log handling, support-message retention, and policy date.
  Do not invent a hosting retention period or treat it as controlled by this website.
- `privacy_approved` records owner policy approval; app verification evidence remains separate.
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
