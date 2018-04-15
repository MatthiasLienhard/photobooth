# photobooth
This is yet another photobooth application written in python3 using a Raspberry Pi, gPhoto2 and pygame.

It's intended to run on raspberry pi 3 with following devices connected:
* DSLR cam (Canon 650D)
* touchscreen (Waveshare 7" HDMI 1024*600 Rev2.1)
* big red pushbutton
* printer (Canon selphy cp1300)

## (planed) features
* supported camera types: gphoto2 (e.g. DLSR), openCV capture (webcam), picamera for raspberry pi
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

## usage
python3 photobooth.py [theme]

## Issues
DSLRs (at least the 650D) can not (hardly) focus during preview.
* workarounds:
    * camera settings: "quick mode AF" interrupts preview to focus
        * downside: takes some time to take picture ( mirror goes up and down several times)
    * camera settings: "continous AF" disabled allows to disable focus
        * manually focus (without preview) 1 second before picture is taken
        * continue preview
        * take picture without refocusing
    * use picamera for preview
        * placed next to main camera
        * placed in optical viewfinder
            * results in poor image quality
    * use other cam (no DSLR)



