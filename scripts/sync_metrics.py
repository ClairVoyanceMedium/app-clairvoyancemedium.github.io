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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

APP_ID = os.environ.get('ONESIGNAL_APP_ID', '').strip()
API_KEY = os.environ.get('ONESIGNAL_API_KEY', '').strip()
OUT = Path(os.environ.get('METRICS_OUTPUT', 'metrics-private.json'))

if not APP_ID or not API_KEY:
    sys.exit('ONESIGNAL_APP_ID et ONESIGNAL_API_KEY doivent être configurés dans GitHub Secrets.')

HEADERS = {
    'Authorization': f'Key {API_KEY}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


def request_json(url, method='GET', payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code}: {body}') from exc


def unix_or_iso(value):
    if value in (None, '', 'null'):
        return None
    try:
        number = float(value)
        if number > 100000000000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        text = str(value)
        return text


def is_truthy(value):
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'y'}


def platform_name(row):
    dtype = str(row.get('device_type', '')).strip()
    tags = str(row.get('tags', '') or '')
    if 'ios_web' in tags:
        return 'iOS / iPadOS Web Push'
    return {
        '0': 'iOS natif',
        '1': 'Android',
        '2': 'Amazon Fire',
        '5': 'Web Chrome',
        '7': 'Safari Web Push',
        '17': 'Safari Web Push',
    }.get(dtype, f'Autre ({dtype or "inconnu"})')


# 1) Export des abonnements. Aucun token push, IP ou identifiant brut n'est
# conservé dans l'artefact final.
export = request_json(
    f'https://api.onesignal.com/players/csv_export?app_id={urllib.parse.quote(APP_ID)}',
    method='POST',
    payload={
        'extra_fields': [
            'country',
            'unsubscribed_at',
            'notification_types',
            'timezone_id',
        ],
    },
)
csv_url = export.get('csv_file_url')
if not csv_url:
    raise RuntimeError(f'Export CSV OneSignal invalide: {export}')

raw = None
for attempt in range(12):
    try:
        with urllib.request.urlopen(csv_url, timeout=60) as r:
            raw = r.read()
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
subscriptions = []
for row in rows:
    unsubscribed = is_truthy(row.get('invalid_identifier'))
    sid = str(row.get('id', '') or '')
    subscriptions.append({
        'id_short': sid[:8] + ('…' if len(sid) > 8 else ''),
        'platform': platform_name(row),
        'status': 'désabonné' if unsubscribed else 'abonné',
        'created_at': unix_or_iso(row.get('created_at')),
        'last_active': unix_or_iso(row.get('last_active')),
        'unsubscribed_at': unix_or_iso(row.get('unsubscribed_at')),
        'country': row.get('country') or '',
        'language': row.get('language') or '',
        'timezone': row.get('timezone_id') or '',
        'device_model': row.get('device_model') or '',
        'device_os': row.get('device_os') or '',
        'app_version': row.get('game_version') or '',
        'session_count': int(float(row.get('session_count') or 0)),
        'playtime_seconds': int(float(row.get('playtime') or 0)),
        'notification_types': row.get('notification_types') or '',
    })

# 2) Messages récents et métriques d'envoi.
messages_response = request_json(
    f'https://api.onesignal.com/notifications?app_id={urllib.parse.quote(APP_ID)}&limit=50&offset=0'
)
messages = []
for msg in messages_response.get('notifications', []):
    headings = msg.get('headings') or {}
    contents = msg.get('contents') or {}
    messages.append({
        'id': msg.get('id'),
        'title': headings.get('fr') or headings.get('en') or msg.get('name') or '',
        'message': contents.get('fr') or contents.get('en') or '',
        'queued_at': unix_or_iso(msg.get('queued_at')),
        'completed_at': unix_or_iso(msg.get('completed_at')),
        'successful': int(msg.get('successful') or 0),
        'received': int(msg.get('received') or 0),
        'clicked': int(msg.get('converted') or 0),
        'failed': int(msg.get('failed') or 0),
        'errored': int(msg.get('errored') or 0),
        'remaining': int(msg.get('remaining') or 0),
        'url': msg.get('url') or msg.get('web_url') or msg.get('app_url') or '',
    })

now = datetime.now(timezone.utc)
new_24h = 0
for s in subscriptions:
    created = s.get('created_at')
    if not created:
        continue
    try:
        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        if (now - dt).total_seconds() <= 86400:
            new_24h += 1
    except ValueError:
        pass

platform_counts = Counter(s['platform'] for s in subscriptions if s['status'] == 'abonné')
subscribed = sum(1 for s in subscriptions if s['status'] == 'abonné')
unsubscribed = len(subscriptions) - subscribed

payload = {
    'generated_at': now.isoformat(),
    'privacy': 'Les tokens push, adresses IP, identifiants OneSignal complets et autres secrets sont exclus de cet artefact.',
    'summary': {
        'subscriptions_total': len(subscriptions),
        'subscribed': subscribed,
        'unsubscribed': unsubscribed,
        'new_last_24h': new_24h,
        'android_subscribed': platform_counts.get('Android', 0),
        'ios_web_subscribed': platform_counts.get('iOS / iPadOS Web Push', 0) + platform_counts.get('Safari Web Push', 0),
        'web_chrome_subscribed': platform_counts.get('Web Chrome', 0),
        'messages_total_api_visible': int(messages_response.get('total_count') or len(messages)),
        'messages_loaded': len(messages),
    },
    'platform_counts': dict(platform_counts),
    'subscriptions': sorted(subscriptions, key=lambda x: x.get('created_at') or '', reverse=True),
    'messages': messages,
}

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Métriques écrites dans {OUT} : {subscribed} abonnés actifs, {unsubscribed} désabonnés.')
