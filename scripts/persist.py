"""Persist authorized Twitch clip metadata to Supabase REST, without resetting status.

Uses only Python stdlib. Intended to run on GitHub Actions with repository secrets.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def api_request(base_url, api_key, table, method='GET', query='', payload=None):
    url = f"{base_url.rstrip('/')}/rest/v1/{table}" + (f'?{query}' if query else '')
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return json.loads(body) if body else []


def persist(clips, base_url, api_key, request_fn=api_request):
    sources = request_fn(base_url, api_key, 'sources', query='select=id,platform,channel,enabled,rights_verified')
    active = {(s['platform'], s['channel'].lower()): s['id'] for s in sources
              if s.get('enabled') and s.get('rights_verified')}
    accepted = []
    for c in clips:
        key = (c.get('source', ''), c.get('channel', '').lower())
        if key not in active:
            continue
        if not c.get('id') or not c.get('url'):
            continue
        accepted.append({
            'source_id': active[key], 'platform_clip_id': c['id'],
            'title': c.get('title') or '', 'original_url': c['url'],
            'views': max(0, int(c.get('views') or 0)), 'status': 'discovered',
        })
    accepted = list({c['platform_clip_id']: c for c in accepted}.values())
    if not accepted:
        print('Nenhum clipe autorizado para persistência.')
        return (0, 0)
    inserted = updated = 0
    # Keep URLs short and queries bounded; ensures status of rendered/published clips is preserved.
    for start in range(0, len(accepted), 40):
        chunk = accepted[start:start + 40]
        ids = [r['platform_clip_id'] for r in chunk]
        query = urllib.parse.urlencode({'select':'platform_clip_id,views', 'platform_clip_id':f'in.({",".join(ids)})'})
        existing = {c['platform_clip_id']: c for c in request_fn(base_url, api_key, 'clips', query=query)}
        new = [row for row in chunk if row['platform_clip_id'] not in existing]
        if new:
            request_fn(base_url, api_key, 'clips', method='POST', payload=new)
            inserted += len(new)
        for row in chunk:
            prior = existing.get(row['platform_clip_id'])
            if prior and row['views'] != prior['views']:
                eq = urllib.parse.urlencode({'platform_clip_id':f"eq.{row['platform_clip_id']}"})
                request_fn(base_url, api_key, 'clips', method='PATCH', query=eq, payload={'views': row['views']})
                updated += 1
    print(f'Supabase: {inserted} novos, {updated} visualizações atualizadas, {len(accepted)} válidos.')
    return (inserted, updated)


def main():
    base_url = os.environ.get('SUPABASE_URL', '').strip()
    api_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not base_url.startswith('https://') or not api_key:
        raise SystemExit('Configure SUPABASE_URL (https) e SUPABASE_SERVICE_ROLE_KEY nos GitHub Secrets.')
    path = Path('output/discovered.json')
    if not path.is_file():
        raise SystemExit('Arquivo output/discovered.json ausente.')
    clips = json.loads(path.read_text(encoding='utf-8'))['clips']
    try:
        persist(clips, base_url, api_key)
    except urllib.error.HTTPError as exc:
        # Avoid printing HTTP bodies: may contain unexpected sensitive info.
        raise SystemExit(f'Erro HTTP Supabase: {exc.code} na operação REST.') from None


if __name__ == '__main__':
    main()
