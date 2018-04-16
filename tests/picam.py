import picamera

cam = picamera.PiCamera( framerate=10)
cam.start_preview(alpha=0)#invisible preview - better for autofokus?
preview_stream = picamera.PiCameraCircularIO(cam, seconds=1)
cam.start_recording(preview_stream, format='mjpeg',resize=(1024,600))
cam.wait_recording(3)
for f in preview_stream.frames:
    print(f)

list( preview_stream.frames)[-1] #last frame