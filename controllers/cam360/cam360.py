# controllers/cam360/cam360.py
#
# Compact 360° recorder for protos/cam360.proto.
# Webots renders the equirectangular image on the GPU ("cylindrical" projection),
# and the raw BGRA frames are piped to ffmpeg, which encodes them with NVENC.

import os
import queue
import subprocess
import threading
from controller import Robot

VIDEO_FPS = 15.0        # target, rounded to a multiple of basicTimeStep
ENCODER = "hevc_nvenc"  # NVIDIA GPU: hevc_nvenc | av1_nvenc (<= 8192 px wide)
#                         no NVIDIA GPU (CPU, slower): libx265 | libx264 (<= 4096 px)
QUALITY_CQ = 23         # lower = better quality / bigger file
MAX_FRAMES = int(os.environ.get("PANO_MAX_FRAMES", 0))  # 0 = unlimited

robot = Robot()
timestep = int(robot.getBasicTimeStep())
steps_per_frame = max(1, round(1000.0 / VIDEO_FPS / timestep))
period = steps_per_frame * timestep

cam = robot.getDevice(f"{robot.getName()}_equirect")
cam.enable(period)
W, H = cam.getWidth(), cam.getHeight()

if "nvenc" in ENCODER:
    quality = ["-preset", "p4", "-rc", "vbr", "-cq", str(QUALITY_CQ), "-b:v", "0"]
else:
    quality = ["-preset", "veryfast", "-crf", str(QUALITY_CQ)]

path = os.path.join(os.path.dirname(__file__), f"{robot.getName()}_{W}x{H}.mp4")
ffmpeg = subprocess.Popen(
    ["ffmpeg", "-loglevel", "error", "-y",
     "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
     "-framerate", f"1000/{period}", "-i", "-",
     "-c:v", ENCODER, *quality, "-pix_fmt", "yuv420p", *(["-tag:v", "hvc1"] if "hevc" in ENCODER or "265" in ENCODER else []), path],
    stdin=subprocess.PIPE)
print(f"[cam360] {W}x{H} @ {1000 / period:.2f} fps -> {path}")

# Encoding thread so Webots can render the next frame while ffmpeg receives this one.
frames = queue.Queue(maxsize=2)


def writer():
    while (frame := frames.get()) is not None:
        ffmpeg.stdin.write(frame)


thread = threading.Thread(target=writer, daemon=True)
thread.start()

step = count = 0
try:
    while robot.step(timestep) != -1:
        step += 1
        if step % steps_per_frame == 0:
            frames.put(cam.getImage())
            count += 1
            if MAX_FRAMES and count >= MAX_FRAMES:
                break
finally:
    frames.put(None)
    thread.join()
    ffmpeg.stdin.close()
    ffmpeg.wait()
    print(f"[cam360] Done: {count} frames -> {path}")
