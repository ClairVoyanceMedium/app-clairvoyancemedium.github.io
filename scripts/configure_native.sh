#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

manifest = Path('android/app/src/main/AndroidManifest.xml')
text = manifest.read_text(encoding='utf-8')
if 'android.permission.INTERNET' not in text:
    text = text.replace(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">',
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n    <uses-permission android:name="android.permission.INTERNET" />'
    )
text = text.replace('android:label="clairvoyancemedium_app"', 'android:label="ClairVoyanceMedium.com"')
manifest.write_text(text, encoding='utf-8')

plist = Path('ios/Runner/Info.plist')
if plist.exists():
    p = plist.read_text(encoding='utf-8')
    if '<key>CFBundleDisplayName</key>' in p:
        import re
        p = re.sub(
            r'(<key>CFBundleDisplayName</key>\s*<string>).*?(</string>)',
            r'\1ClairVoyanceMedium.com\2',
            p,
            count=1,
            flags=re.S,
        )
    plist.write_text(p, encoding='utf-8')
PY

echo "Native configuration applied."
