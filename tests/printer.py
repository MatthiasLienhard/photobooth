from escpos.connections import getUSBPrinter

# get with lsusb
# e.g. Bus 003 Device 003: ID 1504:0006
# lsusb -vvv -d 1504:0006 | grep bEndpointAddress | grep IN
# bEndpointAddress     0x81  EP 1 IN
printer = getUSBPrinter()(idVendor=0x1504,
                          idProduct=0x0006,
                          inputEndPoint=0x81,
                          outputEndPoint=0x01) # Create the printer object with the connection params
printer.image('/home/shantanu/companylogo.gif')

printer.text("Hello World")
printer.lf()


from escpos.connections import getFilePrinter


printer = getFilePrinter()(dev='/dev/ttys2')

printer.text("Hello World")
printer.lf()
