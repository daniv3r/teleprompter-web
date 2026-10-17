# Teleprompter: Speech Deck — website

English static product website with real iPhone, iPad, and Mac screenshots.
No JavaScript, external fonts, analytics, cookies, or AI-generated images.

## Local development

Requires Python 3.10+. No dependency installation is needed to build or test.
Run from this repository:

```sh
python3 build.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory build
```

Open <http://127.0.0.1:8765/>. From the parent workspace, prefix the script and
server directory with `web/`. All four pages build without sibling repositories.

```sh
python3 -m unittest discover -s tests -v
python3 build.py --publish-check
```

Public contact details and owner approvals were recorded on October 17, 2026. Publication checks
validate those inputs before deployment. Incomplete inputs show a preview banner and ask search
engines not to index the site. Nothing publishes on a normal build or Git push.

## Repository layout

```text
.github/workflows/pages.yml   Manual GitHub Pages publishing
assets/
  screenshots/               Ready-to-use responsive WebP images
  favicon.svg                Website icon
  style.css                  Shared responsive styles
docs/
  assets.md                  Image sources and refresh instructions
  publishing.md              Public inputs, release checks, and Pages setup
inputs/
  identity.json              Public snapshot from the separate Docs repository
  policy.json                Website policy values and approval flags
  screenshots.json           Screenshot/frame sources, hashes, and review status
templates/                   Shared page shell and four page templates
tests/                       Isolated website builder tests
tools/                       Optional screenshot refresh tool and its dependency list
build.py                     Dependency-free build entry point
build/                       Generated website; ignored by Git
```

## What belongs in Git

Keep the source folders above, `build.py`, this README, and `.gitignore`. The small screenshot
variants are required build inputs and belong in Git alongside their source records.

Keep generated `build/`, Python caches, virtual environments, Finder metadata, temporary build
folders, and credentials out of Git. The existing ignore rules cover these local files.

Only the contents of `build/` are uploaded by the manual Pages workflow; sources, tests, and input
JSON are not deployed. See [publication setup](docs/publishing.md) and
[screenshot maintenance](docs/assets.md).
