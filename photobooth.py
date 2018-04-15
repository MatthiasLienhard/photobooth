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
from layouts import Layout
from filter import *
from events import Rpi_GPIO as GPIO
from gui import GUI_PyGame as GuiModule
import gui
import numpy as np
import random
import scipy.ndimage
#####################
### Configuration ###
#####################

###############
### Classes ###
###############

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


class Photobooth:
    """The main class.

    It contains all the logic for the photobooth.
    """

    def __init__(self, display_size, picture_basename, picture_size, preview_size,  pose_time, display_time, slideshow_display_time, theme="default"):
        self.start_info_timer=5
        self.screensaver_timer=5
        self.slideshow_timer=slideshow_display_time
        self.display=None
        self.display_size=display_size
        #self.init_display()

        self.pictures     = PictureList(picture_basename)
        self.picture_dir  = os.path.realpath(self.pictures.dirname)
        self.picture_size = picture_size
        self.pose_time    = pose_time
        self.display_time = display_time
        self.theme        = Theme(theme)
        self.layout       = Layout(1, self.picture_size)
        self.filter       = HighContrastMonochrome()

        self.current_page=None
        try:
            self.camera = camera.Camera_gPhoto(picture_size, preview_size)
        except camera.CameraException as e:
            print(e)
            try:
                self.camera = camera.Camera_pi(picture_size, preview_size)
            except camera.CameraException as e:
                print(e)
                try:
                    self.camera = camera.Camera_cv(picture_size, preview_size)
                except camera.CameraException as e:
                    print(e)
                    self.camera = camera.Camera(picture_size, preview_size)

    def run(self, fullscreen=True):
        self.display = GuiModule('Photobooth', self.display_size, fullscreen=fullscreen)
        self.current_page = StartPage(self)
        # Enable lamp
        self.display.gpio.set_output(GPIO_LAMP, 1)

        while True:
            try:
                self.current_page.next_action()
               # Catch exceptions and display message
            except camera.CameraException as e:
                self.current_page=ErrorPage(self,e.message)
            # Do not catch KeyboardInterrupt and SystemExit
            except (KeyboardInterrupt, SystemExit):
                raise
            #except Exception as e:
            #    print('SERIOUS ERROR: ' + repr(e))
            #    self.current_page = ErrorPage(self,'SERIOUS ERROR: \n' + repr(e))
            #    self.teardown()

    def teardown(self):
        self.display.clear()
        self.display.show_message("Shutting down...")
        self.display.apply()
        self.display.gpio.set_output(GPIO_LAMP, 0)
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
    def show_pictopt(self):
        self.current_page=PictOptPage(self)
    def show_layoutopt(self):
        self.current_page=LayoutOptPage(self)
    def show_result(self):
        self.current_page=ResultPage(self)
    def get_info_text(self):
        # todo: make infotext
        return(self.pictures.get_info())

#####################
### Display Pages ###
#####################

class DisplayPage:
    def __init__(self,name, display, options=[], timer=5, bg=None, overlay_text = None ):
        self.name=name
        self.display=display
        if len(options)==0 :
            options=[self.teardown]
        self.options=options # 0:timer 1:middle 2:left 3: right, 4: long middle 5: long left 6: long right
        self.timer=timer
        self.overlay_text=overlay_text
        self.bg=bg
        self.next_action=self.teardown # this is executed when __init__ finished (called in photobooth.run)
        self.overlay_text_size=144

    def apply(self):
        self.display.clear()
        if self.bg is not None:
            self.display.show_picture(self.bg, self.display.get_size())
        if self.overlay_text is not None:
            self.display.show_message(self.overlay_text, size=self.overlay_text_size)
        self.display.apply()

    def start(self):
        self.apply()
        self.wait_for_event()

    def wait_for_event(self):
        while True:
            e = self.display.wait_for_event(self.timer)
            if self.handle_event(e):
                break

    def handle_event(self,event):
        action = event.get_action()
        print(self.name + " handles "+str(event) +"--> action "+str(action))
        if action is not None and len(self.options) > action:
            if self.options[action] is not None:
                self.next_action=self.options[action]
                return True
        if event.get_type() is 'quit':
            self.teardown()
        return False


    def teardown(self):
        self.display.clear()
        self.display.show_message("Shutting down...")
        self.display.apply()
        self.display.gpio.set_output(GPIO_LAMP, 0)
        sleep(0.5)
        self.display.teardown()

        exit(0)

class StartPage(DisplayPage):
    def __init__(self, pb):
        options=[pb.show_slideshow, pb.show_slideshow ]
        DisplayPage.__init__(self, "Start", pb.display,options,pb.start_info_timer)
        self.overlay_text=pb.get_info_text()
        self.overlay_text_size = 60
        self.start()

class ErrorPage(DisplayPage):
    def __init__(self, pb, msg):
        DisplayPage.__init__(self, "Start", pb.display)

        self.overlay_text=msg
        self.timer=2
        self.options=[self.teardown()]
        self.start()

class SlideshowPage(DisplayPage):
    def __init__(self, pb, photo_idx=None,overlay="<Press the Button>"):
        DisplayPage.__init__(self, "Slideshow", pb.display)

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

    def jump_image_random(self):
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
        DisplayPage.__init__(self, "Main", pb.display)
        self.timer=pb.screensaver_timer
        self.options=[pb.show_slideshow,pb.show_shooting, pb.show_pictopt, pb.show_layoutopt,
             pb.teardown] #todo: add advanced opt
        self.theme=pb.theme
        self.bg=self.get_bg()
        self.overlay_text="Main Menue"
        self.start()

    def get_bg(self):
        fn=self.theme.get_file_name("mainpage")
        #todo load background and scale to resolution
        return(fn )


class ShootingPage(DisplayPage):
    def __init__(self, pb:Photobooth):
        DisplayPage.__init__(self, "Shooting", pb.display, timer=2)
        #pb.cam.start_preview()
        #self.bg=pb.get_preview_frame()
        self.posing_timer=pb.pose_time
        self.options=[self.take_pictures]
        self.next=pb.show_result
        self.n_pictures=pb.layout.n_picture
        self.overlay_text ="Taking {} photos!".format(self.n_pictures)
        self.cam=pb.camera
        self.cam.start_preview_stream()
        #self.bg=self.cam.get_preview_frame()
        pic_list=pb.pictures
        self.result_filename=pic_list.get_next()
        self.raw_filenames=pic_list.get_raw(pic_list.counter, self.n_pictures)
        self.layout=pb.layout
        self.filter=pb.filter
        self.apply()
        self.cam.start_preview_stream()
        self.wait_for_event()




    def take_pictures(self):
        self.next_action=self.next
        for i in range(self.n_pictures):
            print("taking picture "+str(i))
            t0=time()
            countdown=self.posing_timer
            while countdown > 0:
                countdown = self.posing_timer - time() + t0
                self.overlay_text=str(math.ceil(countdown))
                self.display.show_picture(self.cam.get_preview_frame(filter=self.filter), flip=True)
                self.display.show_message(self.overlay_text)
                self.display.apply()
                r , event = self.display.check_for_event()
                if r:
                    self.handle_event(event) #no events defined but anyway
            self.display.clear()
            self.display.show_message("smile ;-)")
            self.display.apply()
            self.cam.take_picture(self.raw_filenames[i])
            self.display.show_picture(self.cam.get_preview_frame(filter=self.filter), flip=True)

        self.bg=None
        self.overlay_text="processing..."
        self.apply()
        # self.cam.stop_preview_stream() todo: test does this crash 650D here??

        self.layout.assemble_pictures(self.raw_filenames, self.result_filename, filter=self.filter)


class PictOptPage(DisplayPage):
    def __init__(self, pb: Photobooth) -> object:
        timer=pb.screensaver_timer
        opt=[pb.show_slideshow,pb.show_main(), pb.toggle_pic_orientation, pb.toggle_pic_filter]
        bg=self.get_bg()
        DisplayPage.__init__(self, "Picture Options", pb.display,  options=opt, timer=timer, bg=bg)
        self.start()
    def get_bg(self):
        #todo load background
        return None

class LayoutOptPage(DisplayPage):
    def __init__(self, pb: Photobooth):
        timer=pb.screensaver_timer
        opt=[pb.show_slideshow,pb.set_layout_two, pb.set_layout_one, pb.set_layout_three]
        bg=self.get_bg()
        DisplayPage.__init__(self, "Layout Options", pb.display,  options=opt, timer=timer, bg=bg)
        self.start()

    def get_bg(self):
        #todo load background from file
        return None

class ResultPage(DisplayPage):
    def __init__(self, pb: Photobooth, photo_idx=None):
        timer= pb.screensaver_timer
        opt=[  pb.show_slideshow,pb.show_main, self.delete_pic, self.print_pic ]
        if photo_idx is None:
            self.file_name=pb.pictures.get_last()
        else:
            self.file_name=pb.pictures.get(photo_idx)
        img=self.file_name
        DisplayPage.__init__(self, "Results", pb.display, options=opt, timer=timer, bg=img)
        self.start()

    def delete_pic(self):
        pass

    def print_pic(self):
        pass


#################
### Functions ###
#################

def main():
    # Screen size
    display_size = (1024, 600)

    # Maximum size of assembled image
    image_size = (2352, 1568)

    preview_size = display_size

    # Image basename
    picture_basename = datetime.now().strftime("%Y-%m-%d/photobooth_%Y-%m-%d_")

    # Waiting time in seconds for posing
    pose_time = 3

    # Display time for assembled picture
    display_time = 10

    # Show a slideshow of existing pictures when idle
    idle_slideshow = True

    # Display time of pictures in the slideshow
    slideshow_display_time = 5

    photobooth = Photobooth(display_size, picture_basename, image_size, preview_size, pose_time, display_time,
                             slideshow_display_time)
    photobooth.run(fullscreen=False)
    photobooth.teardown()
    return 0

if __name__ == "__main__":
    exit(main())
