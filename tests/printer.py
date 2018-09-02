#from escpos.connections import getUSBPrinter
#from photobooth import PictureList
import os
import cups
from time import sleep

from datetime import datetime

os.chdir("/home/pi/Pictures")
#picture_basename = datetime.now().strftime("%Y-%m-%d/photobooth_%Y-%m-%d_")
#picture_basename = "2018-07-19/photobooth_2018-07-19"
#list=PictureList(picture_basename)



# get with lsusb
# e.g. Bus 003 Device 003: ID 1504:0006
# lsusb -vvv -d 1504:0006 | grep bEndpointAddress | grep IN
# bEndpointAddress     0x81  EP 1 IN
#printer = getUSBPrinter()(idVendor=0x04a9,
#                          idProduct=0x32db,
#                          inputEndPoint=0x82,
#                          outputEndPoint=0x01)
#printer.image(list.get(0))
#printer.lf()
cups_conn=cups.Connection()
printers=cups_conn.getPrinters()
print("found printers: "+",".join(printers.keys()))
printer_name= "Canon_SELPHY_CP1300"

if printer_name is not None and printer_name in printers.keys():
    printer = printer_name
    print("found specified printer " + printer_name)
else:
    raise Exception(printer_name + " not found")


files=["DSCN4503.jpg","DSCN4554.jpg","DSCN4645.jpg","FHD0671.jpg"]
#print_id=cups_conn.printFile(printer, list.get(0), " ", {})
print_id=cups_conn.printFile(printer, files[0], " ", {})
print_id=cups_conn.printFile(printer, files[1], " ", {})

print("start printing...")
while True:
    attr = cups_conn.getPrinterAttributes(printer)
    printqueuelength = len(cups_conn.getJobs())
    print(",".join(attr['printer-state-reasons']))#=['paused']
    print(attr['printer-state-message'])#: '',
    print(attr['queued-job-count'])##=2
    print(attr['printer-state'])##=5
    print(attr['printer-error-policy'])#: 'retry-job',
    sleep(1)


