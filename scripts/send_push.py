#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

APP_ID = os.environ.get('ONESIGNAL_APP_ID', '').strip()
API_KEY = os.environ.get('ONESIGNAL_API_KEY', '').strip()
TITLE = os.environ.get('PUSH_TITLE', '').strip()
MESSAGE = os.environ.get('PUSH_MESSAGE', '').strip()
URL = os.environ.get('PUSH_URL', '').strip()
IMAGE_URL = os.environ.get('PUSH_IMAGE_URL', '').strip()
TARGET = os.environ.get('PUSH_TARGET', 'all').strip().lower()

if not APP_ID or not API_KEY:
    sys.exit('ONESIGNAL_APP_ID et ONESIGNAL_API_KEY doivent être configurés dans GitHub Secrets.')
if not TITLE or not MESSAGE:
    sys.exit('Le titre et le message sont obligatoires.')
if TARGET not in {'all', 'android', 'ios_web'}:
    sys.exit('Cible invalide. Utiliser all, android ou ios_web.')

payload = {
    'app_id': APP_ID,
    'target_channel': 'push',
    'included_segments': ['Subscribed Users'],
    'headings': {'fr': TITLE, 'en': TITLE},
    'contents': {'fr': MESSAGE, 'en': MESSAGE},
    'name': f'CVM {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
}

if URL:
    payload['url'] = URL
if IMAGE_URL:
    payload['big_picture'] = IMAGE_URL
    payload['chrome_web_image'] = IMAGE_URL

if TARGET == 'android':
    payload['isAndroid'] = True
    payload['isAnyWeb'] = False
elif TARGET == 'ios_web':
    payload['isAndroid'] = False
    payload['isAnyWeb'] = True

request = urllib.request.Request(
    'https://api.onesignal.com/notifications',
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Authorization': f'Key {API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    method='POST',
)

try:
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode('utf-8'))
except urllib.error.HTTPError as exc:
    body = exc.read().decode('utf-8', errors='replace')
    sys.exit(f'Erreur OneSignal HTTP {exc.code}: {body}')

if not result.get('id'):
    sys.exit(f'OneSignal n’a pas renvoyé d’identifiant de message: {json.dumps(result, ensure_ascii=False)}')

print(json.dumps({
    'status': 'sent',
    'message_id': result['id'],
    'target': TARGET,
    'title': TITLE,
}, ensure_ascii=False))
