"""Create a synthetic MP4 to confirm the cloud FFmpeg worker works."""
import subprocess
from pathlib import Path
Path('output').mkdir(exist_ok=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y', '-f','lavfi','-i','testsrc2=size=720x1280:rate=24', '-f','lavfi','-i','sine=frequency=440:sample_rate=44100', '-t','5', '-c:v','libx264','-preset','ultrafast','-crf','30','-pix_fmt','yuv420p','-c:a','aac','-shortest','output/demo-short.mp4'], check=True)
print('Vídeo de teste criado: output/demo-short.mp4')
