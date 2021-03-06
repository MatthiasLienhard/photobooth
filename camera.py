#!/usr/bin/env python
# Created by br@re-web.eu, 2015

import subprocess
import logging
from PIL import Image, ImageDraw
import io
import cv2
import warnings
import time
import os

try:
    import sys

    sony_path = os.path.dirname(os.path.dirname(__file__)) + "/sony_camera_api/src"
    logging.info(sony_path)
    sys.path.insert(0, sony_path)
    # /home/matthias/projects/github/sony_camera_api/src")
    from pysony import SonyAPI, ControlPoint
    import requests

    # import NetworkManager
    # import nmcli
    sony_enabled = True
except ImportError:
    sony_enabled = False
    warnings.warn("pysony not installed. To use sony wifi api camera install pysony module.")

try:
    import gphoto2cffi as gp
    import gphoto2cffi.errors as gpErrors

    gphoto_enabled = True
except ImportError:
    gphoto_enabled = False
    warnings.warn("gphoto module not installed. To use DSLR/digicams install gphoto2cffi module.")

try:
    import picamera
    from picamera.array import PiRGBArray

    picam_enabled = True
except ImportError:
    picam_enabled = False
    warnings.warn("raspberry pi camera module not installed. To use PiCam install picamera module.")


class CameraException(Exception):
    """Custom exception class to handle camera class errors"""

    def __init__(self, message, recoverable=False):
        self.message = message
        self.recoverable = recoverable


class Camera:
    def __init__(self, picture_size, preview_size, focal_length='NA', type="dummicam", name='dummicam'):
        self.picture_size = picture_size
        self.focal_length = focal_length
        self.preview_size = preview_size
        self.type = type
        self.name = name

    def get_test_image(self, size):
        img = Image.new('RGB', size, color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Testimage", fill=(255, 255, 0))
        return (img)

    def get_preview_frame(self, filename=None, filter=None):
        img = self.get_test_image(self.preview_size)
        if filename is not None:
            img.save(filename)
        else:
            return img

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        img = self.get_test_image(self.picture_size)
        if filename is not None:
            img.save(filename)
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
        self.focal_length = focal_length
        return self.focal_length

    def zoom_in(self):
        if self.focal_length is not 'NA':
            self.set_zoom(self.focal_length + 5)

    def zoom_out(self):
        if self.focal_length is not 'NA':
            self.set_zoom(self.focal_length - 5)

    def teardown(self):
        pass


class Camera_sonywifi(Camera):
    def __init__(self, picture_size, preview_size, zoom=30, ssid="DIRECT-LKE0:ILCE-6000", pw="UeyxbxAG",
                 iface="wlp2s0"):
        Camera.__init__(self, picture_size, preview_size, zoom, type='sony_wifi')
        self.live_stream = None
        if not sony_enabled:
            raise CameraException("pysony module not installed")
        self.previous_wifi = \
        subprocess.check_output(["nmcli", "--fields", "NAME", "c", "show", "--active"]).decode("utf-8").split("\n")[
            1].strip()
        self.sony_api_version = "1.0"
        if self.previous_wifi == ssid:
            self.previous_wifi = ""
        else:
            try:
                wifi_list = subprocess.check_output(["nmcli", "--fields", "SSID", "device", "wifi"]).decode(
                    "utf-8").split("\n")
                wifi_list = [wifi_list[i].strip() for i in range(len(wifi_list))]

                if ssid in wifi_list:
                    subprocess.check_call(["nmcli", "con", "up", "id", ssid])
                else:
                    raise CameraException("Sony Wifi not found")

            except subprocess.CalledProcessError:
                raise CameraException("Cannot connect to wifi")
        search = ControlPoint()
        cameras = search.discover()
        self.last_preview_frame = Image.new('RGB', preview_size, (0, 0, 0))

        if len(cameras):
            self.camera = SonyAPI(QX_ADDR=cameras[0])
        else:
            raise CameraException("No camera found")


        options = self.camera.getAvailableApiList()['result'][0]
        logging.info(str(options))

    def zoom_in(self):
        self.camera.actZoom(["in", "1shot"])

    def zoom_out(self):
        self.camera.actZoom(["out", "1shot"])

    def __del__(self):
        self.teardown()

    def teardown(self):
        if sony_enabled:
            if self.live_stream is not None:
                self.stop_preview_stream()
            if self.previous_wifi is not "":
                try:
                    subprocess.check_call(["nmcli", "con", "up", "id", self.previous_wifi])
                except subprocess.CalledProcessError:
                    raise CameraException("Cannot connect to previous wifi " + self.previous_wifi)

    def start_preview_stream(self):
        # For those cameras which need it
        options = self.camera.getAvailableApiList()['result'][0]
        logging.info("starting preview")
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
        logging.info("stopping preview")
        if self.live_stream is not None:
            self.live_stream.stop()
            options = self.camera.getAvailableApiList()['result'][0]
            # if self.preview_active and 'endRecMode' in (options):
            #    self.camera.stopRecMode()
            # if self.live_stream.is_active():
            #    self.camera.stopLiveview() # todo:  is this correct?
        self.preview_active = False

    def get_preview_frame(self, filename=None):
        # read header, confirms image is also ready to read
        header = False
        while not header:
            header = self.live_stream.get_header()

        if header:
            # image_file = io.BytesIO(self.live_stream.get_latest_view())
            # incoming_image = Image.open(image_file)
            # frame_info = self.live_stream.get_frameinfo()
            data = self.live_stream.get_latest_view()
            img = Image.open(io.BytesIO(data))
            # img=img.resize(self.preview_size, Image.ANTIALIAS)
        else:
            img = self.last_preview_frame
        if filename is not None:
            img.save(filename)
        return img

    def take_picture(self, filename="/tmp/picture.jpg"):
        options = self.camera.getAvailableApiList()['result'][0]
        url = self.camera.actTakePicture()
        logging.info(url)
        response = requests.get(url['result'][0][0].replace('\\', ''))
        img = Image.open(io.BytesIO(response.content))
        if filename is not None:
            img.save(filename)
        return img


class Camera_cv(Camera):
    def __init__(self, picture_size, preview_size, zoom=30):
        Camera.__init__(self, picture_size, preview_size, zoom, type='webcam')
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            raise CameraException("No webcam found!")
        fps = 10

        self.cam.set(3, picture_size[0])
        self.cam.set(4, picture_size[1])
        self.cam.set(4, fps)

    def get_preview_frame(self, filename=None, filter=None):
        return (self._take_picture(filename, filter, size=self.preview_size))

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        return (self._take_picture(filename, filter, size=self.picture_size))

    def _take_picture(self, filename, filter, size):
        frame = cv2.resize(self.cam.read()[1], size)
        # frame = self.cam.read()[1]
        if filename is not None and filter is None:
            cv2.imwrite(filename, frame)
            img = Image.fromarray(frame)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            if filter is not None:
                img = filter.apply(img)
        return (img)


class Camera_pi(Camera):
    def __init__(self, picture_size, preview_size, zoom=30):
        Camera.__init__(self, picture_size, preview_size, zoom, type='picam')
        if not picam_enabled:
            raise CameraException("No PiCam module")
        try:
            self.cam = picamera.PiCamera(framerate=5)
            self.cam.rotation = 0
            # self.cam.start_preview(alpha=0) # invisible preview
        except picamera.PiCameraError:
            raise CameraException("Cannot initialize PiCam")
        self.preview_stream = picamera.PiCameraCircularIO(self.cam, seconds=1)  # 17 MB
        self.preview_active = False

    def start_preview_stream(self):
        if not self.preview_active:
            self.cam.start_preview(alpha=0)
            self.cam.start_recording(self.preview_stream, format='mjpeg', resize=self.preview_size)
            self.cam.wait_recording(.5)
            self.preview_active = True
        else:
            self.cam.wait_recording(.5)

    def stop_preview_stream(self):
        if self.preview_active:
            self.cam.stop_preview()
            self.cam.stop_recording()
            self.preview_active = False

    def get_preview_frame(self, filename=None, filter=None):
        if not self.preview_active:
            raise CameraException("preview inactive")
        # logging.info("get preview frame")
        # data = io.BytesIO()
        # self.preview_stream.copy_to(data, first_frame=list(self.preview_stream.frames)[-1] )
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', use_video_port=True)  # , resize=self.preview_size)

        stream.seek(0)
        img = Image.open(stream)
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return (img)
        else:
            img.save(filename)

    def take_picture(self, filename=None, filter=None):
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', resize=self.picture_size)
        stream.seek(0)
        img = Image.open(stream)
        if filter is not None:
            img = filter.apply(img)
        if filename is not None:
            img.save(filename)
        return img


# self.cam.capture(filename)


class Camera_gPhoto(Camera):
    """Camera class providing functionality to take pictures using gPhoto 2"""

    def __init__(self, picture_size, preview_size, zoom=30):
        if not gphoto_enabled:
            raise CameraException("No gphoto module")
        Camera.__init__(self, picture_size, preview_size, zoom, type='dslr')
        # Print the capabilities of the connected camera
        try:
            self.cam = gp.Camera()
        except gpErrors.UnsupportedDevice as e:
            raise CameraException("Can not initialize gphoto camera: " + str(e))

    def start_preview_stream(self):
        self.cam.get_preview()
        # if 'viewfinder' in self.cam._get_config()['actions']:
        #    self.cam._get_config()['actions']['viewfinder'].set(True)
        # else:
        #    self.cam.get_preview()

    def stop_preview_stream(self):
        if 'viewfinder' in self.cam._get_config()['actions']:
            self.cam._get_config()['actions']['viewfinder'].set(False)

    def get_preview_frame(self, filename=None, filter=None):
        data = self.cam.get_preview()
        img = Image.open(io.BytesIO(data))
        if filter is not None:
            img = filter.apply(img)
        if filename is not None:
            img.save(filename)
        return img

        # raise CameraException("No preview supported!")

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        img = self.cam.capture()
        img = Image.open(io.BytesIO(img))
        if filter is not None:
            img = filter.apply(img)
        if filename is not None:
            img.save(filename)
        return img

    def press_half(self):
        if 'eosremoterelease' in self.cam._get_config()['actions']:
            logging.info("press half")
            self.cam._get_config()['actions']['eosremoterelease'].set('Press Half')  #

    def release_full(self):
        if 'eosremoterelease' in self.cam._get_config()['actions']:
            logging.info("release full")
            self.cam._get_config()['actions']['eosremoterelease'].set('Release Full')  #

    def focus(self):
        pass
        # todo define focus function


def get_camera(picture_size, preview_size, priority_list=['sony_wifi', 'webcam', 'dslr', 'picam', 'webcam', 'dummicam'],
               ssid=None, default_cam=None):
    for type in priority_list:
        if default_cam is not None and default_cam.type == type:
            return default_cam
        else:
            cam = _get_camera(picture_size, preview_size, type, ssid)
            if cam is not None:
                logging.info("found " + cam.type)
                return cam
    raise CameraException("specified camera not found...")


def _get_camera(picture_size, preview_size, type, ssid):
    logging.info("try to get camera of type " + type)
    if type == 'sony_wifi':
        try:
            return Camera_sonywifi(picture_size, preview_size, ssid=ssid)
        except CameraException:
            return None
    elif type == 'dslr':
        try:
            return Camera_gPhoto(picture_size, preview_size)
        except CameraException:
            return None
    elif type == 'picam':
        try:
            return Camera_pi(picture_size, preview_size)
        except CameraException:
            return None
    elif type == 'webcam':
        try:
            return Camera_cv(picture_size, preview_size)
        except CameraException:
            return None
    elif type is 'dummicam':
        return Camera(picture_size, preview_size)
    else:
        raise CameraException("Camera type {} not implemented".format(type))
