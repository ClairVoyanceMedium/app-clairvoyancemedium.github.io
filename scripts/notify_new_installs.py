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
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

APP_ID = os.environ.get('ONESIGNAL_APP_ID', '').strip()
API_KEY = os.environ.get('ONESIGNAL_API_KEY', '').strip()
ADMIN_EXTERNAL_ID = os.environ.get('ADMIN_EXTERNAL_ID', 'cvm_admin_frederick').strip()
OUTPUT_PATH = Path(os.environ.get('INSTALL_EVENTS_OUTPUT', 'install-events-private.json'))
ADMIN_URL = os.environ.get(
    'ADMIN_DASHBOARD_URL',
    'https://clairvoyancemedium.github.io/app-clairvoyancemedium.github.io/admin.html',
).strip()
TRACKING_START_RAW = os.environ.get('TRACKING_START', '2026-09-16T15:20:00Z').strip()
LOOKBACK_HOURS = max(1, min(24 * 7, int(os.environ.get('INSTALL_ALERT_LOOKBACK_HOURS', '168'))))

HEADERS = {
    'Authorization': f'Key {API_KEY}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

PLATFORMS = {
    '0': 'iPhone / iPad',
    '1': 'Android',
    '2': 'Amazon Fire',
    '5': 'Web Chrome',
    '7': 'Safari Web Push',
    '17': 'Safari Web Push',
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


def export_rows():
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
    url = export.get('csv_file_url')
    if not url:
        raise RuntimeError(f'Export CSV OneSignal invalide: {export}')

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
        raise RuntimeError('Le CSV OneSignal n’a pas pu être téléchargé.')

    try:
        text = gzip.decompress(raw).decode('utf-8-sig')
    except OSError:
        text = raw.decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text)))


def parse_dt(value):
    if value in (None, '', 'null'):
        return None
    raw = str(value).strip()
    try:
        number = float(raw)
        if number > 100000000000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
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


def ntype(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 't', 'yes', 'y'}


def short_install_id(row, tags):
    install_id = str(tags.get('install_id') or '').strip()
    if install_id:
        return install_id[:12] + ('…' if len(install_id) > 12 else '')
    sid = str(row.get('id', '') or '').strip()
    return hashlib.sha256(sid.encode('utf-8')).hexdigest()[:12] if sid else '—'


def platform_name(row, tags):
    tag_platform = str(tags.get('platform') or '').strip()
    if tag_platform == 'android_native':
        return 'Android'
    if tag_platform == 'ios_native':
        return 'iPhone / iPad'
    return PLATFORMS.get(str(row.get('device_type', '') or '').strip(), 'Autre')


def install_time(row, tags):
    return parse_dt(tags.get('first_install_ts')) or parse_dt(row.get('created_at'))


def local_time_text(dt, timezone_id):
    if not dt:
        return 'heure inconnue'
    try:
        zone = ZoneInfo(timezone_id) if timezone_id else ZoneInfo('Europe/Paris')
        local = dt.astimezone(zone)
    except Exception:
        local = dt.astimezone(ZoneInfo('Europe/Paris'))
    return local.strftime('%d/%m/%Y à %H:%M')


def push_status(row):
    value = ntype(row.get('notification_types'))
    token = bool(str(row.get('identifier', '') or '').strip())
    invalid = truthy(row.get('invalid_identifier'))
    if value > 0 and token and not invalid:
        return 'activé'
    if value == 0:
        return 'non autorisé'
    return 'désactivé ou invalide'


def safe_event(row):
    tags = parse_tags(row.get('tags'))
    dt = install_time(row, tags)
    tz = str(row.get('timezone_id', '') or row.get('timezone', '') or '').strip()
    country = str(row.get('country', '') or '').strip().upper()
    language = str(row.get('language', '') or tags.get('device_locale') or '').strip()
    external_id = str(row.get('external_user_id', '') or '').strip()
    return {
        'anonymous_id': short_install_id(row, tags),
        'platform': platform_name(row, tags),
        'detected_at': dt.isoformat() if dt else None,
        'detected_local': local_time_text(dt, tz),
        'country': country,
        'timezone': tz,
        'language': language,
        'device_model': str(row.get('device_model', '') or '').strip(),
        'device_os': str(row.get('device_os', '') or '').strip(),
        'app_version': str(row.get('game_version', '') or row.get('app_version', '') or '').strip(),
        'session_count': int(float(row.get('session_count') or 0)),
        'playtime_seconds': int(float(row.get('playtime') or 0)),
        'push_status': push_status(row),
        'install_source': str(tags.get('install_source') or tags.get('distribution') or '').strip(),
        'is_admin': external_id == ADMIN_EXTERNAL_ID,
    }


def alert_idempotency_key(subscription_id):
    # UUID RFC 9562 stable pour cette installation. OneSignal déduplique les
    # répétitions pendant 30 jours; on ne recontrôle ici que les 7 derniers jours.
    logical_id = f'https://www.clairvoyancemedium.com/install-alert/{APP_ID}/{subscription_id}'
    return str(uuid.uuid5(uuid.NAMESPACE_URL, logical_id))


def send_admin_alert(row, event):
    subscription_id = str(row.get('id', '') or '').strip()
    device = event['device_model'] or 'appareil inconnu'
    country = event['country'] or 'pays inconnu'
    body = (
        f"{event['platform']} · {device} · {country} · "
        f"{event['detected_local']} · push {event['push_status']}"
    )
    payload = {
        'app_id': APP_ID,
        'target_channel': 'push',
        'include_aliases': {'external_id': [ADMIN_EXTERNAL_ID]},
        'headings': {
            'fr': 'Nouvelle installation détectée',
            'en': 'New installation detected',
        },
        'contents': {'fr': body, 'en': body},
        'name': 'CVM installation ' + event['anonymous_id'],
        'url': ADMIN_URL,
        'idempotency_key': alert_idempotency_key(subscription_id),
        'custom_data': {
            'event': 'new_installation',
            'anonymous_id': event['anonymous_id'],
            'platform': event['platform'],
            'country': event['country'],
        },
    }
    result = request_json(
        'https://api.onesignal.com/notifications?c=push',
        method='POST',
        payload=payload,
    )
    if not result.get('id'):
        raise RuntimeError(
            'OneSignal n’a pas accepté l’alerte administrateur: '
            + json.dumps(result, ensure_ascii=False)
        )
    return result['id']


now = datetime.now(timezone.utc)
tracking_start = parse_dt(TRACKING_START_RAW) or now
lookback_start = max(tracking_start, now - timedelta(hours=LOOKBACK_HOURS))
errors = []
feed = []
alert_attempts = 0
alert_acceptances = 0

if not APP_ID or not API_KEY:
    errors.append('Clés OneSignal absentes: détection des installations impossible.')
    rows = []
else:
    try:
        rows = export_rows()
    except Exception as exc:
        rows = []
        errors.append(f'Export OneSignal impossible: {exc}')

for row in rows:
    sid = str(row.get('id', '') or '').strip()
    if not sid:
        continue
    tags = parse_tags(row.get('tags'))
    detected = install_time(row, tags)
    if not detected or detected < tracking_start:
        continue

    event = safe_event(row)
    if event['is_admin']:
        continue
    feed.append(event)

    if detected < lookback_start:
        continue

    alert_attempts += 1
    try:
        message_id = send_admin_alert(row, event)
        alert_acceptances += 1
        print(json.dumps({
            'status': 'install_alert_accepted_or_deduplicated',
            'message_id': message_id,
            'anonymous_id': event['anonymous_id'],
            'platform': event['platform'],
            'device_model': event['device_model'],
            'country': event['country'],
            'detected_at': event['detected_at'],
        }, ensure_ascii=False))
    except Exception as exc:
        errors.append(f"Alerte {event['anonymous_id']} non envoyée: {exc}")

feed.sort(key=lambda x: x.get('detected_at') or '', reverse=True)
last_24h = sum(
    1
    for event in feed
    if (dt := parse_dt(event.get('detected_at'))) is not None
    and (now - dt).total_seconds() <= 86400
)
platform_counts = {}
for event in feed:
    platform_counts[event['platform']] = platform_counts.get(event['platform'], 0) + 1

output = {
    'generated_at': now.isoformat(),
    'tracking_start': tracking_start.isoformat(),
    'privacy': (
        'Flux privé et pseudonymisé: aucun token push, aucune adresse IP et aucun identifiant OneSignal complet. '
        'Le pays est une information réseau approximative fournie par OneSignal. Aucune localisation GPS n’est activée.'
    ),
    'summary': {
        'installations_detected': len(feed),
        'installations_last_24h': last_24h,
        'alert_attempts': alert_attempts,
        'alert_requests_accepted_or_deduplicated': alert_acceptances,
    },
    'platform_counts': platform_counts,
    'errors': errors,
    'installations': feed[:500],
}
OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(
    f"Flux installations écrit dans {OUTPUT_PATH}: {len(feed)} installation(s) depuis l’activation, "
    f"{alert_attempts} vérification(s) d’alerte, {len(errors)} avertissement(s)."
)
for error in errors:
    print('AVERTISSEMENT:', error)
