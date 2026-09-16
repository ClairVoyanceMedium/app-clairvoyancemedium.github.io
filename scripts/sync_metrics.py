#!/usr/bin/env python3
import csv
import gzip
import hashlib
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
ADMIN_EXTERNAL_ID = os.environ.get('ADMIN_EXTERNAL_ID', 'cvm_admin_frederick').strip()
TRACKING_START_RAW = os.environ.get('INSTALL_TRACKING_START', '2026-09-16T15:20:00Z').strip()

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
            raw = r.read().decode('utf-8')
            return json.loads(raw) if raw else {}
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
        raw = str(value)
        try:
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            return raw


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
        number = float(str(value))
        if number > 100000000000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def parse_tags(value):
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    raw = str(value or '').strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return {str(k): str(v) for k, v in obj.items()}
    except json.JSONDecodeError:
        pass
    return {}


def anonymous_id(sid, tags):
    install_id = str(tags.get('install_id') or '').strip()
    if install_id:
        return install_id[:12] + ('…' if len(install_id) > 12 else '')
    if not sid:
        return '—'
    return hashlib.sha256(sid.encode('utf-8')).hexdigest()[:12]


def platform_name(row, tags=None):
    tags = tags or parse_tags(row.get('tags'))
    tagged = str(tags.get('platform') or '').strip()
    if tagged == 'android_native':
        return 'Android'
    if tagged == 'ios_native':
        return 'iOS natif'
    if tagged == 'ios_web':
        return 'iOS / iPadOS Web Push'

    dtype = str(row.get('device_type', '')).strip()
    return {
        '0': 'iOS natif',
        '1': 'Android',
        '2': 'Amazon Fire',
        '5': 'Web Chrome',
        '7': 'Safari Web Push',
        '17': 'Safari Web Push',
    }.get(dtype, f'Autre ({dtype or "inconnu"})')


def push_status(row, invalid, notification_types):
    token = bool(str(row.get('identifier', '') or '').strip())
    if not invalid and notification_types > 0 and token:
        return 'activé'
    if notification_types == 0:
        return 'non autorisé'
    return 'désactivé ou invalide'


def message_target(msg):
    aliases = msg.get('include_aliases') or {}
    if ADMIN_EXTERNAL_ID in (aliases.get('external_id') or []):
        return 'Administrateur'
    segments = msg.get('included_segments') or []
    if 'Subscribed Users' in segments:
        return 'Tous les abonnés'
    filters = msg.get('filters') or []
    joined = json.dumps(filters, ensure_ascii=False)
    if 'android_native' in joined:
        return 'Android'
    if 'ios_web' in joined or 'ios_native' in joined:
        return 'iPhone / iPad'
    return ''


subscriptions = []
messages = []
messages_total_api_visible = 0

if not APP_ID or not API_KEY:
    errors.append('Clés OneSignal manquantes dans GitHub Secrets. Les métriques OneSignal ne peuvent pas être lues.')
else:
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
            sid = str(row.get('id', '') or '').strip()
            tags = parse_tags(row.get('tags'))
            created_at = unix_or_iso(row.get('created_at'))
            first_install_at = unix_or_iso(tags.get('first_install_ts')) or created_at
            external_id = str(row.get('external_user_id', '') or '').strip()
            subscriptions.append({
                'anonymous_id': anonymous_id(sid, tags),
                'id_short': sid[:8] + ('…' if len(sid) > 8 else ''),
                'is_admin': external_id == ADMIN_EXTERNAL_ID,
                'platform': platform_name(row, tags),
                'status': 'abonné' if push_subscribed else 'désabonné',
                'push_status': push_status(row, invalid, notification_types),
                'created_at': created_at,
                'first_install_at': first_install_at,
                'last_active': unix_or_iso(row.get('last_active')),
                'unsubscribed_at': unix_or_iso(row.get('unsubscribed_at')),
                'country': row.get('country') or '',
                'language': row.get('language') or tags.get('device_locale') or '',
                'timezone': row.get('timezone_id') or '',
                'device_model': row.get('device_model') or '',
                'device_os': row.get('device_os') or '',
                'app_version': row.get('game_version') or '',
                'install_source': tags.get('install_source') or tags.get('distribution') or '',
                'session_count': int(float(row.get('session_count') or 0)),
                'playtime_seconds': int(float(row.get('playtime') or 0)),
                'notification_types': row.get('notification_types') or '',
            })
    except Exception as exc:
        errors.append(f'Abonnements OneSignal indisponibles: {exc}')

    try:
        limit = 50
        max_history = 200
        offset = 0
        while offset < max_history:
            messages_response = request_json(
                f'https://api.onesignal.com/notifications?app_id={urllib.parse.quote(APP_ID)}&limit={limit}&offset={offset}'
            )
            if offset == 0:
                messages_total_api_visible = int(messages_response.get('total_count') or 0)

            batch = messages_response.get('notifications', []) or []
            for msg in batch:
                headings = msg.get('headings') or {}
                contents = msg.get('contents') or {}
                messages.append({
                    'id': msg.get('id'),
                    'name': msg.get('name') or '',
                    'target': message_target(msg),
                    'title': headings.get('fr') or headings.get('en') or msg.get('name') or '',
                    'message': contents.get('fr') or contents.get('en') or '',
                    'queued_at': unix_or_iso(msg.get('queued_at')),
                    'send_after': unix_or_iso(msg.get('send_after')),
                    'delayed_option': msg.get('delayed_option') or '',
                    'delivery_time_of_day': msg.get('delivery_time_of_day') or '',
                    'completed_at': unix_or_iso(msg.get('completed_at')),
                    'successful': int(msg.get('successful') or 0),
                    'received': int(msg.get('received') or 0),
                    'clicked': int(msg.get('converted') or 0),
                    'failed': int(msg.get('failed') or 0),
                    'errored': int(msg.get('errored') or 0),
                    'remaining': int(msg.get('remaining') or 0),
                    'url': msg.get('url') or msg.get('web_url') or msg.get('app_url') or '',
                })

            if len(batch) < limit:
                break
            if messages_total_api_visible and offset + limit >= messages_total_api_visible:
                break
            offset += limit

        if not messages_total_api_visible:
            messages_total_api_visible = len(messages)
    except Exception as exc:
        errors.append(f'Notifications OneSignal indisponibles: {exc}')


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
tracking_start = parse_dt(TRACKING_START_RAW) or now
new_24h = 0
active_7d = 0
active_30d = 0
installations = []

for s in subscriptions:
    created = parse_dt(s.get('created_at'))
    last_active = parse_dt(s.get('last_active'))
    first_install = parse_dt(s.get('first_install_at'))
    if created and (now - created).total_seconds() <= 86400:
        new_24h += 1
    if last_active and s['status'] == 'abonné':
        age = (now - last_active).total_seconds()
        if age <= 7 * 86400:
            active_7d += 1
        if age <= 30 * 86400:
            active_30d += 1
    if first_install and first_install >= tracking_start and not s.get('is_admin'):
        installations.append({
            'anonymous_id': s.get('anonymous_id') or '—',
            'detected_at': s.get('first_install_at') or s.get('created_at'),
            'platform': s.get('platform') or '',
            'device_model': s.get('device_model') or '',
            'device_os': s.get('device_os') or '',
            'app_version': s.get('app_version') or '',
            'country': s.get('country') or '',
            'timezone': s.get('timezone') or '',
            'language': s.get('language') or '',
            'install_source': s.get('install_source') or '',
            'push_status': s.get('push_status') or '',
            'session_count': s.get('session_count') or 0,
            'playtime_seconds': s.get('playtime_seconds') or 0,
            'last_active': s.get('last_active'),
        })

installations.sort(key=lambda x: x.get('detected_at') or '', reverse=True)
installations_last_24h = sum(
    1
    for item in installations
    if (dt := parse_dt(item.get('detected_at'))) is not None
    and (now - dt).total_seconds() <= 86400
)
installation_platform_counts = Counter(i['platform'] or 'Inconnu' for i in installations)
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
    'privacy': (
        'Les tokens push, adresses IP et identifiants OneSignal complets sont exclus. '
        'Les installations sont représentées par un identifiant technique anonyme. '
        'Le pays est approximatif et provient de OneSignal; aucune localisation GPS n’est collectée par ce tableau.'
    ),
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
        'install_tracking_start': tracking_start.isoformat(),
        'installations_detected': len(installations),
        'installations_last_24h': installations_last_24h,
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
    'installation_platform_counts': dict(installation_platform_counts),
    'installations': installations[:500],
    'subscriptions': sorted(subscriptions, key=lambda x: x.get('created_at') or '', reverse=True),
    'messages': sorted(messages, key=lambda x: x.get('queued_at') or '', reverse=True),
}

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(
    f'Métriques écrites dans {OUT} : {subscribed} abonnés actifs, {unsubscribed} désabonnés, '
    f'{apk_downloads} téléchargements APK, {len(installations)} installation(s) détectée(s) depuis le suivi, '
    f'{len(messages)} notifications dans l’historique, {len(errors)} avertissement(s).'
)
for err in errors:
    print('AVERTISSEMENT:', err)
