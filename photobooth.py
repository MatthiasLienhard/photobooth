#!/usr/bin/env python3

import logging
import math
import os
import argparse
import datetime
from glob import glob
from sys import exit
from time import sleep, time, strftime, gmtime
from dateutil.relativedelta import relativedelta
import datetime
logging.basicConfig(filename='logfile.log',level=logging.DEBUG)
from PIL import Image
# from camera import CameraException, Camera_cv as CameraModule
# from camera import CameraException, Camera_gPhoto as CameraModule
import camera
from theme import Theme
from bubbleCanon import BubbleCanon
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
from printqueue import PrintQueue



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
        self.deleted=[]


        # Get number of latest file
        if len(pictures) == 0:
            self.counter = 0
        else:
            pictures.sort()
            last_picture = pictures[-1]
            self.counter = int(last_picture[-(self.count_width+len(self.suffix)):-len(self.suffix)])
            #todo: initialize deleted with missing files?

        # Print initial infos
        logging.info("Info: Number of last existing file: " + str(self.counter))
        logging.info("Info: Saving assembled pictures as: " + self.dirname +"/" + self.basename + "XXXXX.jpg")

    def is_deleted(self, idx):
        return idx in self.deleted

    def n_elements(self):
        return self.counter-len(self.deleted)

    def get(self, count:int):
        if count in self.deleted:
            return None
        return self.dirname+"/" + self.basename + str(count).zfill(self.count_width) + self.suffix

    def get_raw(self, count,n):
        stem=self.dirname+"/raw/"+self.basename + str(count).zfill(self.count_width)
        return [stem+'_'+str(i) + self.suffix for i in range(n)]

    def get_last(self):
        idx=self.counter
        fn=self.get(idx)
        while fn is None and idx > 0:
            idx-=1
            fn=self.get(idx)
        return fn

    def get_next(self):
        self.counter += 1
        return self.get(self.counter)

    def get_info(self):
        info=("Pictures:\nNumber of existing files: " + str(self.counter-len(self.deleted)))
        info+=("\nSaving assembled pictures as: " + self.dirname +"/" + self.basename + "XXXXX.jpg")
        return(info)
    def delete_pic(self, idx=None):
        if idx is None:
            idx=self.counter
        self.deleted.append(idx)
        #todo: actually delete the picture


class Photobooth:
    """The main class.

    It contains all the logic for the photobooth.
    """

    def __init__(self, display_size, picture_basename, picture_size, preview_size,  pose_time, display_time,
                 slideshow_display_time, printer_name=None, theme="default", bubble_prob=0,
                 cam_list=['sony_wifi','picam', 'webcam', 'dslr','dummicam']):
        self.start_info_timer=5
        self.screensaver_timer=30
        self.slideshow_timer=slideshow_display_time
        self.display=None
        self.display_size=display_size
        #self.init_display()
        self.print_queue= PrintQueue(printer_name)

        self.pictures     = PictureList(picture_basename)
        self.picture_dir  = os.path.realpath(self.pictures.dirname)
        self.picture_size = picture_size
        self.pose_time    = pose_time
        self.display_time = display_time
        self.theme        = Theme(theme)
        self.filter_sel   = 0
        self.layout_sel   = 1
        self.layout_options=[True] * N_LAYOUTOPT
        self.filter_options=[True] * N_FILTEROPT
        self.bubble_prob=bubble_prob
        self.enforce_bubbles=False
        self.bubble_canon=BubbleCanon()
        if self.bubble_canon.scan(timeout=1):
            self.bubble_canon.connect()
        self.set_layout()
        self.errors=[]
        self.current_page=None

        self.camera = camera.get_camera(picture_size, preview_size, priority_list=cam_list)
        # self.preview_camera=camera.get_camera(picture_size, preview_size,['picam', 'webcam', 'dslr','dummicam'], self.camera)
        self.preview_camera=camera.get_camera(picture_size, preview_size, priority_list=cam_list,default_cam=self.camera)


    def set_layout(self):
        self.layout = Layout(self.layout_sel, size=self.picture_size, filter_type=self.filter_sel)



    def toggle_layout(self):
        while True:
            self.layout_sel+=1
            if self.layout_sel >= N_LAYOUTOPT:
                self.layout_sel=0
            if self.layout_options[self.layout_sel]:
                break
        self.set_layout()

    def toggle_filter(self):
        while True:
            self.filter_sel+=1
            if self.filter_sel>= N_FILTEROPT:
                self.filter_sel=0
            if self.filter_options[self.filter_sel]:
                break
        self.set_layout()

    def run(self, fullscreen=True, hide_mouse=True):
        self.display = GuiModule('Photobooth', self.display_size, fullscreen=fullscreen, hide_mouse=hide_mouse)
        self.current_page = StartPage(self)
        # Enable lamp
        self.display.gpio.set_output(GPIO_LAMP, 1)
        self.running=True
        while self.running:
            logging.info("ready for next action!")
            try:
                self.current_page.next_action()
               # Catch exceptions and display message
            except camera.CameraException as e:
                self.errors.append(e)
                self.current_page.next_action=self.show_error
            # Do not catch KeyboardInterrupt and SystemExit
            except (KeyboardInterrupt, SystemExit):
                raise
            #except Exception as e:
            #    msg='SERIOUS ERROR: ' + repr(e)
            #    logging.info(msg)
            #    self.errors.append(PhotoboothException(msg))
            #    self.current_page.next_action = self.show_error

            #    self.teardown()

    def teardown(self):
        self.display.clear()
        self.display.show_message("Shutting down...")
        # todo show also self.erros if any
        self.display.apply()
        self.display.gpio.set_output(GPIO_LAMP, 0)
        self.bubble_canon.disconnect()
        self.camera.teardown()
        sleep(0.5)
        self.display.teardown()
        self.display.gpio.teardown()
        self.running=False
        exit(0)

    def show_slideshow(self):
        self.current_page=SlideshowPage(self)
    def show_main(self):
        self.current_page=MainPage(self)
    def show_shooting(self):
        self.current_page=ShootingPage(self)
    def show_result(self, idx=None):
        self.current_page=ResultPage(self, photo_idx=idx)
    def show_error(self):
        self.current_page = ErrorPage(self)
    def show_settings(self):
        self.current_page = SettingsPage(self)
    def show_layout(self):
        self.current_page = LayoutPage(self)
    def show_filter(self):
        self.current_page = FilterPage(self)

    def camera_info(self):
        info=self.camera.type
        if self.preview_camera != self.camera:
            info += " and "+ self.preview_camera.type
        return info



    def get_info_text(self):
        # todo: make better infotext
        return("Camera: {}\n\n{}\n\nprinter: {}".format(self.camera_info(),self.pictures.get_info(),self.print_queue.get_printer_state()))

#####################
### Display Pages ###
#####################

class DisplayPage:
    def __init__(self, name, display, options=None, timer=5, bg=None, overlay_text = None, teardown=None):
        if options is None:
            options = []
        self.name=name
        self.display=display
        if teardown is None:
            teardown=display.teardown
        self.teardown=teardown
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
            self.display.show_picture(self.bg, size=self.display.get_size(), adj=(1,1))
        if self.overlay_text is not None:
            self.display.show_message(self.overlay_text, font_size=self.overlay_text_size)
        self.display.apply()

    def start(self):
        self.apply()
        self.wait_for_event()

    def wait_for_event(self):
        e = self.display.wait_for_event(self.timer)
        while not self.handle_event(e):
            e = self.display.wait_for_event(self.timer)
        logging.info("leaving loop" )

    def handle_event(self,event):
        action = event.get_action()
        logging.info(self.name + " handles "+str(event))
        if event.get_type() == 'global':
            self.next_action=self.teardown
        elif action is not None and len(self.options) > action and self.options[action] is not None:
            self.next_action=self.options[action]
        else:
            return False
        return True

    def get_pos(self, field, dim=(2,2), frame=(50,50,50,50)): #frame: TLBR
        if not isinstance(field, list) and not isinstance(field, tuple):
            field=(field % dim[0],field// dim[0])
        return [round((field[i]+.5)*(self.display.size[i]-frame[0+i]-frame[2+i])/ dim[i]+frame[0+1]) for i in range(2)]

class PhotobothPage(DisplayPage):
    def __init__(self,name, pb, options=None, timer=5, bg=None, overlay_text = None):
        self.pb=pb
        DisplayPage.__init__(self, name, pb.display, options=options, timer=timer, bg=bg, overlay_text = overlay_text, teardown=pb.teardown)

    def handle_event(self,event):
        action = event.get_action()
        logging.info(self.name + " handles "+str(event) + " -> "+str(action))
        if event.get_type() == 'global':
            if event.value is 0:
                self.next_action=self.teardown
            elif event.value is 1:
                self.next_action=self.settings
            elif event.value is 2:
                self.next_action=self.bubbles
            else:
                return False
        elif action is not None and len(self.options) > action and self.options[action] is not None:
            self.next_action=self.options[action]
        else:
            return False
        return True

    def bubbles(self):
        self.pb.enforce_bubbles=True
        self.wait_for_event()

    def settings(self):
        self.next_action=self.pb.show_settings

class StartPage(PhotobothPage):
    def __init__(self, pb):
        options=[pb.show_slideshow, pb.show_slideshow ]
        PhotobothPage.__init__(self, "Start", pb,options,pb.start_info_timer)
        self.overlay_text=pb.get_info_text()
        self.overlay_text_size = 60
        self.start()

    def apply(self):
        self.display.clear()
        self.display.show_message(self.overlay_text, font_size=self.overlay_text_size)
        self.display.apply()


class ErrorPage(PhotobothPage):
    def __init__(self, pb:Photobooth):
        PhotobothPage.__init__(self, "Error", pb)
        self.overlay_text = pb.errors[-1].message
        self.timer=2
        self.options=[self.pb.teardown()]
        self.start()

class SlideshowPage(PhotobothPage):
    def __init__(self, pb, photo_idx=None):
        PhotobothPage.__init__(self, "Slideshow", pb)
        self.timer=pb.slideshow_timer
        self.options=[ self.jump_image_random,pb.show_main, self.jump_image_rev, self.jump_image_fwd,
             self.show_result,  self.jump_image_frev, self.jump_image_ffwd]
        self.image_list=pb.pictures #list of filenames
        self.n_img=self.image_list.counter
        if photo_idx is None:
            photo_idx=self.n_img
        self.photo_idx=photo_idx
        if self.image_list.is_deleted(photo_idx):
            self.jump_image_rev()



        self.bigjump=10
        if photo_idx > 0 and photo_idx <= self.n_img and self.image_list.n_elements()>0:
            self.bg = self.image_list.get(self.photo_idx)
            self.next_action=self.jump_image_fwd
            self.start()
        else:
            logging.info("No Photos - skipping slideshow")
            self.next_action=pb.show_main


    def apply(self):
        self.display.clear()
        #self.display.add_button(action_value=1, pos=(0,0),size=self.display.size)
        self.display.add_button(img_fn=self.bg, size=self.display.get_size(), adj=(1,1), press_depth=1, action_value=1, keep_ratio=True)
        self.display.show_message("#{}".format(self.photo_idx), font_size=self.overlay_text_size, adj=(0,0))
        self.display.add_button(img_fn=self.pb.theme.get_file_name("left_button"), size=(50,50), adj=(0,1),action_value=2)
        self.display.add_button(img_fn=self.pb.theme.get_file_name("right_button"), size=(50,50), adj=(2,1),action_value=3)
        self.display.add_button(img_fn=self.pb.theme.get_file_name("picture_opt"), size=(50,50), adj=(2,2),action_value=4)

        self.display.apply()
    def show_result(self):
        self.next_action=lambda i=self.photo_idx: self.pb.show_result(i)
    def jump_image_random(self):
        if (self.image_list.n_elements()>1):
            old_idx=self.photo_idx
            while self.photo_idx is old_idx or self.image_list.is_deleted(self.photo_idx) :
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
        self._jump_image(jump)
        logging.info("photo idx: {}".format(self.photo_idx))
        self.bg = self.image_list.get(self.photo_idx)
        self.apply()
        self.wait_for_event()

    def _jump_image(self, jump):
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
        if(self.image_list.is_deleted(self.photo_idx)) and self.image_list.n_elements()>0:
            self._jump_image(int(math.copysign(1,jump)))




class MainPage(PhotobothPage):
    def __init__(self, pb: Photobooth):
        PhotobothPage.__init__(self, "Main", pb)
        self.timer=pb.screensaver_timer
        self.options=[pb.show_slideshow,pb.show_shooting, self.toggle_filter, self.toggle_layout,
             pb.show_settings,pb.show_slideshow] #todo: add camera opt
        self.overlay_text="Main Menue"
        self.example_img_raw = open_images([self.pb.theme.get_file_name("test_picture", ".jpg")])
        if not self.pb.layout_options[self.pb.layout_sel]:
            self.pb.toggle_layout()
        if not self.pb.filter_options[self.pb.filter_sel]:
            self.pb.toggle_filter()
        self.set_example_img()

        self.start()

    def apply(self):
        self.display.clear()
        self.display.show_picture(self.pb.theme.get_file_name("mainpage"), scale=True)
        #self.display.show_picture(self.pb.theme.get_file_name("title"), adj=(2,0), scale=True)

        self.display.show_picture(self.example_img, adj=(1, 0), scale=False)

        self.display.add_button(action_value=2, adj=(0, 2), img_fn=self.pb.theme.get_file_name("filter_options"))
        self.display.add_button(action_value=3, adj=(2, 2), img_fn=self.pb.theme.get_file_name("layout_options"))
        self.display.add_button(action_value=1, adj=(1, 2), img_fn=self.pb.theme.get_file_name("button"))
        self.display.add_button(action_value=4, adj=(2, 0), img_fn=self.pb.theme.get_file_name("settings"),
                                size=(70, 70))
        self.display.add_button(action_value=5, adj=(0, 0), img_fn=self.pb.theme.get_file_name("slideshow_icon"),
                                size=(70, 70))
        self.display.apply()

    def set_example_img(self):
        self.example_img = self.pb.layout.assemble_pictures(self.example_img_raw * self.pb.layout.get_npic(),self.pb.theme, (600,400))
        self.example_img = self.example_img.rotate(10,expand=True)
    def toggle_filter(self):
        self.pb.toggle_filter()
        self.set_example_img()
        self.start()
    def toggle_layout(self):
        self.pb.toggle_layout()
        self.set_example_img()
        self.start()



class ShootingPage(PhotobothPage):
    def __init__(self, pb:Photobooth):
        PhotobothPage.__init__(self, "Shooting", pb, timer=2)
        #pb.cam.start_preview()
        #self.bg=pb.get_preview_frame()
        self.posing_timer=pb.pose_time
        self.options=[self.take_pictures]
        self.next=pb.show_result
        self.n_pic=pb.layout.get_npic()
        self.overlay_text ="Taking {} photos!".format(self.n_pic)
        self.cam=pb.camera
        self.prev_cam = pb.preview_camera
        #self.bg=self.cam.get_preview_frame()
        pic_list=pb.pictures
        self.result_filename=pic_list.get_next()
        self.raw_filenames=pic_list.get_raw(pic_list.counter, self.n_pic)
        self.layout=pb.layout
        if pb.enforce_bubbles or np.random.binomial(1, p=[pb.bubble_prob/100])[0]:
            if pb.bubble_canon.has_connection():
                pb.enforce_bubbles=False
                pb.bubble_canon.start_bubbles(self.n_pic*(self.posing_timer+3)+4)
                self.bg=pb.theme.get_file_name("bubbles", ".jpg")
            else:
                logging.info("I would have loved to make bubbles... :-(")
        self.apply()

        self.wait_for_event()

    def take_pictures(self):
        self.next_action=self.next
        self.display.clear()
        for i in range(self.n_pic):
            self.prev_cam.start_preview_stream()
            logging.info("taking picture {}/{}".format(i+1, self.n_pic))
            t0=time()
            countdown=self.posing_timer
            frameC=0
            while countdown > 0:
                frameC+=1
                countdown = self.posing_timer - time() + t0
                self.overlay_text=str(math.ceil(countdown))
                img=self.layout.apply_filters(self.prev_cam.get_preview_frame(), i)
                self.display.show_picture(img, flip=True, scale=True)
                #self.display.show_picture(self.prev_cam.get_preview_frame(), flip=True,  scale=True)
                self.display.show_message(self.overlay_text)
                self.display.apply()

                r , event = self.display.check_for_event()
                if r:
                    self.handle_event(event) #no events defined but anyway
            logging.info("preview framerate: {} fps".format(frameC/(time()-t0)))
            self.prev_cam.stop_preview_stream()
            self.display.clear()
            self.display.show_message("smile ;-)")
            self.display.apply()
            img=self.cam.take_picture(self.raw_filenames[i])
            self.display.show_picture(self.layout.apply_filters(img,i), flip=True, scale=True)
            self.display.apply()
            sleep(0.5)
            self.display.clear()
        self.bg=None
        self.overlay_text="processing..."
        self.apply()
        self.cam.stop_preview_stream() # todo: test does this crash 650D here??
        raw_imgs=open_images(self.raw_filenames)
        result_img=self.layout.assemble_pictures(raw_imgs, self.pb.theme)
        result_img.save(self.result_filename)


class ResultPage(PhotobothPage):
    def __init__(self, pb: Photobooth, photo_idx=None):
        timer= pb.screensaver_timer
        opt=[ pb.show_main,pb.show_main, self.delete_pic, self.print_pic ]
        self.photo_idx=photo_idx
        if photo_idx is None:
            self.file_name=pb.pictures.get_last()
        else:
            self.file_name=pb.pictures.get(photo_idx)
        img=self.file_name

        PhotobothPage.__init__(self, "Results", pb, options=opt, timer=timer, bg=img)
        self.printer_ready, self.printer_message=self.pb.print_queue.get_printer_state()
        self.start()

    def apply(self):
        self.display.clear()
        if self.bg is not None:
            self.display.show_picture(self.bg, size=self.display.get_size(), adj=(1,1))
        if self.overlay_text is not None:
            self.display.show_message(self.overlay_text, font_size=self.overlay_text_size)
        if self.printer_ready:
            self.display.add_button(action_value=3, adj=(2, 2), img_fn=self.pb.theme.get_file_name("printer"))
        self.display.show_message(self.printer_message, adj=(2, 2), font_size=30)
        self.display.add_button(action_value=2, adj=(0, 2), img_fn=self.pb.theme.get_file_name("trashbin"), size=(100,100))
        self.display.add_button(action_value=1, adj=(1, 2), img_fn=self.pb.theme.get_file_name("button_next"))
        self.display.apply()

    def delete_pic(self):
        logging.info("delete")
        self.pb.pictures.delete_pic(self.photo_idx)
        self.display.clear()
        if self.bg is not None:
            self.display.show_picture(self.bg, size=self.display.get_size(), adj=(1, 1))
        self.display.show_message("delete picture")
        self.display.apply()

        sleep(2)
        if self.pb.pictures.n_elements()>0:
            self.next_action = self.pb.show_slideshow()
        else:
            self.next_action = self.pb.show_main()


    def print_pic(self):
        self.display.clear()
        if self.bg is not None:
            self.display.show_picture(self.bg, size=self.display.get_size(), adj=(1, 1))
        self.display.apply()
        #lpr filename.jpg -P Canon_SELPHY_CP1300
        #try:
        #    subprocess.check_call(["lpr",  self.bg,  "-P", self.pb.printer])
        #except subprocess.CalledProcessError as e:
        #    logging.info(e)
        try:
            self.pb.print_queue.printFile( self.bg)
        except:
            raise #todo: what can go wrong here?

        sleep(.1)


        #self.display.show_message("start printing...")
        p_ready, p_msg = self.pb.print_queue.get_printer_state()
        self.display.show_message(p_msg, font_size=50)
        self.display.apply()
        sleep(2)
        self.next_action = self.pb.show_main()

class SettingsPage(PhotobothPage):
    def __init__(self, pb):
        options=[pb.show_main, pb.show_main, pb.show_layout, pb.show_filter, self.zoom_out, self.zoom_in,
                 self.next_theme, self.prev_theme, self.del_printjobs,self.bubble_connect, self.bubble_down, self.bubble_up,
                 self.time_down, self.time_up, pb.teardown]
        PhotobothPage.__init__(self, "Settings", pb, options, pb.screensaver_timer)
        self.themes=os.listdir('themes')
        self.theme_idx=self.themes.index(self.pb.theme.name)
        self.start()


    def apply(self):
        ncols=6
        nrows=6
        row_height=self.display.size[1]//(nrows+1)
        #row_height=100
        b_size= row_height*8//10
        cols=[self.display.size[0]*(i+1)//(ncols+1) for i in range(ncols)]
        rows=[row_height*(2*(i+1)+1)//2 for i in range(nrows)]

        self.display.clear()
        self.display.show_message("Settings", font_size=72, adj=(1,0))
        self.display.add_button(action_value=1, adj=(2, 2), img_fn=self.pb.theme.get_file_name("return"), size=(100,100))
        self.display.add_button(action_value=14, adj=(0, 2), img_fn=self.pb.theme.get_file_name("exit"),
                                   size=(100, 50))
        self.display.add_button(action_value=2, pos=(cols[2], rows[0]), adj=(1,1),size=[300, b_size], img_fn=self.pb.theme.get_file_name("layout_options_small"))
        self.display.add_button(action_value=3, pos=(cols[4], rows[0]), adj=(1,1),size=[300,b_size], img_fn=self.pb.theme.get_file_name("filter_options_small"))
        self.display.show_message("Zoom:", font_size=50, pos=(cols[1],rows[1]),   adj=(1,1) )
        self.display.show_message("{} mm".format(self.pb.camera.get_zoom()), font_size=50, pos=(cols[3],rows[1]),  adj=(1,1))
        self.display.add_button(action_value=4, pos=(cols[3]-100, rows[1]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("left_button"))
        self.display.add_button(action_value=5, pos=(cols[3]+100, rows[1]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("right_button"))
        self.display.show_message("Theme:", font_size=50, pos=(cols[1],rows[2]),  adj=(1,1) )
        self.display.show_message(self.pb.theme.name, font_size=50, pos=(cols[3],rows[2]),  adj=(1,1) )
        self.display.add_button(action_value=6, pos=(cols[3]-100, rows[2]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("left_button"))
        self.display.add_button(action_value=7, pos=(cols[3]+100, rows[2]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("right_button"))
        self.display.show_message("Printer:", font_size=50, pos=(cols[1],rows[3]), adj=(1,1) )
        self.display.add_button(action_value=8, pos=(cols[2], rows[3]), adj=(1,1),size=[b_size, b_size], img_fn=self.pb.theme.get_file_name("printer"))
        p_ready, p_msg=self.pb.print_queue.get_printer_state()
        self.display.show_message(p_msg, font_size=50, pos=((cols[2]+cols[3])/2, rows[3]), adj=(2, 1))

        self.display.show_message("Bubble gun:", font_size=50, pos=(cols[1],rows[4]),  adj=(1,1) )
        self.display.add_button(action_value=9, pos=(cols[2], rows[4]), adj=(1,1),size=[b_size, b_size], img_fn=self.pb.theme.get_file_name("ble"))
        if not self.pb.bubble_canon.is_supported():
            self.display.show_message("no ble support", font_size=50, pos=((cols[2]+cols[3])/2, rows[4]), adj=(2, 1))

        elif self.pb.bubble_canon.has_connection():
            self.display.add_button(action_value=10, pos=(cols[3]-75, rows[4]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("left_button"))
            self.display.add_button(action_value=11, pos=(cols[3]+75, rows[4]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("right_button"))
            self.display.show_message("{} %".format(self.pb.bubble_prob), font_size=50, pos=(cols[3],rows[4]),  adj=(1,1) )

        self.display.show_message("Posing Time:", font_size=50, pos=(cols[1],rows[5]),  adj=(1,1) )
        self.display.show_message(str(self.pb.pose_time), font_size=50, pos=(cols[3],rows[5]),  adj=(1,1) )
        self.display.add_button(action_value=12, pos=(cols[3]-100, rows[5]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("left_button"))
        self.display.add_button(action_value=13, pos=(cols[3]+100, rows[5]), adj=(1,1),size=[b_size,b_size], img_fn=self.pb.theme.get_file_name("right_button"))


        self.display.apply()

    def zoom_out(self):
        self.pb.camera.zoom_out( )
        self.next_action = self.pb.show_settings()

    def zoom_in(self):
        self.pb.camera.zoom_in( )
        self.next_action = self.pb.show_settings()

    def bubble_connect(self):
        if self.pb.bubble_canon.is_supported():
            self.display.show_message("scanning...", font_size=50, pos=self.get_pos((3,4), dim=(6,6), frame=(0,0,0,0)),  adj=(1,1) )
            self.display.apply()
            self.pb.bubble_canon.scan()
            self.pb.bubble_canon.connect()
        self.next_action = self.pb.show_settings()
    def time_up(self):
        self.pb.pose_time+=1;
        self.start()


    def time_down(self):
        if(self.pb.pose_time>0):
            self.pb.pose_time-=1;
        self.start()


    def bubble_up(self):
        self.pb.bubble_prob+=5
        if(self.pb.bubble_prob>100):
            self.pb.bubble_prob=100
        self.start()

    def bubble_down(self):
        self.pb.bubble_prob-=5
        if(self.pb.bubble_prob<0):
            self.pb.bubble_prob=0
        self.start()

    def next_theme(self):
        self.theme_idx+=1
        if self.theme_idx >= len(self.themes):
            self.theme_idx=0
        self.pb.theme = Theme(self.themes[self.theme_idx])
        self.start()

    def prev_theme(self):
        self.theme_idx-=1
        if self.theme_idx < 0:
            self.theme_idx=len(self.themes)-1
        self.pb.theme = Theme(self.themes[self.theme_idx])
        self.start()

    def del_printjobs(self):
        self.pb.print_queue.cancel_printjobs()
        self.start()

class LayoutPage(PhotobothPage):
    def __init__(self, pb):
        options=[pb.show_settings, pb.show_settings]
        self.example_img_raw = open_images([pb.theme.get_file_name("test_picture", ".jpg")])
        self.example_img = []
        self.grid_dim=(math.ceil(math.sqrt(N_LAYOUTOPT)), math.ceil(N_LAYOUTOPT/math.ceil(math.sqrt(N_LAYOUTOPT))))
        img_height=(pb.display_size[1]-150)//self.grid_dim[0]
        for i in range(N_LAYOUTOPT):
            layout=Layout(layout_type=i, filter_type=pb.filter_sel)
            options.append(lambda i=i: self.toggle(i))
            self.example_img.append(layout.assemble_pictures(self.example_img_raw * layout.get_npic(),pb.theme,(img_height*3//2,img_height) ))
        PhotobothPage.__init__(self, "LayoutSelection", pb, options, pb.screensaver_timer)
        self.start()

    def apply(self):
        self.display.clear()
        for i in range(N_LAYOUTOPT):
            self.display.show_picture(self.example_img[i],pos=self.get_pos(i,self.grid_dim),adj=(1,1), scale=False)
            button=self.pb.theme.get_file_name("check")
            if not self.pb.layout_options[i]:
                button=self.pb.theme.get_file_name("remove")
            self.display.add_button(action_value=i+2,pos=self.get_pos(i,self.grid_dim), adj=(1, 1), img_fn=button, size=(100,100), press_depth=1)
        self.display.add_button(action_value=1, adj=(2, 2), img_fn=self.pb.theme.get_file_name("return"), size=(100,100))

        self.display.apply()

    def toggle(self, i):
        self.pb.layout_options[i]= not self.pb.layout_options[i]
        if not any(self.pb.layout_options):
            self.pb.layout_options[0]=True
        self.start()




class FilterPage(PhotobothPage):
    def __init__(self, pb):
        options=[pb.show_settings, pb.show_settings]
        self.example_img_raw = open_images([pb.theme.get_file_name("test_picture", ".jpg")])
        self.example_img = []
        self.grid_dim=(math.ceil(math.sqrt(N_FILTEROPT)), math.ceil(N_FILTEROPT/math.ceil(math.sqrt(N_FILTEROPT))))
        img_height=(pb.display_size[1]-150)//self.grid_dim[0]
        for i in range(N_FILTEROPT):
            layout=Layout(layout_type=pb.layout_sel, filter_type=i)
            options.append(lambda i=i: self.toggle(i))
            self.example_img.append(layout.assemble_pictures(self.example_img_raw * layout.get_npic(),pb.theme,(img_height*3//2,img_height) ))
        PhotobothPage.__init__(self, "LayoutSelection", pb, options, pb.screensaver_timer)
        self.start()

    def apply(self):
        self.display.clear()
        for i in range(N_FILTEROPT):
            self.display.show_picture(self.example_img[i],pos=self.get_pos(i,self.grid_dim),adj=(1,1), scale=False)
            button=self.pb.theme.get_file_name("check")
            if not self.pb.filter_options[i]:
                button=self.pb.theme.get_file_name("remove")
            self.display.add_button(action_value=i+2,pos=self.get_pos(i,self.grid_dim), adj=(1, 1), img_fn=button, size=(100,100), press_depth=1)
        self.display.add_button(action_value=1, adj=(2, 2), img_fn=self.pb.theme.get_file_name("return"), size=(100,100))

        self.display.apply()

    def toggle(self, i):
        self.pb.filter_options[i]= not self.pb.filter_options[i]
        if not any(self.pb.filter_options):
            self.pb.filter_options[0]=True

        self.start()


class TimePage(DisplayPage):
    def __init__(self, display):

        DisplayPage.__init__(self, "SetTimePage", display)
        self.t= datetime.datetime.now()
        self.theme = Theme("default")
        self.grid_dim=(5,5)
        self.options=[self.teardown, self.teardown]
        for i in range(3):
            self.options.append(lambda i=i: self.up(i))
            self.options.append(lambda i=i: self.down(i))
        self.start()

    def start(self):
        self.apply()
        self.wait_for_event()
        self.next_action()

    def apply(self):
        self.display.clear()
        self.display.show_message("Set the date", adj=(1,0))
        for i in range(3):
            self.display.add_button(action_value=i*2+2,pos=self.get_pos((i+1,1),self.grid_dim), adj=(1, 1), img_fn=self.theme.get_file_name("up_button"), size=(100,100), press_depth=1)
            self.display.show_message(str(self.get(i)),pos=self.get_pos((i+1,2),self.grid_dim), adj=(1, 1))
            self.display.add_button(action_value=i*2+3,pos=self.get_pos((i+1,3),self.grid_dim), adj=(1, 1), img_fn=self.theme.get_file_name("down_button"), size=(100,100), press_depth=1)
        self.display.add_button(action_value=0,adj=(1,2), text="OK", frame_color=(255,0,0),font_color=(255,255,255), size=(100,50) )
        self.display.apply()


    def get(self, i):
        if i == 0:
            return self.t.day
        elif i==1:
            return self.t.month
        else:
            return self.t.year
    def change(self,i,dif):
        if i == 0:
            self.t += relativedelta(days=dif)
        elif i==1:
            self.t += relativedelta(months=dif)
        else:
            self.t += relativedelta(years=dif)
        logging.info("changed date")
        self.start()

    def up(self, i):
        self.change(i,1)

    def down(self,i):
        self.change(i,-1)

#################
### Functions ###
#################


def internet_time(NTP_SERVER = '0.uk.pool.ntp.org'):
    from socket import socket, AF_INET, SOCK_DGRAM
    import struct
    TIME1970 = 2208988800
    client = socket(AF_INET, SOCK_DGRAM)
    client.settimeout(1)
    data = '\x1b' + 47 * '\0'
    try:
        client.sendto(data.encode('utf-8'), (NTP_SERVER, 123))
        data, address = client.recvfrom(1024)
    except:
        return False
    #if data: logging.info('Response received from:', address)
    t = struct.unpack('!12I', data)[10] - TIME1970
    return datetime.datetime.fromtimestamp(t)

def display_time(display_size, fullscreen):
    display = GuiModule('Set Time', display_size, hide_mouse=False, fullscreen=fullscreen)
    page = TimePage(display)
    return(page.t)

def main(args):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Image basename
    t=False #speed up 
    #t=internet_time()
    
    #if True:
    if not t:
        t=display_time(args.display_size, args.fullscreen)
    logging.info("Time: {}:".format(t))
    picture_basename = t.strftime("%Y-%m-%d/photobooth_%Y-%m-%d_")
    photobooth = Photobooth(args.display_size, picture_basename, args.image_size, args.preview_size, args.pose_time, args.display_time,
                             args.slideshow_time, printer_name=args.printer, theme=args.theme, cam_list=args.cam)
    photobooth.run(fullscreen=args.fullscreen, hide_mouse= not args.mouse)
    return 0

class ResolutionAction(argparse.Action):
    # parse the resolution string
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            res=values.split("x")
            res=(int(res[0]), int(res[1]))
        except:
            raise argparse.ArgumentTypeError("resolution must be WWWxHHH")
        setattr(namespace, self.dest, res)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Photobooth application')
    parser.add_argument('-f','--fullscreen', help="run in fullscreen mode", action="store_true")
    parser.add_argument('-m','--mouse', help="show mouse point", action="store_true")
    parser.add_argument('-ds','--display_size', metavar='WWWxHHH', help="the size of the window/screen", default=(1024,600), action=ResolutionAction)
    parser.add_argument('-is','--image_size', metavar='WWWxHHH', help="the size of the resulting picture", default=(2352,1568), action=ResolutionAction)
    parser.add_argument('-ps','--preview_size', metavar='WWWxHHH', help="the size of the preview image", default=(900,600), action=ResolutionAction)
    parser.add_argument('-pt','--pose_time',metavar='<int>',type=int, help="countdown time", default=3)
    parser.add_argument('-st','--slideshow_time',metavar='<int>',type=int, help="Display time of pictures in the slideshow", default=5)
    parser.add_argument('-dt','--display_time',metavar='<int>',type=int, help="Display time for assembled picture", default=10)
    parser.add_argument('--theme',metavar='<string>',type=str, help="display theme name", default="default")
    parser.add_argument('--cam',metavar='list of <string>',type=str, help="cameras to use", nargs="+", default=['sony_wifi','picam', 'webcam', 'dslr','dummicam'])
    parser.add_argument('--printer',metavar='<NAME>', help="Name of CUPS printer", default="Canon_SELPHY_CP1300")
    args = parser.parse_args()
    logging.info("args:")
    for arg in vars(args):
        logging.info("{}: {}".format(arg, getattr(args, arg)))
    exit(main(args))
