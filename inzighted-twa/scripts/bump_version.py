"""
Simple script to bump Android versionCode and versionName in `app/build.gradle`.
Usage: python bump_version.py [major|minor|patch]

This script makes a very small, best-effort edit and should be reviewed before committing.
"""
import re
import sys
from pathlib import Path

build_gradle = Path(__file__).resolve().parents[1] / 'app' / 'build.gradle'
text = build_gradle.read_text(encoding='utf-8')

# Find versionCode and versionName
vc_match = re.search(r'versionCode\s+(\d+)', text)
vn_match = re.search(r'versionName\s+"([^"]+)"', text)
if not vc_match or not vn_match:
    print('versionCode/versionName not found in build.gradle')
    sys.exit(1)

vc = int(vc_match.group(1))
vn = vn_match.group(1)
parts = vn.split('.')

bump = 'patch'
if len(sys.argv) > 1:
    bump = sys.argv[1]

if bump == 'major':
    parts[0] = str(int(parts[0]) + 1) if parts[0].isdigit() else parts[0]
    if len(parts) > 1: parts[1] = '0'
    if len(parts) > 2: parts[2] = '0'
elif bump == 'minor':
    if len(parts) < 2:
        parts += ['0']
    parts[1] = str(int(parts[1]) + 1) if parts[1].isdigit() else parts[1]
    if len(parts) > 2: parts[2] = '0'
else:
    if len(parts) < 3:
        parts += ['0' for _ in range(3-len(parts))]
    parts[2] = str(int(parts[2]) + 1) if parts[2].isdigit() else parts[2]

new_vn = '.'.join(parts)
new_vc = vc + 1

text = re.sub(r'(versionCode\s+)\d+', r'\1{}'.format(new_vc), text)
text = re.sub(r'(versionName\s+")([^"]+)(")', r'\1{}\3'.format(new_vn), text)

build_gradle.write_text(text, encoding='utf-8')
print(f'Bumped versionCode {vc} -> {new_vc}, versionName {vn} -> {new_vn}')
