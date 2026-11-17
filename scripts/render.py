"""Render an authorized local MP4 into a vertical short; requires FFmpeg."""
import argparse
import subprocess
from pathlib import Path


def build_command(source, destination, seconds):
    return ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
            '-t', str(seconds), '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(destination)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--seconds', type=int, default=30)
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error('Arquivo de origem não encontrado')
    if not 1 <= args.seconds <= 60:
        parser.error('O corte deve ter entre 1 e 60 segundos')
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_command(args.source, args.destination, args.seconds), check=True)
    print(f'Vídeo gerado: {args.destination}')


if __name__ == '__main__':
    main()
