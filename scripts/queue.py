"""Select up to three authorized Twitch clip candidates daily (metadata only)."""
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


def rest(base, key, table, params=None, rows=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{base.rstrip('/')}/rest/v1/{table}" + (f'?{query}' if query else '')
    headers = {'apikey': key, 'Authorization': 'Bearer ' + key,
               'Content-Type': 'application/json', 'Accept': 'application/json'}
    if rows is not None:
        headers['Prefer'] = 'resolution=ignore-duplicates,return=representation'
    req = urllib.request.Request(url, headers=headers,
                                 data=json.dumps(rows).encode() if rows is not None else None,
                                 method='POST' if rows is not None else 'GET')
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
        return json.loads(data) if data else []


def rating(clip, now):
    views = max(0, int(clip.get('views') or 0))
    timestamp = datetime.fromisoformat(clip['created_at'].replace('Z', '+00:00'))
    age_hours = max(0, (now - timestamp).total_seconds() / 3600)
    return round(min(80, math.log1p(views) * 14) + max(0, 20 - age_hours / 12), 2)


def choose(clips, queued_ids, count, now):
    options = [c for c in clips if c['id'] not in queued_ids and
               c.get('status') == 'discovered' and c.get('original_url')]
    options.sort(key=lambda c: (-rating(c, now), c['id']))
    return options[:count]


def enqueue(base, key, now=None, daily_max=3, transport=rest):
    now = now or datetime.now(timezone.utc)
    start = now.date().isoformat() + 'T00:00:00Z'
    end = (now.date() + timedelta(days=1)).isoformat() + 'T00:00:00Z'
    today = transport(base, key, 'clip_queue', {
        'select': 'clip_id', 'selected_at': f'gte.{start}',
        'and': f'(selected_at.lt.{end})', 'limit': '1000'})
    remaining = max(0, daily_max - len(today))
    if not remaining:
        print('Limite diário atingido.'); return []
    sources = transport(base, key, 'sources', {
        'select': 'id', 'enabled': 'eq.true', 'rights_verified': 'eq.true'})
    authorized = {x['id'] for x in sources}
    if not authorized:
        print('Nenhuma fonte autorizada.'); return []
    clips = transport(base, key, 'clips', {
        'select': 'id,source_id,title,original_url,views,status,created_at',
        'status': 'eq.discovered', 'order': 'views.desc', 'limit': '200'})
    clips = [c for c in clips if c['source_id'] in authorized]
    if not clips:
        print('Nenhum candidato disponível.'); return []
    ids = ','.join(c['id'] for c in clips)
    existing = transport(base, key, 'clip_queue', {
        'select': 'clip_id', 'clip_id': f'in.({ids})', 'limit': '1000'})
    selected = choose(clips, {r['clip_id'] for r in existing}, remaining, now)
    if not selected:
        print('Todos os candidatos já selecionados.'); return []
    records = [{'clip_id': c['id'], 'rank_score': rating(c, now),
                'status': 'awaiting_media'} for c in selected]
    result = transport(base, key, 'clip_queue', {'on_conflict': 'clip_id'}, records)
    print(f'Selecionados {len(result)} clipes aguardando arquivos de mídia.')
    return result


if __name__ == '__main__':
    url = os.environ.get('SUPABASE_URL', '').strip()
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not url.startswith('https://') or not key:
        raise SystemExit('Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.')
    try:
        enqueue(url, key)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'Erro HTTP {exc.code} no Supabase.') from None
