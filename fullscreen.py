#!/usr/bin/env python3

from photobooth import Photobooth
from datetime import datetime

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
    photobooth.run(fullscreen=True)
    photobooth.teardown()
    return 0

exit(main())
