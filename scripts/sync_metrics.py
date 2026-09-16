#!/usr/bin/env python3
import csv
import gzip
import io
import json
import os
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

HEADERS = {
    'Authorization': f'Key {API_KEY}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

errors = []


def request_json(url, method='GET', payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers or HEADERS, method=method)
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
        return str(value)


def is_truthy(value):
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'y'}


def notification_type_value(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


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


subscriptions = []
messages = []
messages_total_api_visible = 0

if not APP_ID or not API_KEY:
    errors.append('Clés OneSignal manquantes dans GitHub Secrets. Les métriques OneSignal ne peuvent pas être lues.')
else:
    # 1) Abonnements OneSignal. Une panne de cette source ne bloque plus
    # la création de l’artefact : les autres métriques restent disponibles.
    try:
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
        for row in rows:
            invalid = is_truthy(row.get('invalid_identifier'))
            notification_types = notification_type_value(row.get('notification_types'))
            push_subscribed = (not invalid) and notification_types > 0
            sid = str(row.get('id', '') or '')
            subscriptions.append({
                'id_short': sid[:8] + ('…' if len(sid) > 8 else ''),
                'platform': platform_name(row),
                'status': 'abonné' if push_subscribed else 'désabonné',
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
    except Exception as exc:
        errors.append(f'Abonnements OneSignal indisponibles: {exc}')

    # 2) Notifications récentes. Même principe : on conserve les métriques
    # disponibles si l’API notifications échoue temporairement.
    try:
        messages_response = request_json(
            f'https://api.onesignal.com/notifications?app_id={urllib.parse.quote(APP_ID)}&limit=50&offset=0'
        )
        messages_total_api_visible = int(messages_response.get('total_count') or 0)
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
        if not messages_total_api_visible:
            messages_total_api_visible = len(messages)
    except Exception as exc:
        errors.append(f'Notifications OneSignal indisponibles: {exc}')


# 3) Téléchargements du dernier APK GitHub Release. Cette source est publique
# et reste disponible même si OneSignal est mal configuré.
apk_downloads = 0
apk_release_updated_at = None
apk_size = None
try:
    release = request_json(
        'https://api.github.com/repos/ClairVoyanceMedium/app-clairvoyancemedium.github.io/releases/tags/android-latest',
        headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'ClairVoyanceMedium-metrics'},
    )
    apk_release_updated_at = release.get('updated_at')
    for asset in release.get('assets', []):
        if asset.get('name') == 'ClairVoyanceMedium.apk':
            apk_downloads = int(asset.get('download_count') or 0)
            apk_size = int(asset.get('size') or 0)
            break
except Exception as exc:
    errors.append(f'Téléchargements APK indisponibles: {exc}')

now = datetime.now(timezone.utc)
new_24h = 0
active_7d = 0
active_30d = 0
for s in subscriptions:
    created = parse_dt(s.get('created_at'))
    last_active = parse_dt(s.get('last_active'))
    if created and (now - created).total_seconds() <= 86400:
        new_24h += 1
    if last_active and s['status'] == 'abonné':
        age = (now - last_active).total_seconds()
        if age <= 7 * 86400:
            active_7d += 1
        if age <= 30 * 86400:
            active_30d += 1

platform_counts = Counter(s['platform'] for s in subscriptions if s['status'] == 'abonné')
country_counts = Counter(s['country'] or 'Inconnu' for s in subscriptions if s['status'] == 'abonné')
version_counts = Counter(s['app_version'] or 'Inconnue' for s in subscriptions if s['status'] == 'abonné')
subscribed = sum(1 for s in subscriptions if s['status'] == 'abonné')
unsubscribed = len(subscriptions) - subscribed
sessions_total = sum(s['session_count'] for s in subscriptions)
playtime_total = sum(s['playtime_seconds'] for s in subscriptions)
notifications_sent = sum(m['successful'] for m in messages)
notifications_received = sum(m['received'] for m in messages)
notifications_clicked = sum(m['clicked'] for m in messages)
notifications_failed = sum(m['failed'] + m['errored'] for m in messages)

payload = {
    'generated_at': now.isoformat(),
    'partial': bool(errors),
    'errors': errors,
    'sources': {
        'onesignal_configured': bool(APP_ID and API_KEY),
        'subscriptions_loaded': len(subscriptions),
        'messages_loaded': len(messages),
        'github_apk_loaded': apk_size is not None,
    },
    'privacy': 'Les tokens push, adresses IP, identifiants OneSignal complets et autres secrets sont exclus de cet artefact.',
    'summary': {
        'subscriptions_total': len(subscriptions),
        'subscribed': subscribed,
        'unsubscribed': unsubscribed,
        'new_last_24h': new_24h,
        'active_7d': active_7d,
        'active_30d': active_30d,
        'android_subscribed': platform_counts.get('Android', 0),
        'ios_web_subscribed': (
            platform_counts.get('iOS natif', 0)
            + platform_counts.get('iOS / iPadOS Web Push', 0)
            + platform_counts.get('Safari Web Push', 0)
        ),
        'web_chrome_subscribed': platform_counts.get('Web Chrome', 0),
        'sessions_total': sessions_total,
        'playtime_total_seconds': playtime_total,
        'apk_downloads': apk_downloads,
        'apk_release_updated_at': apk_release_updated_at,
        'apk_size_bytes': apk_size,
        'messages_total_api_visible': messages_total_api_visible,
        'messages_loaded': len(messages),
        'notifications_sent_recent': notifications_sent,
        'notifications_received_recent': notifications_received,
        'notifications_clicked_recent': notifications_clicked,
        'notifications_failed_recent': notifications_failed,
    },
    'platform_counts': dict(platform_counts),
    'country_counts': dict(country_counts.most_common(50)),
    'version_counts': dict(version_counts.most_common(50)),
    'subscriptions': sorted(subscriptions, key=lambda x: x.get('created_at') or '', reverse=True),
    'messages': messages,
}

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Métriques écrites dans {OUT} : {subscribed} abonnés actifs, {unsubscribed} désabonnés, {apk_downloads} téléchargements APK, {len(errors)} avertissement(s).')
for err in errors:
    print('AVERTISSEMENT:', err)
