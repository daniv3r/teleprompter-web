"""Website-only build and publication checks. Every mutation uses an isolated temp copy."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]


class WebsiteBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='speech-deck-web-test-')
        self.addCleanup(self.temporary.cleanup)
        self.web = Path(self.temporary.name) / 'standalone'
        shutil.copytree(SOURCE, self.web, ignore=shutil.ignore_patterns('.git', 'build', '__pycache__', '.venv', '.site-*', '.DS_Store'))
        # Keep tests independent of future approval or store-link changes in real inputs.
        self.update_json('inputs/identity.json', lambda value: value.update(support_email=None, store_url=None))
        self.update_json('inputs/policy.json', lambda value: value.update(privacy_approved=False, screenshots_approved=False))
        self.update_json('inputs/screenshots.json', lambda value: [asset.update(publication_ready=False) for asset in value['assets'].values()])

    def run_build(self, *args, succeeds=True):
        result = subprocess.run([sys.executable, str(self.web / 'build.py'), *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0 if succeeds else 1, result.stdout + result.stderr)
        return result.stdout

    def update_json(self, name, update):
        path = self.web / name
        value = json.loads(path.read_text())
        update(value)
        path.write_text(json.dumps(value))

    def complete_inputs(self):
        # Fictional complete inputs are confined to this temporary website copy.
        base = 'https://speech-deck-fixture.github.io/site/'
        self.update_json('inputs/identity.json', lambda value: value.update(
            domain='speech-deck-fixture.github.io', support_email='support@speech-deck-fixture.github.io',
            privacy_url=base+'privacy.html', support_url=base+'support.html', marketing_url=base,
            territories=['PL'], legal_owner='Website Test Fixture', name_confirmed=True))
        self.update_json('inputs/policy.json', lambda value: value.update(
            privacy_approved=True, screenshots_approved=True, hosting_provider='Fixture host',
            hosting_log_retention='Fixture policy: seven days.', support_retention='Fixture policy: thirty days.'))
        self.update_json('inputs/screenshots.json', lambda value: [asset.update(publication_ready=True) for asset in value['assets'].values()])
        self.update_json('inputs/screenshots.json', lambda value: [asset['frame'].update(publication_ready=True) for asset in value['assets'].values() if asset.get('frame')])

    def test_independent_preview_and_existing_cli(self):
        self.run_build()
        self.assertFalse((self.web.parent / 'Docs').exists())
        for page in ('index', 'support', 'privacy', 'terms'):
            text = (self.web / f'build/{page}.html').read_text()
            self.assertIn('noindex,nofollow', text)
            self.assertIn('Local preview', text)
        self.assertIn('Coming soon to the App Store', (self.web / 'build/index.html').read_text())
        self.run_build('--identity', str(self.web / 'inputs/identity.json'))
        self.run_build('--screenshot', '/missing/reader.png', succeeds=False)

    def test_incomplete_publication_is_blocked(self):
        result = self.run_build('--publish-check', succeeds=False)
        self.assertIn('identity.support_email', result)
        self.assertIn('policy.privacy_approved', result)
        self.assertIn('assets.mac.publication_ready', result)
        self.assertFalse((self.web / 'build').exists())

    def test_complete_publication_build_has_no_preview_markers(self):
        self.complete_inputs()
        self.run_build('--publish-check')
        for page in ('index', 'support', 'privacy', 'terms'):
            text = (self.web / f'build/{page}.html').read_text()
            self.assertNotIn('noindex,nofollow', text)
            self.assertNotIn('Local preview', text)
            self.assertNotIn('pending', text.lower())
        self.assertTrue((self.web / 'build/.nojekyll').is_file())
        # No build-input identity, manifest, or source templates enter the deploy artifact.
        self.assertFalse((self.web / 'build/inputs').exists())

    def test_missing_and_changed_screenshots_fail(self):
        path = self.web / 'assets/screenshots/reader-480.webp'
        original = path.read_bytes()
        path.unlink()
        self.assertIn('Missing or invalid screenshot', self.run_build(succeeds=False))
        path.write_bytes(original + b'changed')
        self.assertIn('changed without manifest review', self.run_build(succeeds=False))

    def test_broken_links_anchors_and_project_paths_fail(self):
        path = self.web / 'templates/index.html'
        original = path.read_text()
        for reference in ('missing.html', '#missing-anchor', '/support.html'):
            path.write_text(original + f'<a href="{reference}">Broken reference</a>')
            self.run_build(succeeds=False)

    def test_unfinished_public_copy_and_external_assets_fail(self):
        self.complete_inputs()
        path = self.web / 'templates/index.html'
        original = path.read_text()
        path.write_text(original + '<p>TODO: finish this.</p>')
        self.assertIn('Unfinished public copy', self.run_build('--publish-check', succeeds=False))
        path.write_text(original + '<img src="https://assets.invalid/image.webp" alt="External">')
        self.assertIn('External asset', self.run_build('--publish-check', succeeds=False))

    def test_store_and_public_urls(self):
        for store in ('javascript:alert(1)', 'https://apps.apple.com.evil.invalid/app/id123', 'https://apps.apple.com/'):
            self.update_json('inputs/identity.json', lambda value: value.update(store_url=store))
            self.assertIn('apps.apple.com HTTPS app listing', self.run_build(succeeds=False))
        self.update_json('inputs/identity.json', lambda value: value.update(store_url='https://apps.apple.com/app/id6768774327'))
        self.run_build()
        self.assertIn('View on the App Store', (self.web / 'build/index.html').read_text())
        self.complete_inputs()
        self.update_json('inputs/identity.json', lambda value: value.update(privacy_url='https://example.com/privacy.html'))
        self.assertIn('real HTTPS URL', self.run_build('--publish-check', succeeds=False))

    def test_identity_refresh_filters_internal_fields_and_escapes_content(self):
        source = self.web / 'canonical-identity.json'
        source.write_text(json.dumps({'public_name': '<script>alert(1)</script>', 'internal_secret': 'not-public'}))
        self.run_build('--refresh-identity', str(source))
        snapshot = json.loads((self.web / 'inputs/identity.json').read_text())
        self.assertNotIn('internal_secret', snapshot)
        self.run_build()
        text = (self.web / 'build/index.html').read_text()
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('<script>', text)


if __name__ == '__main__':
    unittest.main()
