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

APP_ID = os.environ.get('ONESIGNAL_APP_ID', '').strip()
API_KEY = os.environ.get('ONESIGNAL_API_KEY', '').strip()
ADMIN_EXTERNAL_ID = os.environ.get('ADMIN_EXTERNAL_ID', 'cvm_admin_frederick').strip()
ADMIN_DEVICE_MODEL = os.environ.get('ADMIN_DEVICE_MODEL', 'SM-F971B').strip()
ADMIN_COUNTRY = os.environ.get('ADMIN_COUNTRY', 'FR').strip().upper()
ADMIN_TIMEZONE = os.environ.get('ADMIN_TIMEZONE', 'Europe/Paris').strip()

if not APP_ID or not API_KEY:
    sys.exit('ONESIGNAL_APP_ID et ONESIGNAL_API_KEY sont obligatoires.')

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
            raw = response.read().decode('utf-8')
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code}: {body}') from exc


def truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 't', 'yes', 'y'}


def ntype(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def export_rows():
    export = request_json(
        f'https://api.onesignal.com/players/csv_export?app_id={urllib.parse.quote(APP_ID)}',
        method='POST',
        payload={
            'extra_fields': [
                'notification_types',
                'timezone_id',
                'country',
                'unsubscribed_at',
            ],
        },
    )
    url = export.get('csv_file_url')
    if not url:
        raise RuntimeError(f'Export OneSignal invalide: {export}')

    raw = None
    for attempt in range(12):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                raw = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or attempt == 11:
                raise
            time.sleep(min(2 + attempt * 2, 15))

    if raw is None:
        raise RuntimeError('CSV OneSignal introuvable.')

    try:
        text = gzip.decompress(raw).decode('utf-8-sig')
    except OSError:
        text = raw.decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text)))


rows = export_rows()
candidates = []
for row in rows:
    sid = str(row.get('id', '') or '').strip()
    token = str(row.get('identifier', '') or '').strip()
    if not sid or not token:
        continue
    if truthy(row.get('invalid_identifier')) or ntype(row.get('notification_types')) <= 0:
        continue
    if str(row.get('device_model', '') or '').strip() != ADMIN_DEVICE_MODEL:
        continue
    if str(row.get('country', '') or '').strip().upper() != ADMIN_COUNTRY:
        continue
    tz = str(row.get('timezone_id', '') or row.get('timezone', '') or '').strip()
    if ADMIN_TIMEZONE and tz != ADMIN_TIMEZONE:
        continue
    candidates.append(row)

if len(candidates) != 1:
    summary = [
        {
            'id': (str(r.get('id', ''))[:8] + '…') if r.get('id') else '—',
            'device_model': r.get('device_model'),
            'country': r.get('country'),
            'timezone': r.get('timezone_id') or r.get('timezone'),
            'notification_types': r.get('notification_types'),
        }
        for r in candidates
    ]
    sys.exit(
        'Marquage administrateur arrêté par sécurité: '
        f'{len(candidates)} appareil(s) correspondent aux critères. {json.dumps(summary, ensure_ascii=False)}'
    )

subscription_id = str(candidates[0]['id']).strip()
result = request_json(
    'https://api.onesignal.com/apps/'
    + urllib.parse.quote(APP_ID)
    + '/subscriptions/'
    + urllib.parse.quote(subscription_id)
    + '/user/identity',
    method='PATCH',
    payload={'identity': {'external_id': ADMIN_EXTERNAL_ID}},
)

identity = result.get('identity') or {}
if identity.get('external_id') != ADMIN_EXTERNAL_ID:
    sys.exit('OneSignal n’a pas confirmé l’identité administrateur: ' + json.dumps(result, ensure_ascii=False))

print(json.dumps({
    'status': 'admin_device_marked',
    'external_id': ADMIN_EXTERNAL_ID,
    'subscription_id_short': subscription_id[:8] + '…',
    'device_model': ADMIN_DEVICE_MODEL,
    'country': ADMIN_COUNTRY,
    'timezone': ADMIN_TIMEZONE,
}, ensure_ascii=False))
