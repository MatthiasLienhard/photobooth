#!/usr/bin/env python
# Created by br _at_ re-web _dot_ eu, 2015
GPIO_MAIN = 24
GPIO_LEFT = 23
GPIO_RIGHT = 22
GPIO_LAMP = 4
try:
    import RPi.GPIO as GPIO
    gpio_enabled = True

except ImportError:
    gpio_enabled = False


class Event:
    eventname = ['quit', 'key', 'mouseclick', 'gpio', 'timer']
    def __init__(self, type, value=None):
        """type  0: quit
                 1: keystroke 
                 2: mouseclick
                 3: gpio
                 4: timer
        """
        if type == 1 and value in (27,113): #ESC, q
            type=0


        self.type = type
        self.value = value

    def __str__(self):
        return "Event: " + self.get_type() + " " +str(self.value)

    def get_type(self):
        return self.eventname[self.type]

    def get_action(self):
        if self.get_type() is 'timer':
            return 0
        elif self.get_type() is 'key':
            if self.value == 274: #down
                return 1
            elif self.value == 276: #left
                return 2
            elif self.value == 275: #right
                return 3
        elif self.get_type() is 'gpio':
            if self.value == GPIO_MAIN: #down
                return 1
            elif self.value == GPIO_LEFT: #left
                return 2
            elif self.value == GPIO_RIGHT: #right
                return 3
        return None



class Rpi_GPIO:
    def __init__(self, handle_function):
        if gpio_enabled:
            input_channels = [GOIO_MAIN , GPIO_LEFT, GPIO_RIGHT ]
            output_channels = [GPIO_LAMP]
            # Display initial information
            print("Your Raspberry Pi is board revision " + str(GPIO.RPI_INFO['P1_REVISION']))
            print("RPi.GPIO version is " + str(GPIO.VERSION))

            # Choose BCM numbering system
            GPIO.setmode(GPIO.BCM)

            # Setup the input channels
            for input_channel in input_channels:
                GPIO.setup(input_channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(input_channel, GPIO.RISING, callback=handle_function, bouncetime=200)

            # Setup the output channels
            for output_channel in output_channels:
                GPIO.setup(output_channel, GPIO.OUT)
                GPIO.output(output_channel, GPIO.LOW)
        else:
            print("Warning: RPi.GPIO could not be loaded. GPIO disabled.")

    def teardown(self):
        if gpio_enabled:
            GPIO.cleanup()

    def set_output(self, channel, value=0):
        if gpio_enabled:
            GPIO.output(channel, GPIO.HIGH if value==1 else GPIO.LOW)
