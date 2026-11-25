"""Records a dev/drive.tscn script to an H.264 MP4 on the hidden desktop, and deletes the AVI.

    toolchain\\blender\\4.5\\python\\bin\\python.exe -I tools\\clip.py out.mp4 [godot arguments] [-- drive arguments]

Godot gets --path, res://dev/drive.tscn, --fixed-fps 60 and --write-movie for you; add --resolution
WxH and drive's key=value arguments (scene=, do=, side=) as usual. Godot's movie writer makes an
AVI; Blender's built-in FFmpeg, run in the background on this same file, encodes it.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLENDER = 'toolchain/blender/blender.exe'
QUIET = ROOT / 'dev' / 'quiet.py'


def encode(avi: str, mp4: str) -> None:
    import bpy
    scene = bpy.context.scene
    strip = scene.sequence_editor_create().strips.new_movie('clip', avi, 1, 1)
    scene.render.resolution_x, scene.render.resolution_y = strip.elements[0].orig_width, strip.elements[0].orig_height
    scene.render.resolution_percentage = 100
    scene.render.fps, scene.render.fps_base = round(strip.fps), 1.0
    scene.frame_start, scene.frame_end = 1, strip.frame_final_duration
    scene.view_settings.view_transform = 'Standard'  # Godot's colours as they are: the factory AgX greys them
    scene.render.image_settings.file_format = 'FFMPEG'
    ffmpeg = scene.render.ffmpeg
    ffmpeg.format, ffmpeg.codec = 'MPEG4', 'H264'
    ffmpeg.constant_rate_factor, ffmpeg.ffmpeg_preset = 'HIGH', 'GOOD'
    ffmpeg.gopsize = 30
    scene.render.filepath = mp4
    bpy.ops.render.render(animation=True)


def find_blender() -> Path:
    for folder in [ROOT, *ROOT.parents]:
        if (folder / BLENDER).exists():
            return folder / BLENDER
    sys.exit('clip: Blender not found in any parent folder')


def main() -> int:
    mp4 = Path(sys.argv[1]).resolve()
    godot_args = sys.argv[2:]
    avi = mp4.with_suffix('.avi')
    mp4.parent.mkdir(parents=True, exist_ok=True)
    avi.unlink(missing_ok=True)
    head = ['--path', str(ROOT), 'res://dev/drive.tscn', '--fixed-fps', '60', '--write-movie', str(avi)]
    recorded = subprocess.run([sys.executable, '-I', str(QUIET)] + head + godot_args)
    if recorded.returncode or not avi.exists():
        sys.exit(f'clip: Godot failed ({recorded.returncode})')
    try:
        encoded = subprocess.run([str(find_blender()), '--background', '--factory-startup', '--python', __file__, '--', str(avi), str(mp4)])
    finally:
        avi.unlink(missing_ok=True)
    return encoded.returncode


if __name__ == '__main__':
    try:
        import bpy
        encode(*sys.argv[sys.argv.index('--') + 1:])
    except ImportError:
        sys.exit(main())
