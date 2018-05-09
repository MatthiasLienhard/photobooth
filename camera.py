#!/usr/bin/env python
# Created by br@re-web.eu, 2015

import subprocess

from PIL import Image, ImageDraw
import io
import cv2
import warnings
import time
try:
    from pysony import SonyAPI, ControlPoint
    import requests
except ImportError:
    sony_enabled=False
    warnings.warn("pysony not installed. To use sony wifi api camera install pysony module.")

try:
    import gphoto2cffi as gp
    import gphoto2cffi.errors as gpErrors
    gphoto_enabled = True
except ImportError:
    gphoto_enabled=False
    warnings.warn("gphoto module not installed. To use DSLR/digicams install gphoto2cffi module.")


try:
    import picamera
    from picamera.array import PiRGBArray
    picam_enabled=True
except ImportError:
    picam_enabled=False
    warnings.warn("raspberry pi camera module not installed. To use PiCam install picamera module.")

class CameraException(Exception):
    """Custom exception class to handle camera class errors"""
    def __init__(self, message, recoverable=False):
        self.message = message
        self.recoverable = recoverable

class Camera:
    def __init__(self, picture_size,preview_size, focal_length=30, type="dummicam",name='dummicam' ):
        self.picture_size = picture_size
        self.focal_length = focal_length
        self.preview_size=preview_size
        self.type=type
        self.name=name

    def get_test_image(self, size):
        img = Image.new('RGB', size, color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Testimage", fill=(255, 255, 0))
        return(img)

    def get_preview_frame(self, filename=None, filter = None):
        img=self.get_test_image(self.preview_size)
        if filename is not None:
            img.save(filename)
        else:
            return img
    def take_picture(self, filename="/tmp/picture.jpg", filter = None):
        img=self.get_test_image(self.picture_size)
        if filename is not None:
            img.save(filename)
        else:
            return img

    def set_idle(self):
        pass
    def start_preview_stream(self):
        pass
    def stop_preview_stream(self):
        pass
    def focus(self):
        pass
    def get_zoom(self):
        return self.focal_length

    def set_zoom(self, focal_length):
        self.focal_length=focal_length
        return self.focal_length


class Camera_sonywifi(Camera):
    def __init__(self, picture_size, preview_size, zoom=30, ssid="DIRECT-LKE0:ILCE-6000", pw="UeyxbxAG", iface="wlp2s0"):
        Camera.__init__(self, picture_size, preview_size, zoom, type='sony_wifi')
        self.previous_wifi="yesman 1" #todo: get the current wifi NAME! not ssid eg with nmcli con show --active or iwgetid -r
        self.sony_api_version="1.0"
        try:
            subprocess.check_call(["nmcli",  "con",  "up", "id", ssid])
        except subprocess.CalledProcessError:
            raise CameraException("Cannot connect to wifi")
        search = ControlPoint()
        cameras = search.discover()

        if len(cameras):
            self.camera = SonyAPI(QX_ADDR=cameras[0])
        else:
            raise CameraException("No camera found")
        options = self.camera.getAvailableApiList()['result'][0]
        print(str(options))

    def __del__(self):
        try:
            subprocess.check_call(["nmcli", "con", "up", "id", self.previous_wifi])
        except subprocess.CalledProcessError:
            raise CameraException("Cannot connect to previous wifi " + self.previous_wifi)

    def start_preview_stream(self):
        # For those cameras which need it
        options = self.camera.getAvailableApiList()['result'][0]

        if 'startRecMode' in options:
            self.camera.startRecMode()
            time.sleep(1)
            options = self.camera.getAvailableApiList()['result'][0]
            print(str(options))
        self.camera.setLiveviewFrameInfo([{"frameInfo": False}])
        url = self.camera.liveview()
        assert isinstance(url, str)
        print(url)
        self.live_stream = SonyAPI.LiveviewStreamThread(url)
        self.live_stream.start()
        self.preview_active = True

    def stop_preview_stream(self):
        options = self.camera.getAvailableApiList()['result'][0]
        #if self.preview_active and 'endRecMode' in (options):
        #     self.camera.stopRecMode()
        #if self.live_stream.is_alive():
        #    self.camera.stopLiveview() # todo:  is this correct?
        self.preview_active = False


    def get_preview_frame(self, filename=None, filter=None):
        data = self.live_stream.get_latest_view()
        img = Image.open(io.BytesIO(data))
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return (img)
        else:
            img.save(filename)

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        options = self.camera.getAvailableApiList()['result'][0]
        url = self.camera.actTakePicture()
        print(url)
        response = requests.get(url['result'][0][0].replace('\\', ''))
        img=Image.open(io.BytesIO(response.content))
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return (img)
        else:
            img.save(filename)

class Camera_cv(Camera):
    def __init__(self, picture_size, preview_size, zoom=30):
        Camera.__init__(self,picture_size, preview_size, zoom, type='webcam')
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            raise CameraException("No webcam found!")
        fps=10

        self.cam.set(3, picture_size[0])
        self.cam.set(4, picture_size[1])
        self.cam.set(4, fps)

    def get_preview_frame(self, filename=None, filter=None):
        return(self._take_picture(filename, filter, size=self.preview_size))

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        return (self._take_picture(filename, filter, size=self.picture_size))

    def _take_picture(self, filename, filter, size):
        frame = cv2.resize( self.cam.read()[1], size)
        if filename is not None and filter is None:
            cv2.imwrite(filename, frame)
        else:
            frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            if filter is not None:
                img=filter.apply(img)
            return(img)

class Camera_pi(Camera):
    def __init__(self, picture_size,preview_size, zoom =30):
        Camera.__init__(self,picture_size, preview_size, zoom, type='picam')
        if not picam_enabled:
            raise CameraException("No PiCam module")
        try:
            self.cam = picamera.PiCamera(framerate=5)
            self.cam.rotation = 0
            #self.cam.start_preview(alpha=0) # invisible preview
        except picamera.PiCameraError:
            raise CameraException("Cannot initialize PiCam")
        self.preview_stream= picamera.PiCameraCircularIO(self.cam, seconds=1) # 17 MB
        self.preview_active=False

    def start_preview_stream(self):
        if not self.preview_active :
            self.cam.start_preview(alpha=0)
            self.cam.start_recording(self.preview_stream, format='mjpeg',resize=self.preview_size)
            self.cam.wait_recording(.5)
            self.preview_active = True
        else:
            self.cam.wait_recording(.5)

    def stop_preview_stream(self):
        if self.preview_active:
            self.cam.stop_preview()
            self.cam.stop_recording()
            self.preview_active=False


    def get_preview_frame(self, filename=None, filter=None):
        if not self.preview_active:
            raise CameraException("preview inactive")
        #print("get preview frame")
        #data = io.BytesIO()
        #self.preview_stream.copy_to(data, first_frame=list(self.preview_stream.frames)[-1] )
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', use_video_port=True)#, resize=self.preview_size)

        stream.seek(0)
        img = Image.open(stream)
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)

    def take_picture(self, filename=None, filter=None):
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', resize=self.picture_size)
        stream.seek(0)
        img=Image.open(stream)
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)
        # self.cam.capture(filename)



class Camera_gPhoto(Camera):
    """Camera class providing functionality to take pictures using gPhoto 2"""

    def __init__(self, picture_size, preview_size, zoom=30):
        Camera.__init__(self,picture_size, preview_size, zoom, type='dslr')
        # Print the capabilities of the connected camera
        try:
            self.cam = gp.Camera()
        except gpErrors.UnsupportedDevice as e:
            raise CameraException("Can not initialize gphoto camera: "+str(e))

    def start_preview_stream(self):
        self.cam.get_preview()
        #if 'viewfinder' in self.cam._get_config()['actions']:
        #    self.cam._get_config()['actions']['viewfinder'].set(True)
        #else:
        #    self.cam.get_preview()

    def stop_preview_stream(self):
        if 'viewfinder' in self.cam._get_config()['actions']:
            self.cam._get_config()['actions']['viewfinder'].set(False)


    def get_preview_frame(self, filename=None, filter=None):
        data=self.cam.get_preview()
        img = Image.open(io.BytesIO(data))
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)

        # raise CameraException("No preview supported!")

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        img=self.cam.capture()
        img=Image.open(io.BytesIO(img))
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)



    def press_half(self):
        if 'eosremoterelease' in self.cam._get_config()['actions']:
            print("press half")
            self.cam._get_config()['actions']['eosremoterelease'].set('Press Half')#

    def release_full(self):
        if 'eosremoterelease' in self.cam._get_config()['actions']:
            print("release full")
            self.cam._get_config()['actions']['eosremoterelease'].set('Release Full')#

    def focus(self):
        pass
        # todo define focus function

def get_camera(picture_size, preview_size,priority_list=['sony_wifi', 'dslr', 'picam', 'webcam', 'dummicam'], default_cam=None):

    for type in priority_list:
        if default_cam is not None and default_cam.type is type:
            return default_cam
        else:
            cam=_get_camera(picture_size, preview_size, type)
            if cam is not None:
                return cam

def _get_camera(picture_size, preview_size, type):
    if type=='sony_wifi':
        try:
            return Camera_sonywifi(picture_size, preview_size)
        except CameraException:
            return None
    elif type=='dslr':
        try:
            return Camera_gPhoto(picture_size, preview_size)
        except CameraException:
            return None
    elif type=='picam':
        try:
            return Camera_pi(picture_size, preview_size)
        except CameraException:
            return None
    elif type=='webcam':
        try:
            return Camera_cv(picture_size, preview_size)
        except CameraException as e:
            return None
    elif type is 'dummicam':
        return Camera(picture_size, preview_size)
    else:
        raise CameraException("Camera type {} not implemented".format(type))