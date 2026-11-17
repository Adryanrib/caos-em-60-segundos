"""Experimental media acquisition of a permitted public Twitch clip.

Only obtains publicly accessible playback with Streamlink. Never uses private
endpoints directly, cookies, tokens or circumvented access controls.
Does not mark queued clips as processed; artifact inspection comes first.
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'https://www.twitch.tv/'


def supabase_request(path, params):
    url = os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/' + path
    url += '?' + urllib.parse.urlencode(params)
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    req = urllib.request.Request(url, headers={
        'apikey': key, 'Authorization': 'Bearer ' + key,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


def validate_twitch_clip_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or (parts.hostname or '').lower() not in ('www.twitch.tv', 'twitch.tv', 'clips.twitch.tv'):
        raise ValueError('A origem precisa ser uma URL HTTPS de clipe da Twitch')
    path = parts.path.strip('/')
    if parts.hostname == 'clips.twitch.tv':
        valid = bool(re.fullmatch(r'[A-Za-z0-9_-]{8,150}', path))
    else:
        valid = bool(re.fullmatch(r'[A-Za-z0-9_]{2,30}/clip/[A-Za-z0-9_-]{8,150}', path))
    if not valid:
        raise ValueError('URL Twitch inválida ou não é de um clipe')
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def select_candidate():
    queue = supabase_request('clip_queue', {
        'select': 'clip_id,rank_score,selected_at',
        'status': 'eq.awaiting_media',
        'order': 'rank_score.desc',
        'limit': '20',
    })
    for item in queue:
        clips = supabase_request('clips', {
            'select': 'id,source_id,title,original_url',
            'id': 'eq.' + item['clip_id'],
            'limit': '1',
        })
        if not clips:
            continue
        clip = clips[0]
        sources = supabase_request('sources', {
            'select': 'id,platform,channel,enabled,rights_verified',
            'id': 'eq.' + str(clip['source_id']),
            'limit': '1',
        })
        if not sources or not sources[0]['enabled'] or not sources[0]['rights_verified'] or sources[0]['platform'] != 'twitch':
            continue
        try:
            clip['original_url'] = validate_twitch_clip_url(clip['original_url'])
        except ValueError:
            continue
        return clip
    raise RuntimeError('Nenhum clipe Twitch autorizado aguardando mídia')


def run_checked(args, timeout):
    subprocess.run(args, check=True, timeout=timeout)


def main():
    for key in ('SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'):
        if not os.getenv(key):
            raise SystemExit('Secret obrigatório ausente: ' + key)
    if not os.environ['SUPABASE_URL'].startswith('https://'):
        raise SystemExit('Supabase URL deve ser HTTPS')

    candidate = select_candidate()
    out = Path('output')
    out.mkdir(exist_ok=True)
    source_file = out / 'source.ts'
    final_file = out / 'clip-vertical.mp4'
    # Streamlink supports Twitch clip URLs. This is an EXPERIMENT, not a guarantee.
    # Streamlink may use Twitch's public playback endpoints internally. Never
    # supply privileged session data or attempt bypasses if blocked.
    print('Tentando clipe selecionado:', candidate['title'][:100], flush=True)
    run_checked(['streamlink', '--loglevel', 'warning', '--retry-max', '1',
                 '--output', str(source_file), candidate['original_url'], 'best'], timeout=160)
    if not source_file.exists() or source_file.stat().st_size < 100_000:
        raise RuntimeError('Streamlink não forneceu um vídeo utilizável')
    # Keep game action readable: center crop to 9:16, h264/aac, <= 60s.
    # Quality can be improved later with camera-aware composition.
    run_checked(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                 '-i', str(source_file), '-t', '60',
                 '-vf', "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25',
                 '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                 str(final_file)], timeout=400)
    run_checked(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size',
                 '-of', 'default=noprint_wrappers=1', str(final_file)], timeout=20)
    (out / 'metadata.json').write_text(json.dumps({
        'clip_id': candidate['id'], 'title': candidate['title'],
        'source_url': candidate['original_url'], 'output': 'clip-vertical.mp4',
        'publication_status': 'not_published',
        'note': 'Experimento de captura por reprodução pública; não altera Supabase.'
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    source_file.unlink(missing_ok=True)
    print('Concluído: output/clip-vertical.mp4. Nenhuma publicação foi realizada.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError) as e:
        print('Falha de captura/renderização (fila inalterada):', type(e).__name__, file=sys.stderr)
        raise SystemExit(1)
