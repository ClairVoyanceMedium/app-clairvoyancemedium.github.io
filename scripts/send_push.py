#!/usr/bin/env python3
import csv
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
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

HEADERS = {
    'Authorization': f'Key {API_KEY}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


def request_json(url, method='GET', payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code}: {body}') from exc


def truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 't', 'yes', 'y'}


def notification_type(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def target_matches(row):
    if TARGET == 'all':
        return True

    device_type = str(row.get('device_type', '') or '').strip()
    tags = str(row.get('tags', '') or '')

    if TARGET == 'android':
        return device_type == '1' or 'android_native' in tags

    return device_type in {'0', '7', '17'} or 'ios_web' in tags or 'ios_native' in tags


def fetch_subscription_ids():
    export = request_json(
        f'https://api.onesignal.com/players/csv_export?app_id={urllib.parse.quote(APP_ID)}',
        method='POST',
        payload={
            'extra_fields': [
                'notification_types',
                'unsubscribed_at',
            ],
        },
    )

    csv_url = export.get('csv_file_url')
    if not csv_url:
        raise RuntimeError(f'Export CSV OneSignal invalide: {export}')

    raw = None
    for attempt in range(12):
        try:
            with urllib.request.urlopen(csv_url, timeout=60) as response:
                raw = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or attempt == 11:
                raise
            time.sleep(min(2 + attempt * 2, 15))

    if raw is None:
        raise RuntimeError('Le CSV OneSignal n’a pas pu être téléchargé.')

    try:
        text = gzip.decompress(raw).decode('utf-8-sig')
    except OSError:
        text = raw.decode('utf-8-sig')

    rows = list(csv.DictReader(io.StringIO(text)))
    valid_ids = []
    diagnostics = []

    for row in rows:
        sid = str(row.get('id', '') or '').strip()
        invalid = truthy(row.get('invalid_identifier'))
        ntype = notification_type(row.get('notification_types'))
        token = str(row.get('identifier', '') or '').strip()
        matched = target_matches(row)

        diagnostics.append({
            'id': (sid[:8] + '…') if sid else '—',
            'device_type': str(row.get('device_type', '') or ''),
            'notification_types': ntype,
            'invalid': invalid,
            'push_token_present': bool(token),
            'matched_target': matched,
        })

        # OneSignal exige à la fois un abonnement positif et un jeton push.
        if sid and matched and not invalid and ntype > 0 and token:
            valid_ids.append(sid)

    print('Diagnostic abonnements OneSignal:', json.dumps(diagnostics, ensure_ascii=False))
    return list(dict.fromkeys(valid_ids))


try:
    subscription_ids = fetch_subscription_ids()
except Exception as exc:
    sys.exit(f'Impossible de lire les abonnements OneSignal: {exc}')

if not subscription_ids:
    sys.exit(
        'Aucun abonnement OneSignal réellement joignable pour cette cible. '
        'Les autorisations peuvent être acceptées sur le téléphone, mais aucun jeton push FCM/APNs valide n’est actuellement enregistré.'
    )

payload = {
    'app_id': APP_ID,
    'target_channel': 'push',
    'include_subscription_ids': subscription_ids[:20000],
    'headings': {'fr': TITLE, 'en': TITLE},
    'contents': {'fr': MESSAGE, 'en': MESSAGE},
    'name': f'CVM {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
}

if URL:
    payload['url'] = URL
if IMAGE_URL:
    payload['big_picture'] = IMAGE_URL
    payload['chrome_web_image'] = IMAGE_URL

try:
    result = request_json(
        'https://api.onesignal.com/notifications?c=push',
        method='POST',
        payload=payload,
    )
except Exception as exc:
    sys.exit(f'Erreur OneSignal lors de l’envoi: {exc}')

if not result.get('id'):
    sys.exit(
        'OneSignal n’a pas accepté la notification pour les abonnements ciblés: '
        + json.dumps(result, ensure_ascii=False)
    )

print(json.dumps({
    'status': 'sent',
    'message_id': result['id'],
    'target': TARGET,
    'subscription_count': len(subscription_ids),
    'title': TITLE,
}, ensure_ascii=False))
