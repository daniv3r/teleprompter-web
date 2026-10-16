#!/usr/bin/env python3
"""Create proportional website images from real marketing captures; requires Pillow."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

WEB = Path(__file__).resolve().parents[1]
FRAME_NAMES = {
    'iphone': 'iPhone 17 Pro - Silver - Portrait',
    'ipad': 'iPad Pro 13 - M4 - Space Gray - Portrait',
}
SELECTED = (
    ('reader', 'iphone-6.3', '01_hero', 'iphone'),
    ('cards', 'iphone-6.3', '03_key_feature', 'iphone'),
    ('settings', 'iphone-6.3', '05_personalize', 'iphone'),
    ('library', 'ipad-13', '04_collection', 'ipad'),
    ('mac', 'mac-16x10', '01_hero', 'mac'),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def device_frame(marketing, name):
    directory = marketing / 'app-store/assets/device-frames'
    metadata = json.loads((directory / 'Frames.json').read_text())[name]
    path = directory / f'{name}.png'
    if digest(path) != metadata['sha256']:
        raise ValueError(f'{name}: artwork does not match its source manifest')
    frame = Image.open(path).convert('RGBA')
    alpha = frame.getchannel('A')
    # Flood out transparent exterior pixels. The enclosed transparent area is
    # the actual screen opening, including its curved edges and camera cutout.
    inside = alpha.point(lambda value: 255 if value <= 50 else 0)
    width, height = frame.size
    for x in range(width):
        for y in (0, height - 1):
            if inside.getpixel((x, y)):
                ImageDraw.floodfill(inside, (x, y), 0)
    for y in range(height):
        for x in (0, width - 1):
            if inside.getpixel((x, y)):
                ImageDraw.floodfill(inside, (x, y), 0)
    mask = ImageChops.multiply(ImageChops.invert(alpha), inside)
    return frame, mask, metadata


def frame_capture(image, frame, mask, bounds):
    if image.size != (bounds['width'], bounds['height']):
        raise ValueError('Capture must exactly match the hardware screen opening')
    screen = Image.new('RGBA', frame.size)
    screen.paste(image.convert('RGBA'), (bounds['x'], bounds['y']))
    screen.putalpha(mask)
    return Image.alpha_composite(screen, frame)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--marketing', required=True, type=Path, help='Path to the canonical marketing repository')
    args = parser.parse_args()
    manifest = {
        'description': 'Real app captures, proportionally resized. iPhone and iPad captures use existing hardware artwork and exact screen masks; Mac has no added frame or corner clipping. No generated imagery or UI retouching.',
        'assets': {},
    }
    frames = {platform: device_frame(args.marketing, name) for platform, name in FRAME_NAMES.items()}
    for name, device, key, platform in SELECTED:
        source = args.marketing / f'app-store/raw-captures/en-US/{device}/{key}.png'
        record = json.loads((args.marketing / f'app-store/capture-manifests/{platform}.json').read_text())
        capture = next(item for item in record['captures'] if item['key'] == key)
        if digest(source) != capture['sha256']:
            parser.error(f'Capture does not match its source manifest: {source}')
        identity = capture.get('original_capture_identity', record)
        image = Image.open(source).convert('RGB')
        if platform in frames:
            frame, mask, frame_metadata = frames[platform]
            image = frame_capture(image, frame, mask, frame_metadata['screen_bounds'])
        variants = []
        widths = [480, 960] if platform == 'iphone' else [640, 1200] if platform == 'ipad' else [960, 1600]
        for width in widths:
            height = round(image.height * width / image.width)
            target = WEB / 'assets/screenshots' / f'{name}-{width}.webp'
            image.resize((width, height), Image.Resampling.LANCZOS).save(target, 'WEBP', quality=90, method=6)
            variants.append({'file': target.name, 'width': width, 'height': height, 'sha256': digest(target)})
        manifest['assets'][name] = {
            'source': f'marketing/app-store/raw-captures/en-US/{device}/{key}.png',
            'source_sha256': digest(source),
            'capture_sha256': capture['sha256'],
            'captured_at_utc': capture.get('captured_at_utc', identity['captured_at_utc']),
            'reused': capture.get('reused', False),
            'configuration': identity['configuration'],
            'app_version': identity['app_version'], 'app_build': identity['app_build'],
            'source_commit': identity['source_commit'],
            'app_binary_sha256': identity['app_binary_sha256'],
            'publication_ready': False,
            'variants': variants,
        }
        if platform in frames:
            manifest['assets'][name]['frame'] = {
                'source': f'marketing/app-store/assets/device-frames/{FRAME_NAMES[platform]}.png',
                'sha256': frame_metadata['sha256'],
                'source_pack': frame_metadata['source_pack'],
                'screen_bounds': frame_metadata['screen_bounds'],
                'publication_ready': False,
            }
    (WEB / 'inputs/screenshots.json').write_text(json.dumps(manifest, indent=2) + '\n')
    policy_path = WEB / 'inputs/policy.json'
    policy = json.loads(policy_path.read_text())
    policy['screenshots_approved'] = False
    policy_path.write_text(json.dumps(policy, indent=2) + '\n')
    print('Refreshed five real captures and ten WebP variants. Screenshot publication approval reset.')


if __name__ == '__main__':
    main()
