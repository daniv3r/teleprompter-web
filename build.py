#!/usr/bin/env python3
"""Build a self-contained static preview; --publish-check enforces publication gates."""
import argparse
import hashlib
import html
import json
import re
import shutil
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from string import Template
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
IDENTITY_KEYS = (
    'app_id', 'observed_store_name', 'public_name', 'name_confirmed', 'domain',
    'support_email', 'privacy_url', 'support_url', 'marketing_url', 'territories',
    'legal_owner', 'version', 'price_model', 'primary_locale', 'store_url',
)
PAGES = {
    'index.html': ('Your words. Your pace.', 'Prepare your script and practice talks with word-by-word guidance on iPhone, iPad, and Mac.'),
    'support.html': ('Support', 'Get started with Speech Deck, adjust reading settings, resume a rehearsal, and find help.'),
    'privacy.html': ('Privacy', 'How Speech Deck handles scripts, reading preferences, diagnostics, website requests, and support messages.'),
    'terms.html': ('Terms of use', 'Read the terms for the free first release of Speech Deck and learn about local script storage.'),
}


def escaped(value):
    return html.escape(str(value), quote=True)


def load_json(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError(f'Cannot read {path}: {error}') from error
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected a JSON object')
    return value


def real_https(value):
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        return (parsed.scheme == 'https' and '.' in host and not parsed.username
                and not parsed.password and not any(c.isspace() for c in value)
                and not host.endswith(('.invalid', '.test', '.localhost'))
                and host not in ('example.com', 'example.org', 'example.net'))
    except (ValueError, TypeError):
        return False


def publication_gaps(identity, policy, manifest):
    missing = [f'identity.{key}' for key in (
        'public_name', 'domain', 'support_email', 'privacy_url', 'support_url',
        'marketing_url', 'territories', 'legal_owner',
    ) if not identity.get(key)]
    if identity.get('name_confirmed') is not True:
        missing.append('identity.name_confirmed')
    for key in ('hosting_provider', 'hosting_log_retention', 'support_retention', 'policy_date'):
        if not policy.get(key):
            missing.append(f'policy.{key}')
    for key in ('privacy_approved', 'screenshots_approved'):
        if policy.get(key) is not True:
            missing.append(f'policy.{key}')
    for name, asset in manifest['assets'].items():
        if asset.get('publication_ready') is not True:
            missing.append(f'assets.{name}.publication_ready')
        if asset.get('frame') and asset['frame'].get('publication_ready') is not True:
            missing.append(f'assets.{name}.frame.publication_ready')
    contact = identity.get('support_email')
    if contact and (not isinstance(contact, str) or not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', contact)):
        missing.append('identity.support_email: valid email required')
    for key in ('privacy_url', 'support_url', 'marketing_url'):
        if identity.get(key) and not real_https(identity[key]):
            missing.append(f'identity.{key}: real HTTPS URL required')
    try:
        date.fromisoformat(policy.get('policy_date') or '')
    except (ValueError, TypeError):
        missing.append('policy.policy_date: YYYY-MM-DD required')
    return missing


def validate_assets(manifest):
    for name in ('reader', 'cards', 'settings', 'library', 'mac'):
        variants = manifest.get('assets', {}).get(name, {}).get('variants', [])
        if not variants:
            raise ValueError(f'Missing screenshot variants: {name}')
        for variant in variants:
            filename = variant['file']
            path = HERE / 'assets/screenshots' / filename
            if Path(filename).name != filename or not path.is_file():
                raise ValueError(f'Missing or invalid screenshot: {filename}')
            if hashlib.sha256(path.read_bytes()).hexdigest() != variant['sha256']:
                raise ValueError(f'Screenshot changed without manifest review: {filename}')
            if variant['width'] <= 0 or variant['height'] <= 0:
                raise ValueError(f'Invalid screenshot dimensions: {filename}')


def screenshot(manifest, name, alt, sizes, eager=False):
    variants = manifest['assets'][name]['variants']
    large = max(variants, key=lambda variant: variant['width'])
    srcset = ', '.join(f'assets/screenshots/{v["file"]} {v["width"]}w' for v in variants)
    priority = 'fetchpriority="high" loading="eager"' if eager else 'loading="lazy"'
    return (f'<img src="assets/screenshots/{escaped(large["file"])}" srcset="{escaped(srcset)}" '
            f'sizes="{escaped(sizes)}" width="{large["width"]}" height="{large["height"]}" '
            f'alt="{escaped(alt)}" {priority} decoding="async">')


class PageInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.references = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            if attrs['id'] in self.ids:
                raise ValueError(f'Duplicate HTML id: {attrs["id"]}')
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.references.append((attrs[key], key == 'src' or (tag == 'link' and attrs.get('rel') != 'canonical')))
        for candidate in attrs.get('srcset', '').split(','):
            if candidate.strip():
                self.references.append((candidate.strip().split()[0], True))

    def handle_data(self, data):
        self.text.append(data)


def validate_output(output, publication=False):
    pages = {}
    for filename in PAGES:
        parser = PageInspector()
        parser.feed((output / filename).read_text(encoding='utf-8'))
        pages[filename] = parser
        if publication:
            text = ' '.join(parser.text).lower()
            # “First draft” describes writing a script, not unfinished website copy.
            text = re.sub(r'\bfirst draft\b', 'first version', text)
            if re.search(r'\b(draft|local preview|pending|placeholder|todo|tbd|preview only)\b', text):
                raise ValueError(f'Unfinished public copy in {filename}')
    for filename, parser in pages.items():
        for reference, asset in parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc:
                if asset:
                    # Canonical URLs describe the page; they are not fetched assets.
                    raise ValueError(f'External asset in {filename}: {reference}')
                if parsed.scheme not in ('https', 'mailto'):
                    raise ValueError(f'Unsafe link in {filename}: {reference}')
                continue
            if parsed.path.startswith('/'):
                raise ValueError(f'Root-relative link breaks project Pages URLs: {reference}')
            target = (output / unquote(parsed.path)).resolve() if parsed.path else output / filename
            if not target.is_relative_to(output.resolve()) or not target.is_file():
                raise ValueError(f'Broken local link in {filename}: {reference}')
            if parsed.fragment:
                target_page = pages.get(target.name)
                if target_page is None or unquote(parsed.fragment) not in target_page.ids:
                    raise ValueError(f'Broken anchor in {filename}: {reference}')


def render(filename, values):
    return Template((HERE / 'templates' / filename).read_text(encoding='utf-8')).substitute(values)


def build(identity, policy, manifest, output, screenshot_override=None):
    missing = publication_gaps(identity, policy, manifest)
    values = {'name': escaped(identity.get('public_name') or identity.get('observed_store_name') or 'Speech Deck')}
    values['draft_banner'] = ('<aside class="draft" aria-label="Publication status">Local preview · '
                              'publication details and screenshot review pending</aside>' if missing else '')
    values['robots'] = '<meta name="robots" content="noindex,nofollow">' if missing else ''
    values['contact'] = (f'<a href="mailto:{escaped(identity["support_email"])}">{escaped(identity["support_email"])}</a>'
                         if identity.get('support_email') else '<span class="pending">Support contact pending — preview only.</span>')
    values['owner'] = escaped(identity.get('legal_owner') or 'Legal owner pending — preview only.')
    for key in ('hosting_provider', 'hosting_log_retention', 'support_retention', 'policy_date'):
        values[key] = escaped(policy.get(key) or 'Pending owner confirmation — preview only.')
    values['privacy_note'] = ('<p class="document-notice">Draft policy: final app privacy review and owner approval are pending.</p>'
                              if policy.get('privacy_approved') is not True else '')
    store = identity.get('store_url')
    values['availability'] = (f'<a class="store-link" href="{escaped(store)}">View on the App Store</a>' if store
                               else '<p class="availability">Coming soon to the App Store</p>')
    values['reader_image'] = screenshot(manifest, 'reader', 'iPhone reader with a blue active word and pause, reset, and reading settings controls.', '(max-width: 760px) 256px, 260px', True)
    values['cards_image'] = screenshot(manifest, 'cards', 'Cards reading on iPhone, showing one part of a talk with word guidance and playback controls.', '(max-width: 760px) 256px, 260px')
    values['settings_image'] = screenshot(manifest, 'settings', 'iPhone Reading Settings with highlight choices, pace, text size, and smaller and larger text buttons.', '(max-width: 760px) 256px, 260px')
    values['library_image'] = screenshot(manifest, 'library', 'iPad script library beside the saved script A Clearer Presentation.', '(max-width: 760px) 84vw, 400px')
    values['mac_image'] = screenshot(manifest, 'mac', 'Native Mac reader window with a highlighted word and separate playback and reading settings controls.', '(max-width: 760px) 90vw, 960px')
    if screenshot_override:
        # An override is a local review input, never an implicitly approved asset.
        import struct
        with screenshot_override.open('rb') as source:
            header = source.read(24)
        if header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
            raise ValueError('--screenshot must be a PNG')
        width, height = struct.unpack('>II', header[16:24])
        if not width or not height:
            raise ValueError('--screenshot must have positive dimensions')
        shutil.copy2(screenshot_override, output / 'assets/screenshots' / 'reader-override.png')
        values['reader_image'] = (f'<img src="assets/screenshots/reader-override.png" width="{width}" height="{height}" '
                                   'alt="Supplied real app reader screenshot." fetchpriority="high" decoding="async">')
    for filename, (title, description) in PAGES.items():
        page_values = dict(values, title=escaped(title), description=escaped(description))
        url = identity.get('marketing_url' if filename == 'index.html' else filename.split('.')[0] + '_url')
        page_values['canonical'] = f'<link rel="canonical" href="{escaped(url)}">' if real_https(url) else ''
        page_values['content'] = render(filename, page_values)
        (output / filename).write_text(render('page.html', page_values), encoding='utf-8')
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-check', action='store_true', help='Build only when every publication gate passes')
    parser.add_argument('--identity', type=Path, default=HERE / 'inputs/identity.json', help='Explicit release identity override; default is the checked-in public snapshot')
    parser.add_argument('--screenshot', type=Path, help='Existing hero PNG override for local review only')
    parser.add_argument('--refresh-identity', type=Path, help='Refresh the public snapshot from Docs identity and exit')
    args = parser.parse_args()
    try:
        if args.refresh_identity:
            original = load_json(args.refresh_identity)
            snapshot = {key: original.get(key) for key in IDENTITY_KEYS}
            (HERE / 'inputs/identity.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
            print('Refreshed inputs/identity.json from the explicit Docs source; no approvals changed.')
            return 0
        identity = load_json(args.identity)
        policy = load_json(HERE / 'inputs/policy.json')
        manifest = load_json(HERE / 'inputs/screenshots.json')
        validate_assets(manifest)
        store = identity.get('store_url')
        if store and (not real_https(store) or urlsplit(store).hostname != 'apps.apple.com'
                      or not re.search(r'/id[0-9]+(?:/|$)', urlsplit(store).path)):
            raise ValueError('store_url must be an apps.apple.com HTTPS app listing URL')
        if args.screenshot and not args.screenshot.is_file():
            raise ValueError(f'Missing screenshot: {args.screenshot}')
        missing = publication_gaps(identity, policy, manifest)
        if args.publish_check and args.screenshot:
            missing.append('--screenshot overrides require asset-manifest review; use the checked-in assets for publication')
        if args.publish_check and missing:
            print('Publication blocked:\n- ' + '\n- '.join(missing))
            return 1
        with tempfile.TemporaryDirectory(prefix='.site-', dir=HERE) as temporary:
            stage = Path(temporary)
            (stage / 'assets/screenshots').mkdir(parents=True)
            for asset in manifest['assets'].values():
                for variant in asset['variants']:
                    shutil.copy2(HERE / 'assets/screenshots' / variant['file'], stage / 'assets/screenshots' / variant['file'])
            shutil.copy2(HERE / 'assets/style.css', stage / 'assets/style.css')
            shutil.copy2(HERE / 'assets/favicon.svg', stage / 'assets/favicon.svg')
            (stage / '.nojekyll').touch()
            build(identity, policy, manifest, stage, args.screenshot)
            validate_output(stage, publication=args.publish_check or not missing)
            output = HERE / 'build'
            if output.is_symlink():
                raise ValueError('Refusing to replace a symlinked build directory')
            if output.exists():
                shutil.rmtree(output)
            shutil.copytree(stage, output)
        print(f'Built {output}: 4 pages; local links, anchors, assets, and screenshot hashes pass.')
        if missing:
            print('Local preview only. Publication blocked:\n- ' + '\n- '.join(missing))
        else:
            print('Website publication checks pass. App release qualification is separate. Nothing was published.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Build failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
