#!/usr/bin/env python
# Created by br _at_ re-web _dot_ eu, 2015
#from photobooth import Photobooth
import tkinter as tk
from PIL import Image
import pygame
import time
import threading
import scipy.ndimage
import numpy as np
import random
#import pygame.event as EventModule
import pygame.event
import events
import os
GPIOEVENT=pygame.USEREVENT+1
TIMEREVENT=pygame.USEREVENT+2
BUTTONEVENT=pygame.USEREVENT+3


class GuiException(Exception):
    """Custom exception class to handle GUI class errors"""

class Button_PyGame:
    def __init__(self, surface_idx, parent, action_value,adj=None, pos=None,size=None, img_fn=None,  text=None, font_color=(0,0,0),font_size=72,  color=None, frame_color=None, press_depth=10):
        self.text=text
        self.font_size=font_size
        self.font_color=font_color
        self.action_value=action_value
        self.surface_idx=surface_idx
        self.press_depth=press_depth
        if img_fn is None and size is None:
            raise ValueError("specify either size or img")
        if img_fn is not None:
            img=pygame.image.load(img_fn)
        else:
            img=None

        if size is None:
            size=img.get_rect().size
        elif img is not None:
            img=pygame.transform.scale(img, size).convert_alpha()

        if adj is None and pos is None:
            raise ValueError("specify either adj or pos")

        self.img=img
        self.size=size
        if pos is None:
            pos=parent.get_offset(adj, size)
        else:
            pos=[ pos[i]-size[i]//2 for i in range(2) ]
        self.pos=pos
        self.color=color
        self.frame_color=frame_color
        self.screen_size=parent.size
        self.down=False

    def get_surface(self):
        surface = pygame.Surface(self.screen_size, pygame.SRCALPHA)
        pos=list(self.pos)
        if self.down:
            pos[1]+=self.press_depth
        if self.img is not None:
            surface.blit(self.img, pos)

        if self.text is not None:
            font = pygame.font.Font(None, self.font_size)
            text_size = font.size(self.text)
            text_pos=(pos[0] + (self.size[0] - text_size[0]) // 2,
                      pos[1] + (self.size[1] - text_size[1]) // 2)
            rendered_text = font.render(self.text, 1, self.font_color)
            surface.blit(rendered_text, text_pos)

        if self.frame_color is not None:
            # Render outline
            pygame.draw.rect(surface, self.frame_color, (pos[0] , pos[1] , self.size[0],self.size[1]), 1)
        return(surface, (0,0))

    def handle_click(self, pos, down=False):
        if not down:
            self.down=False
        if pos[0]>=self.pos[0] and pos[0] <= self.pos[0]+self.size[0] \
            and pos[1] >= self.pos[1] and pos[1] <= self.pos[1] + self.size[1]:
            if down:
                print("button {} pressed!".format(self.action_value))
                self.down=True
            else:
                print("button {} released!".format(self.action_value))
                pygame.event.post(pygame.event.Event(BUTTONEVENT, action=self.action_value))
            return True
        return False







class GUI_PyGame:
    """A GUI class using PyGame"""

    def __init__(self, name, size, hide_mouse=True, fullscreen=True):
        # Call init routines
        pygame.init()
        #if hasattr(pygame.event, 'init'):
        #pygame.event.init()

        # Window name
        pygame.display.set_caption(name)

        # Hide mouse cursor
        if hide_mouse:
            pygame.mouse.set_cursor(*pygame.cursors.load_xbm(
                os.path.dirname(os.path.abspath(__file__))+'/transparent.xbm',
                os.path.dirname(os.path.abspath(__file__))+'/transparent.msk'))

        # Store screen and size
        self.size = size
        if fullscreen:
            mode=pygame.FULLSCREEN
        else:
            mode=pygame.NOFRAME

        self.screen = pygame.display.set_mode(size, mode)
        self.gpio   = events.Rpi_GPIO(self.trigger_gpio_event)

        self.buttons = []

        # Clear screen
        self.clear( )
        self.apply()

    def get_offset( self,adj,item_size):
        pos=[0,0]
        for i in range(2):
            if adj[i] == 0:
                pos[i] = 0
            elif adj[i] == 1:
                pos[i] = (self.size[i]-item_size[i])//2
            elif adj[i] ==2:
                pos[i] = (self.size[i])-item_size[i]
        return tuple(pos)

    def clear(self, color=(0, 0, 0)):
        self.screen.fill(color)
        self.surface_list = []
        self.buttons=[]

    def apply(self, bg=(0, 0, 0)):
        self.screen.fill(bg)
        for surface in self.surface_list:
            self.screen.blit(surface[0], surface[1])
        pygame.display.update()

    def get_size(self):
        return self.size

    @staticmethod
    def trigger_gpio_event( event_channel):#trigger_GPIO event
        pygame.event.post(pygame.event.Event(GPIOEVENT, channel=event_channel))

    @staticmethod
    def trigger_timer_event():
        pygame.event.post(pygame.event.Event(TIMEREVENT))

    def show_picture(self, image, size=(0, 0),adj=(1,1),pos=None, flip=False, scale=True):
        # Use window size if none given
        if size == (0, 0):
            size = self.size
        if type(image) is str:
            filename=image
            try:
                # Load image from file
                print("opening "+filename)
                image = pygame.image.load(filename)
            except pygame.error as msg:
                raise GuiException("ERROR: Can't open image '" + filename + "': " + str(msg))

        else:
            try:
                mode = image.mode
                if mode is 'L':
                    rgbimg = Image.new("RGBA", image.size)
                    rgbimg.paste(image)
                    image=rgbimg
                    mode=image.mode

                data = image.tobytes()


                image = pygame.image.fromstring(data, image.size, mode)
                #image = pygame.image.frombuffer(image_buf, size, format="RGB")
            except pygame.error as msg:
                raise GuiException("ERROR: Can't read image from buffer: " + msg)
        image_size = image.get_rect().size

        if scale:
            # determine scaling factor
            image_scale = min(a / b for a, b in zip(size, image_size))
            # New image size
            image_size = [int(a * image_scale) for a in image_size]
            # Apply scaling and display picture
            image = pygame.transform.scale(image, image_size).convert()

        # Create surface and blit the image to it
        surface = pygame.Surface(image_size)
        surface.blit(image, (0, 0))
        if flip:
            surface = pygame.transform.flip(surface, True, False)

        if pos is None:
            pos=self.get_offset(adj=adj, item_size=image_size)
        else:
            pos=[pos[i]-image_size[i]+image_size[i]*adj[i]//2 for i in range(2)]
        self.surface_list.append((surface, pos))



    def show_message(self, msg, color=(0, 0, 0), bg=(230, 230, 230), transparency=True, outline=(245, 245, 245), font_size=144,adj=(1,1), pos=None, max_size=None, align=1):
        # Choose font
        font = pygame.font.Font(None,font_size)
        # Wrap and render text
        if max_size is None:
            max_size=self.size
        wrapped_text, text_height, text_width = self.wrap_text(msg, font, max_size)
        if pos is None:
            pos=self.get_offset(adj=adj, item_size=(text_width, text_height))
        else:
            pos=(pos[0]-text_width+text_width*adj[0]//2, pos[1]-text_height+text_height*adj[1]//2)
        rendered_text = self.render_text(wrapped_text, font=font, color=color, bg=bg,
                                         transparency=transparency, outline=outline, size=(text_width, text_height), align=align)
        self.surface_list.append((rendered_text, pos))


    def add_button(self, **kwargs):
        self.buttons.append(Button_PyGame(parent=self, surface_idx=len(self.surface_list),  **kwargs))
        self.surface_list.append(self.buttons[-1].get_surface())

    def release_buttons(self):
        release = []
        for i, b in enumerate(self.buttons):
            if b.down:
                b.down = False
                release.append(i)
        for i in release:
            self.surface_list[self.buttons[i].surface_idx] = self.buttons[i].get_surface()
        if release:
            self.apply()

    def wrap_text(self, msg, font, size):
        final_lines = []  # resulting wrapped text
        requested_lines = msg.splitlines()  # wrap input along line breaks
        accumulated_height = 0  # accumulated height
        max_width=0 #width of longest line
        # Form a series of lines
        for requested_line in requested_lines:
            # Handle too long lines
            if font.size(requested_line)[0] > size[0]:
                # Split at white spaces
                words = requested_line.split(' ')
                # if any of our words are too long to fit, trim them
                for word in words:
                    while font.size(word)[0] >= size[0]:
                        word = word[:-1]
                # Start a new line
                accumulated_line = ""
                # Put words on the line as long as they fit
                for word in words:
                    test_line = accumulated_line + word + " "
                    # Build the line while the words fit.   
                    if font.size(test_line)[0] < size[0]:
                        accumulated_line = test_line

                    else:
                        # Start a new line
                        line_height = font.size(accumulated_line)[1]
                        if accumulated_height + line_height > size[1]:
                            break
                        else:
                            accumulated_height += line_height
                            final_lines.append(accumulated_line)
                            accumulated_line = word + " "
                            # Finish requested_line
                line_height = font.size(accumulated_line)[1]
                max_width=max(max_width, font.size(accumulated_line)[0])
                if accumulated_height + line_height > size[1]:
                    break
                else:
                    accumulated_height += line_height
                    final_lines.append(accumulated_line)
            # Line fits as it is
            else:
                accumulated_height += font.size(requested_line)[1]
                final_lines.append(requested_line)
                max_width=max(max_width, font.size(requested_line)[0])

        # Check height of wrapped text
        if accumulated_height >= size[1]:
            raise GuiException("Wrapped text is too long to fit.")
        #print("size of {}: {}x{} ({})".format(msg, accumulated_height, max_width, font.size(final_lines[0])[0]))
        return final_lines, accumulated_height, max_width

    def render_text(self, text,  font, color, bg, transparency, outline, size, align=1):
        # Determine vertical position

        # Create Surface object and fill it with the given background
        surface = pygame.Surface(size)
        surface.fill(bg)

        # Blit one line after another
        accumulated_height = 0
        for line in text:
            maintext = font.render(line, 1, color)
            shadow = font.render(line, 1, outline)
            if align is 0:
                xpos=0
            elif align is 2:
                xpos=size[0]-font.size(line)[0]
            else:
                xpos=(size[0]-font.size(line)[0])//2
            pos = (xpos,  accumulated_height)
            # Outline
            surface.blit(shadow, (pos[0] - 1, pos[1] - 1))
            surface.blit(shadow, (pos[0] - 1, pos[1] + 1))
            surface.blit(shadow, (pos[0] + 1, pos[1] - 1))
            surface.blit(shadow, (pos[0] + 1, pos[1] + 1))
            # Text
            surface.blit(maintext, pos)
            accumulated_height += font.size(line)[1]

        # Make background color transparent
        if transparency:
            surface.set_colorkey(bg)
        # Return the rendered surface
        return surface




    def convert_event(self, event):
        if event.type == pygame.QUIT:
            return True, events.Event(0, 0)
        elif event.type == pygame.KEYDOWN:
            return True, events.Event(1, event.key)

        elif event.type == GPIOEVENT: #GPIO event
            return True, events.Event(3, event.channel)
        elif event.type == TIMEREVENT: #timer event
            return True, events.Event(4,None)
        elif event.type == BUTTONEVENT: #button event
            print("Button {} clicked".format(event.action))
            return True, events.Event(2,event.action)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pressed=[]
            for i, b in enumerate(self.buttons):
                if b.handle_click(event.pos, down=True):
                    pressed.append(i)
            for i in pressed:
                self.surface_list[self.buttons[i].surface_idx] = self.buttons[i].get_surface()
            if pressed:
                self.apply()


        elif event.type == pygame.MOUSEBUTTONUP:
            self.release_buttons()
            for b in self.buttons:
                b.handle_click(event.pos)
            #return True, events.Event(2, (event.button, event.pos))

        return False, ''

    def check_for_event(self):
        for event in pygame.event.get():
            r, e = self.convert_event(event)
            if r:
                return r, e
        return False, ''

    def wait_for_event(self, time=None):
        # Repeat until a relevant event happened
        r,e=self.check_for_event()
        if r:
            return e
        if time is not None:
            t = threading.Timer(time, self.trigger_timer_event)
            t.start()
        while True:
            # Discard all input that happened before entering the loop

            # Wait for event
            event = pygame.event.wait()
            # Return Event-Object
            r, e = self.convert_event(event)
            if r:
                if time is not None and t.is_alive():
                    t.cancel()
                return e
            else:
                pass
                # print("discarded pygames event of type {}".format(event.type))

    def set_timer(self, sec):
        #triggers timer event every [sec] seconds
        pygame.time.set_timer(TIMEREVENT, sec * 1000)


    def teardown(self):
        self.gpio.teardown()
        pygame.quit()



if __name__ == "__main__":
    import time
    display = GUI_PyGame('Photobooth', (1024,600), fullscreen=False, hide_mouse=False)
    display.show_message("testscreen")
    display.add_button(action_value=2, text="button", adj=(2, 1), size=(200, 50), font_color=(230, 0, 0), font_size=30,
                       frame_color=(255, 255, 255))
    display.apply()
    display.wait_for_event(10)
    display.clear()
    display.show_picture("themes/default/mainpage.png")
    display.show_picture("themes/default/title.png", adj=(2,0))

    display.add_button(action_value=3, adj=(0, 2), img_fn="themes/default/photo_options.png")
    display.add_button(action_value=2, adj=(2, 2), img_fn="themes/default/layout_options.png")
    display.add_button(action_value=1, adj=(1, 2), img_fn="themes/default/button.png")
    display.apply()
    display.wait_for_event(10)
    display.teardown()
