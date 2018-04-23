from escpos.connections import getUSBPrinter
from photobooth import PictureList
import os
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
picture_basename = datetime.now().strftime("%Y-%m-%d/photobooth_%Y-%m-%d_")
list=PictureList(picture_basename)


# get with lsusb
# e.g. Bus 003 Device 003: ID 1504:0006
# lsusb -vvv -d 1504:0006 | grep bEndpointAddress | grep IN
# bEndpointAddress     0x81  EP 1 IN
printer = getUSBPrinter()(idVendor=0x04a9,
                          idProduct=0x32db,
                          inputEndPoint=0x82,
                          outputEndPoint=0x01)
printer.image(list.get(0))
printer.lf()

