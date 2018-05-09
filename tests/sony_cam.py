import pysony
import time
import io
from PIL import Image

def main():
    info=True
    photomode=False
    api=pysony.SonyAPI()
    search = pysony.ControlPoint()
    cameras = search.discover(1)
    if len(cameras):
        camera = pysony.SonyAPI(QX_ADDR=cameras[0])
    else:
        print("No camera found, aborting")
        return -1
    mode = camera.getAvailableApiList()
    # For those cameras which need it
    if 'startRecMode' in (mode['result'])[0]:
        camera.startRecMode()
        time.sleep(5)
        # and re-read capabilities
        mode = camera.getAvailableApiList()
    if 'setLiveviewFrameInfo' in (mode['result'])[0]:
         if info:
            camera.setLiveviewFrameInfo([{"frameInfo": True}])
         else:
            camera.setLiveviewFrameInfo([{"frameInfo": False}])
    url = camera.liveview() #liveview(["L"]) -> large
    incoming_image = None
    frame_info = None
    print("set cam mode")
    # Ensure that we're in correct mode (movie by default)
    mode = camera.getAvailableShootMode()
    if type(mode) == dict:
        if (mode['result'])[0] != 'movie':
            if 'movie' in (mode['result'])[1]:
                camera.setShootMode(["movie"]) #other option: "still"
            else:
                photomode = True
    print("starting stream")
    lst = api.LiveviewStreamThread(url)
    lst.start()
    for i in range(100):
        print("frame {}".format(i))
        header = lst.get_header()
        if header:
            image_file = io.BytesIO(lst.get_latest_view())
            incoming_image = Image.open(image_file)
            incoming_image.sav("test.jpg")
            frame_info = lst.get_frameinfo()
            print(frame_info)
            time.sleep(.1)
    print("stop")
    api.stopLiveview('1.0')

main()
# python3 ~/projects/downloads/sony_camera_api/src/example/dump_camera_capabilities.py