# photobooth
This is yet another photobooth application written in python3 using a Raspberry Pi, gPhoto2 and pygame.

It's intended to run on raspberry pi 3 with following devices connected:
* Sony Cam accessed via wifi api
* touchscreen (Waveshare 7" HDMI 1024*600 Rev2.1)
* big red pushbutton (not added yet)
* printer (Canon selphy cp1300)
* wooden case

## features
* supported camera types: Sony wifi api, gphoto2 (e.g. DLSR), openCV capture (webcam), picamera for raspberry pi
* idle state: slideshow of today's pictures
* controlled touchscreen and optional GPIO button - or keyboard (mainly for testing)
* different layouts (e.g. how pictures are arranged)
* different color filters (e.g. monochrome or fancy color filters)
* option: wide or portrait (cropped)
* preview during countdown
* preview streams are kept in memory
* print option
* customization with "themes" (used in gui and layout)

Ideas for features
* Transfer picture to smartphone (e.g. with bluetooth)
* Add effects: sephia, rainbowify
* Add layouts 
* Add banner / other theme elements in layout

## usage
python3 photobooth.py [theme] [--fullscreen]

## Issues
DSLRs (at least the 650D) can not (hardly) focus during preview.
* workarounds:
    * camera settings: "quick mode AF" interrupts preview to focus
        * downside: takes some time to take picture ( mirror goes up and down several times)
    * camera settings: "continous AF" disabled allows to disable focus
        * manually focus (without preview) 1 second before picture is taken
        * continue preview
        * take picture without refocusing
    * use additional camera (e.g. picamera) for preview
        * placed next to main camera
        * placed in optical viewfinder
            * results in poor image quality
    * use other cam (no DSLR, the mirrorless Sony alpha 6000 does not have issues with focus)
    * Switching preview on and off takes 2 seconds
## prequirements
* patched sony api (see my git sony_camera_api)
* usage of sony cam depends on network manager (which is not default on raspberrypi)




