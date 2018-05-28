#!/usr/bin/env python3


import math
import os
from datetime import datetime
from glob import glob
from sys import exit
from time import sleep, time
from PIL import Image
# from camera import CameraException, Camera_cv as CameraModule
# from camera import CameraException, Camera_gPhoto as CameraModule
import camera
from theme import Theme
from events import GPIO_LAMP
from layouts import Layout, N_LAYOUTOPT
from filter import *
from events import Rpi_GPIO as GPIO
from gui import GUI_PyGame as GuiModule
# import numpy as np
import random
import sys
import subprocess
# import scipy.ndimage
try:
    import cups
    _has_cups=True
except ImportError:
    _has_cups=False
    print("for printer support, install pycups")

class PhotoboothException(Exception):
    """Custom exception class to handle camera class errors"""
    def __init__(self, message):
        self.message = message

###############
### Classes ###
###############
def open_images(filenames:[str]):
    imgs=[]
    for fn in filenames:
        imgs.append(Image.open(fn))
    return(imgs)

class PictureList:
    """A simple helper class.

    It provides the filenames for the assembled pictures and keeps count
    of taken and previously existing pictures.
    """

    def __init__(self, basename):
        """Initialize filenames to the given basename and search for
        existing files. Set the counter accordingly.
        """

        # Set basename and suffix
        self.suffix = ".jpg"
        self.count_width = 5

        # Ensure directory exists
        self.dirname, self.basename = os.path.split(basename)
        if not os.path.exists(self.dirname):
            os.makedirs(self.dirname)
        if not os.path.exists(self.dirname+"/raw"):
            os.makedirs(self.dirname+"/raw")

        # Find existing files
        count_pattern = "[0-9]" * self.count_width
        pictures = glob(self.dirname+"/"+self.basename + count_pattern + self.suffix)



        # Get number of latest file
        if len(pictures) == 0:
            self.counter = 0
        else:
            pictures.sort()
            last_picture = pictures[-1]
            self.counter = int(last_picture[-(self.count_width+len(self.suffix)):-len(self.suffix)])

        # Print initial infos
        print("Info: Number of last existing file: " + str(self.counter))
        print("Info: Saving assembled pictures as: " + self.dirname +"/" + self.basename + "XXXXX.jpg")

    def get(self, count):
        return self.dirname+"/" + self.basename + str(count).zfill(self.count_width) + self.suffix

    def get_raw(self, count,n):
        stem=self.dirname+"/raw/"+self.basename + str(count).zfill(self.count_width)
        return [stem+'_'+str(i) + self.suffix for i in range(n)]

    def get_last(self):
        return self.get(self.counter)

    def get_next(self):
        self.counter += 1
        return self.get(self.counter)

    def get_info(self):
        info=("Pictures:\nNumber of existing files: " + str(self.counter))
        info+=("\nSaving assembled pictures as: " + self.dirname +"/" + self.basename + "XXXXX.jpg")
        return(info)
    def delete_pic(self):
        self.counter -=1



class Photobooth:
    """The main class.

    It contains all the logic for the photobooth.
    """

    def __init__(self, display_size, picture_basename, picture_size, preview_size,  pose_time, display_time,
                 slideshow_display_time, printer_name=None, theme="default"):
        self.start_info_timer=5
        self.screensaver_timer=30
        self.slideshow_timer=slideshow_display_time
        self.display=None
        self.display_size=display_size
        #self.init_display()
        if _has_cups:
            self.cups_conn=cups.Connection()
            printers=self.cups_conn.getPrinters()
            if printer_name is not None and printer_name in printers.keys():
                self.printer=printer_name
                print("found specified printer "+printer_name)
            else:
                self.printer=None
        else:
            self.printer=None

        self.pictures     = PictureList(picture_basename)
        self.picture_dir  = os.path.realpath(self.pictures.dirname)
        self.picture_size = picture_size
        self.pose_time    = pose_time
        self.display_time = display_time
        self.theme        = Theme(theme)
        self.filter_opt   = 0
        self.layout_opt   = 1
        self.set_layout()
        self.errors=[]
        self.current_page=None
        self.camera = camera.get_camera(picture_size, preview_size)
        # self.preview_camera=camera.get_camera(picture_size, preview_size,['picam', 'webcam', 'dslr','dummicam'], self.camera)
        self.preview_camera=camera.get_camera(picture_size, preview_size,default_cam=self.camera)
    def set_layout(self):
        self.layout = Layout(self.layout_opt, size=self.picture_size, filter_type=self.filter_opt)

    def toggle_layout(self):
        self.layout_opt+=1
        if self.layout_opt >= N_LAYOUTOPT:
            self.layout_opt=0
        self.set_layout()

    def toggle_filter(self):
        self.filter_opt+=1
        if self.filter_opt>= N_FILTEROPT:
            self.filter_opt=0
        self.set_layout()

    def run(self, fullscreen=True):
        self.display = GuiModule('Photobooth', self.display_size, fullscreen=fullscreen)
        self.current_page = StartPage(self)
        # Enable lamp
        self.display.gpio.set_output(GPIO_LAMP, 1)

        while True:
            print ("ready for next action!")
            try:
                self.current_page.next_action()
               # Catch exceptions and display message
            #except camera.CameraException as e:
            #    self.errors.append(e)
            #    self.current_page.next_action=self.show_error
            # Do not catch KeyboardInterrupt and SystemExit
            except (KeyboardInterrupt, SystemExit):
                raise
            #except Exception as e:
            #    msg='SERIOUS ERROR: ' + repr(e)
            #    print(msg)
            #    self.errors.append(PhotoboothException(msg))
            #    self.current_page.next_action = self.show_error

            #    self.teardown()

    def teardown(self):
        self.display.clear()
        self.display.show_message("Shutting down...")
        self.display.apply()
        self.display.gpio.set_output(GPIO_LAMP, 0)
        self.camera.teardown()
        sleep(0.5)
        self.display.teardown()
        self.display.gpio.teardown()
        exit(0)

    def show_slideshow(self):
        self.current_page=SlideshowPage(self)
    def show_main(self):
        self.current_page=MainPage(self)
    def show_shooting(self):
        self.current_page=ShootingPage(self)
    def show_result(self):
        self.current_page=ResultPage(self)
    def show_error(self):
        self.current_page = ErrorPage(self)
    def camera_info(self):
        info=self.camera.type
        if self.preview_camera != self.camera:
            info += " and "+ self.preview_camera.type
        return info



    def get_info_text(self):
        # todo: make infotext
        return("Camera: "+self.camera_info()+"\n\n"+self.pictures.get_info()+"\n\nprinter: "+self.printer)

#####################
### Display Pages ###
#####################

class DisplayPage:
    def __init__(self, name, pb:Photobooth, options=None, timer=5, bg=None, overlay_text = None):
        if options is None:
            options = []
        self.name=name
        self.pb=pb
        if len(options)==0 :
            options=[self.pb.teardown]
        self.options=options # 0:timer 1:middle 2:left 3: right, 4: long middle 5: long left 6: long right
        self.timer=timer
        self.overlay_text=overlay_text
        self.bg=bg
        self.next_action=self.pb.teardown # this is executed when __init__ finished (called in photobooth.run)
        self.overlay_text_size=144

    def apply(self):
        self.pb.display.clear()
        if self.bg is not None:
            self.pb.display.show_picture(self.bg, size=self.pb.display.get_size(), adj=(0,0))
        if self.overlay_text is not None:
            self.pb.display.show_message(self.overlay_text, size=self.overlay_text_size)
        self.pb.display.apply()

    def start(self):
        self.apply()
        self.wait_for_event()

    def wait_for_event(self):
        e = self.pb.display.wait_for_event(self.timer)
        while not self.handle_event(e):
            e = self.pb.display.wait_for_event(self.timer)
        print("leaving loop" )

    def handle_event(self,event):
        action = event.get_action()
        print(self.name + " handles "+str(event) +"--> action "+str(action))
        if action is not None and len(self.options) > action:
            if self.options[action] is not None:
                self.next_action=self.options[action]
                return True
        if event.get_type() is 'quit':
            self.pb.teardown()
        return False



class StartPage(DisplayPage):
    def __init__(self, pb):
        options=[pb.show_slideshow, pb.show_slideshow ]
        DisplayPage.__init__(self, "Start", pb,options,pb.start_info_timer)
        self.overlay_text=pb.get_info_text()
        self.overlay_text_size = 60
        self.start()

class ErrorPage(DisplayPage):
    def __init__(self, pb:Photobooth):
        DisplayPage.__init__(self, "Start", pb)

        self.overlay_text = pb.errors[-1].message
        self.timer=2
        self.options=[self.pb.teardown()]
        self.start()

class SlideshowPage(DisplayPage):
    def __init__(self, pb, photo_idx=None,overlay="<Press the Button>"):
        DisplayPage.__init__(self, "Slideshow", pb)

        self.timer=pb.slideshow_timer
        self.options=[ self.jump_image_random,pb.show_main, self.jump_image_rev, self.jump_image_fwd,
             pb.show_result,  self.jump_image_frev, self.jump_image_ffwd]
        self.image_list=pb.pictures #list of filenames
        self.n_img=self.image_list.counter
        if photo_idx is None:
            photo_idx=self.n_img

        self.photo_idx=photo_idx
        self.bigjump=10
        self.overlay_text=overlay
        if photo_idx > 0 and photo_idx <= self.n_img:
            self.bg = self.image_list.get(self.photo_idx)
            self.next_action=self.jump_image_fwd
        else:
            print("No Photos - skipping slideshow")
            self.next_action=pb.show_main
        self.start()

    def apply(self):
        self.pb.display.clear()
        self.pb.display.add_button(action_value=1, pos=(0,0),size=self.pb.display.size)
        if self.bg is not None:
            self.pb.display.show_picture(self.bg, size=self.pb.display.get_size(), adj=(0,0))
        if self.overlay_text is not None:
            self.pb.display.show_message(self.overlay_text, size=self.overlay_text_size)
        self.pb.display.apply()

    def jump_image_random(self):
        if (self.n_img > 1):
            old_idx=self.photo_idx
            while self.photo_idx is old_idx:
                self.photo_idx=random.randrange(1,self.n_img+1)
            self.bg = self.image_list.get(self.photo_idx)
            self.apply()

        self.wait_for_event()

    def jump_image_frev(self):
        self.jump_image(-self.bigjump)
    def jump_image_rev(self):
        self.jump_image(-1)
    def jump_image_fwd(self):
        self.jump_image(1)
    def jump_image_ffwd(self):
        self.jump_image(self.bigjump)
    def jump_image(self, jump):
        if self.photo_idx==1 and jump < 0:
            self.photo_idx=self.n_img
        elif self.photo_idx + jump < 0:
            self.photo_idx=1
        elif self.photo_idx==self.n_img and jump > 0:
            self.photo_idx=1
        elif self.photo_idx + jump > self.n_img:
            self.photo_idx=self.n_img
        else:
            self.photo_idx += jump
        self.bg = self.image_list.get(self.photo_idx)

        self.apply()
        self.wait_for_event()

class MainPage(DisplayPage):
    def __init__(self, pb: Photobooth):
        DisplayPage.__init__(self, "Main", pb)
        self.timer=pb.screensaver_timer
        self.options=[pb.show_slideshow,pb.show_shooting, pb.toggle_filter, pb.toggle_layout,
             pb.teardown] #todo: add camera opt
        self.overlay_text="Main Menue"
        self.example_img_raw = open_images([self.pb.theme.get_file_name("test_picture", ".jpg")])
        self.set_example_img()
        self.start()

    def apply(self):
        self.pb.display.clear()
        self.pb.display.show_picture(self.pb.theme.get_file_name("mainpage"), scale=True)
        #self.pb.display.show_picture(self.pb.theme.get_file_name("title"), adj=(2,0), scale=True)

        self.pb.display.show_picture(self.example_img, adj=(1, 0), scale=False)

        self.pb.display.add_button(action_value=2, adj=(0, 2), img_fn=self.pb.theme.get_file_name("filter_options"))
        self.pb.display.add_button(action_value=3, adj=(2, 2), img_fn=self.pb.theme.get_file_name("layout_options"))
        self.pb.display.add_button(action_value=1, adj=(1, 2), img_fn=self.pb.theme.get_file_name("button"))
        self.pb.display.add_button(action_value=4, adj=(1, 0), img_fn=self.pb.theme.get_file_name("exit"))
        self.pb.display.apply()

    def set_example_img(self):
        self.example_img = self.pb.layout.assemble_pictures(self.example_img_raw * self.pb.layout.n_picture, (600,400))
        self.example_img=self.example_img.rotate(10,expand=True)
    def handle_event(self,event):
        action = event.get_action()
        if action in (2,3):
            self.options[action]()
            self.set_example_img()
            self.apply()
            return False
        else:
            return DisplayPage.handle_event(self,event)


class ShootingPage(DisplayPage):
    def __init__(self, pb:Photobooth):
        DisplayPage.__init__(self, "Shooting", pb, timer=2)
        #pb.cam.start_preview()
        #self.bg=pb.get_preview_frame()
        self.posing_timer=pb.pose_time
        self.options=[self.take_pictures]
        self.next=pb.show_result
        self.n_pictures=pb.layout.n_picture
        self.overlay_text ="Taking {} photos!".format(self.n_pictures)
        self.cam=pb.camera
        self.prev_cam = pb.preview_camera
        #self.bg=self.cam.get_preview_frame()
        pic_list=pb.pictures
        self.result_filename=pic_list.get_next()
        self.raw_filenames=pic_list.get_raw(pic_list.counter, self.n_pictures)
        self.layout=pb.layout
        self.apply()

        self.wait_for_event()

    def take_pictures(self):
        self.next_action=self.next
        self.pb.display.clear()
        for i in range(self.n_pictures):
            self.prev_cam.start_preview_stream()
            print("taking picture {}/{}".format(i+1, self.n_pictures))
            t0=time()
            countdown=self.posing_timer
            while countdown > 0:
                countdown = self.posing_timer - time() + t0
                self.overlay_text=str(math.ceil(countdown))
                self.pb.display.show_picture(self.layout.apply_filters(self.prev_cam.get_preview_frame(), i), flip=True, scale=True)
                self.pb.display.show_message(self.overlay_text)
                self.pb.display.apply()
                r , event = self.pb.display.check_for_event()
                if r:
                    self.handle_event(event) #no events defined but anyway
            self.prev_cam.stop_preview_stream()
            self.pb.display.clear()
            self.pb.display.show_message("smile ;-)")
            self.pb.display.apply()
            img=self.cam.take_picture(self.raw_filenames[i])
            self.pb.display.show_picture(self.layout.apply_filters(img,i), flip=True, scale=True)
            self.pb.display.apply()
            sleep(0.5)
            self.pb.display.clear()
        self.bg=None
        self.overlay_text="processing..."
        self.apply()
        self.cam.stop_preview_stream() # todo: test does this crash 650D here??
        raw_imgs=open_images(self.raw_filenames)
        result_img=self.layout.assemble_pictures(raw_imgs)
        result_img.save(self.result_filename)


class ResultPage(DisplayPage):
    def __init__(self, pb: Photobooth, photo_idx=None):
        timer= pb.screensaver_timer
        opt=[ pb.show_main,pb.show_main, self.delete_pic, self.print_pic ]
        if photo_idx is None:
            self.file_name=pb.pictures.get_last()
        else:
            self.file_name=pb.pictures.get(photo_idx)
        img=self.file_name
        self.printer_ready=False
        if pb.printer is not None:
            attr=pb.cups_conn.getPrinterAttributes(pb.printer)
            # todo: more states that should disable printing?
            if attr['printer-state-message'] != 'Unplugged or turned off':
                self.printer_ready=True
                # print(attr['printer-state-message'])

        DisplayPage.__init__(self, "Results", pb, options=opt, timer=timer, bg=img)
        self.start()

    def apply(self):
        self.pb.display.clear()
        if self.bg is not None:
            self.pb.display.show_picture(self.bg, size=self.pb.display.get_size(), adj=(0,0))
        if self.overlay_text is not None:
            self.pb.display.show_message(self.overlay_text, size=self.overlay_text_size)
        if self.printer_ready:
            self.pb.display.add_button(action_value=3, adj=(2, 2), img_fn=self.pb.theme.get_file_name("printer"))
        self.pb.display.add_button(action_value=2, adj=(0, 2), img_fn=self.pb.theme.get_file_name("trashbin"))
        self.pb.display.add_button(action_value=1, adj=(1, 2), img_fn=self.pb.theme.get_file_name("button_next"))
        self.pb.display.apply()

    def delete_pic(self):
        print("delete")
        self.pb.pictures.delete_pic()

        self.pb.display.show_message("delete picture")
        self.pb.display.apply()
        sleep(2)
        self.next_action = self.pb.show_main()
    def print_pic(self):
        #lpr filename.jpg -P Canon_SELPHY_CP1300
        #try:
        #    subprocess.check_call(["lpr",  self.bg,  "-P", self.pb.printer])
        #except subprocess.CalledProcessError as e:
        #    print(e)
        try:
            self.pb.cups_conn.printFile(self.pb.printer_name, self.bg, " ", {})
        except:
            raise #todo: what can go wrong here?

        self.pb.display.show_message("start printing...")
        self.pb.display.apply()
        sleep(2)
        self.next_action = self.pb.show_main()


#################
### Functions ###
#################

def main(fullscreen):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    display_size = (1024, 600)
    image_size = (2352, 1568)
    preview_size = (900,600)

    # Image basename
    picture_basename = datetime.now().strftime("%Y-%m-%d/photobooth_%Y-%m-%d_")

    # Waiting time in seconds for posing
    pose_time = 5

    # Display time for assembled picture
    display_time = 10

    # Display time of pictures in the slideshow
    slideshow_display_time = 5
    printer='Canon-SELPHY-CP1300'

    photobooth = Photobooth(display_size, picture_basename, image_size, preview_size, pose_time, display_time,
                             slideshow_display_time, printer_name=printer)
    photobooth.run(fullscreen=fullscreen)
    return 0

if __name__ == "__main__":
    exit(main("--fullscreen" in sys.argv))
