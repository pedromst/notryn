#!/usr/bin/env python3
"""Aggregate GitHub package downloads. Not unique users or completed installs."""
import json
import urllib.request

base = 'https://api.github.com/repos/pedromst/notryn/releases'
rows = []
page = 1
while True:
    request = urllib.request.Request(f'{base}?per_page=100&page={page}', headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Notryn-download-report'})
    with urllib.request.urlopen(request, timeout=30) as response:
        releases = json.load(response)
    for release in releases:
        if release.get('draft'):
            continue
        for asset in release.get('assets', []):
            name = asset['name']
            if name.startswith('Notryn-') and name.endswith(('.tar.gz', '.zip', '.AppImage')):
                rows.append((release['tag_name'], name, asset['download_count']))
    if len(releases) < 100:
        break
    page += 1
print('Package downloads (includes repeat downloads, updates and tests):')
for tag, name, count in rows:
    print(f'{count:6d}  {tag}  {name}')
print(f'Total: {sum(row[2] for row in rows)} package downloads')
print('Setup executables and checksum files are excluded. Completed installs and unique people are not measured.')
