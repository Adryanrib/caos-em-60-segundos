"""Discover Twitch clips via official Helix API; metadata only, no media download."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = 'https://api.twitch.tv/helix'


def request(url, headers=None, form=None):
    data = urllib.parse.urlencode(form).encode() if form else None
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


def api_headers():
    client_id = os.environ.get('TWITCH_CLIENT_ID', '').strip()
    client_secret = os.environ.get('TWITCH_CLIENT_SECRET', '').strip()
    if not client_id or not client_secret:
        raise RuntimeError('Configure TWITCH_CLIENT_ID e TWITCH_CLIENT_SECRET como GitHub Actions secrets.')
    token = request('https://id.twitch.tv/oauth2/token', form={
        'client_id': client_id, 'client_secret': client_secret,
        'grant_type': 'client_credentials',
    })['access_token']
    return {'Client-Id': client_id, 'Authorization': f'Bearer {token}'}


def discover(channels, now=None):
    now = now or datetime.now(timezone.utc)
    start = (now - timedelta(hours=24)).isoformat(timespec='seconds').replace('+00:00', 'Z')
    end = now.isoformat(timespec='seconds').replace('+00:00', 'Z')
    headers = api_headers()
    output = []
    for login in channels:
        users = request(f'{API}/users?' + urllib.parse.urlencode({'login': login}), headers)
        if not users['data']:
            print(f'Canal não encontrado: {login}', file=sys.stderr)
            continue
        broadcaster_id = users['data'][0]['id']
        params = urllib.parse.urlencode({'broadcaster_id': broadcaster_id, 'started_at': start, 'ended_at': end, 'first': 100})
        clips = request(f'{API}/clips?{params}', headers)
        for clip in clips.get('data', []):
            output.append({
                'id': clip['id'], 'source': 'twitch', 'channel': login,
                'title': clip.get('title', ''), 'url': clip.get('url', ''),
                'created_at': clip.get('created_at', ''),
                'duration': clip.get('duration', 0), 'views': clip.get('view_count', 0),
                'thumbnail_url': clip.get('thumbnail_url', ''),
                'status': 'discovered',
            })
    return sorted({c['id']: c for c in output}.values(), key=lambda c: c['views'], reverse=True)


def main():
    source_file = Path('sources.json')
    config = json.loads(source_file.read_text(encoding='utf-8'))
    channels = sorted({s['channel'].strip().lower() for s in config['sources'] if s.get('enabled') and s.get('platform') == 'twitch'})
    if not channels:
        raise SystemExit('Nenhuma fonte Twitch ativa em sources.json')
    clips = discover(channels)
    Path('output').mkdir(exist_ok=True)
    Path('output/discovered.json').write_text(json.dumps({'generated_at': datetime.now(timezone.utc).isoformat(), 'clips': clips}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Descoberta concluída: {len(clips)} clipes; {len(channels)} canais. Arquivo: output/discovered.json')


if __name__ == '__main__':
    main()
