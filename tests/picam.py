import picamera
import time
import io

cam = picamera.PiCamera( framerate=10)
cam.start_preview(alpha=0)#invisible preview - better for autofokus?
time.sleep(1)
preview_stream = picamera.PiCameraCircularIO(cam, seconds=1)
cam.start_recording(preview_stream, format='mjpeg',resize=(1024,600))
cam.wait_recording(3)
for f in preview_stream.frames:
    print(f)

last_frame=list( preview_stream.frames)[-1] #last frame
data = io.BytesIO()
preview_stream.copy_to(data, first_frame=last_frame )
