"""Daily, authorized Twitch clip rendering with private Supabase Storage.

Does not publish content. No Twitch privileged tokens/cookies used.
"""
import json
import os
import subprocess
import sys
import tempfile
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

def validate_twitch_clip_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or (parts.hostname or '').lower() not in ('www.twitch.tv', 'twitch.tv', 'clips.twitch.tv'):
        raise ValueError('URL não é HTTPS da Twitch')
    segment = parts.path.strip('/')
    if parts.hostname == 'clips.twitch.tv':
        ok = bool(re.fullmatch(r'[A-Za-z0-9_-]{8,150}', segment))
    else:
        ok = bool(re.fullmatch(r'[A-Za-z0-9_]{2,30}/clip/[A-Za-z0-9_-]{8,150}', segment))
    if not ok:
        raise ValueError('URL de clipe inválida')
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


BUCKET = 'caos60-shorts'
MAX_DAILY = 3


def request(table, method='GET', params=None, payload=None, prefer=None):
    base = os.environ['SUPABASE_URL'].rstrip('/')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    qs = urllib.parse.urlencode(params or {})
    url = f'{base}/rest/v1/{table}' + ('?' + qs if qs else '')
    headers = {'apikey': key, 'Authorization': 'Bearer ' + key,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    if prefer:
        headers['Prefer'] = prefer
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read()
        return json.loads(raw) if raw else []


def claim(item):
    """Conditional update prevents processing a row already claimed elsewhere."""
    result = request('clip_queue', 'PATCH',
                     {'clip_id': 'eq.' + item['clip_id'], 'status': 'eq.awaiting_media', 'select': 'clip_id'},
                     {'status': 'rendering', 'updated_at': datetime.now(timezone.utc).isoformat(), 'error_message': None},
                     'return=representation')
    return bool(result)


def mark(clip_id, status, error=None, media_path=None):
    data = {'status': status, 'updated_at': datetime.now(timezone.utc).isoformat(),
            'error_message': (str(error)[:400] if error else None)}
    if media_path:
        data['media_path'] = media_path
        data['rendered_at'] = datetime.now(timezone.utc).isoformat()
    return request('clip_queue', 'PATCH', {'clip_id': 'eq.' + clip_id}, data,
                   'return=minimal')


def load_candidates():
    queue = request('clip_queue', params={
        'select': 'clip_id,rank_score,selected_at', 'status': 'eq.awaiting_media',
        'order': 'rank_score.desc', 'limit': '30'})
    result = []
    for q in queue:
        clips = request('clips', params={
            'select': 'id,source_id,title,original_url', 'id': 'eq.' + q['clip_id'], 'limit': '1'})
        if not clips:
            continue
        clip = clips[0]
        sources = request('sources', params={
            'select': 'platform,enabled,rights_verified',
            'id': 'eq.' + str(clip['source_id']), 'limit': '1'})
        if not sources or not sources[0].get('enabled') or not sources[0].get('rights_verified') or sources[0]['platform'] != 'twitch':
            continue
        try:
            clip['original_url'] = validate_twitch_clip_url(clip['original_url'])
        except ValueError:
            continue
        result.append(clip)
    return result


def render(clip, folder):
    folder = Path(folder)
    source = folder / 'source.ts'
    output = folder / 'short.mp4'
    subprocess.run(['streamlink', '--loglevel', 'warning', '--retry-max', '1',
                    '--output', str(source), clip['original_url'], 'best'],
                   check=True, timeout=180)
    if not source.is_file() or source.stat().st_size < 100_000:
        raise RuntimeError('mídia vazia ou indisponível')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                    '-t', '60', '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28', '-maxrate', '1800k',
                    '-bufsize', '3600k', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
                    '-movflags', '+faststart', str(output)], check=True, timeout=420)
    subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1', str(output)], check=True, timeout=20)
    if not output.exists() or output.stat().st_size < 100_000:
        raise RuntimeError('arquivo MP4 inválido')
    if output.stat().st_size > 50 * 1024 * 1024:
        raise RuntimeError('arquivo acima de 50 MB')
    return output


def upload(path, clip_id):
    """Uploads a completed private MP4; never returns a public URL."""
    base = os.environ['SUPABASE_URL'].rstrip('/')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    object_path = f'{clip_id}.mp4'
    url = base + '/storage/v1/object/' + BUCKET + '/' + object_path
    # Standard uploads are less reliable above 6 MB. Size limits and errors are explicit.
    body = Path(path).read_bytes()
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'apikey': key, 'Authorization': 'Bearer ' + key,
        'Content-Type': 'video/mp4', 'Cache-Control': '3600',
        'x-upsert': 'false'})
    with urllib.request.urlopen(req, timeout=180) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError('falha no upload Storage')
    return object_path


def count_today():
    start = datetime.now(timezone.utc).date().isoformat() + 'T00:00:00Z'
    rows = request('clip_queue', params={
        'select': 'clip_id', 'rendered_at': 'gte.' + start,
        'status': 'in.(rendered,publishing,published)', 'limit': '100'})
    return len(rows)


def main():
    if not os.getenv('SUPABASE_URL', '').startswith('https://') or not os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
        raise SystemExit('Secrets SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY obrigatórios')
    remaining = max(0, MAX_DAILY - count_today())
    print('Meta diária: até', MAX_DAILY, '| vagas restantes:', remaining, flush=True)
    if not remaining:
        return
    failures = 0
    successes = 0
    for clip in load_candidates():
        if successes >= remaining:
            break
        clip_id = clip['id']
        if not claim({'clip_id': clip_id}):
            continue
        try:
            print('Processando:', clip_id, flush=True)
            with tempfile.TemporaryDirectory() as directory:
                file = render(clip, directory)
                object_path = upload(file, clip_id)
            mark(clip_id, 'rendered', media_path=object_path)
            successes += 1
            print('Renderizado e armazenado:', clip_id, flush=True)
        except (RuntimeError, subprocess.TimeoutExpired, subprocess.CalledProcessError,
                urllib.error.URLError, OSError, ValueError) as exc:
            failures += 1
            print('Falha no clipe:', clip_id, type(exc).__name__, flush=True)
            mark(clip_id, 'awaiting_media', error=f'{type(exc).__name__}: falha na captura, render ou upload')
    print(f'Concluído: {successes} vídeo(s); {failures} falha(s).', flush=True)
    if failures:
        raise SystemExit('Parte dos clipes falhou; confira os logs, sem expor secrets.')


if __name__ == '__main__':
    main()
