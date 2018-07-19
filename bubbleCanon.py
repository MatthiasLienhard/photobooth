from bluepy import btle
from time import time, sleep

class ScanDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print ("Discovered device {}".format( dev.addr))
        elif isNewData:
            print ("Received new data from {}".format(dev.addr))

class BubbleCanon:
    def __init__(self):
        self.conn=None
        self.write_uuid = btle.UUID(0x2222)
        # e8:c5:c5:88:83:66
        self.addr="e8:c5:c5:88:83:66"
        
    def scan(self, name="BubbleCannon", timeout=6, limitone=False):
        scanner = btle.Scanner() #.withDelegate(ScanDelegate())
        t0=time()    
        scanned=set()
        try:
          while time() < t0+timeout:
            # Scanner.scan() has no way to return early
            # so we will just do a succession of really short scans
            for d in scanner.scan(timeout = 0.1):
                if not d.addr in scanned:
                    print("new device: {}".format(d.addr))
                    scanned.add(d.addr)
                    for _,key,val in d.getScanData():
                        # print("{}: {}".format(key, val))
                        if key == "Complete Local Name" :
                            # print("device name: {}".format(val))
                            if val == name:
                                # print("Found it!")
                                self.addr=d.addr
                                return True
        except btle.BTLEException as e:
            print("    ->", e)
        
        return False
            

    def start_bubbles(self, s=20):
        if self.has_connection():
            ch = self.conn.getCharacteristics(uuid=self.write_uuid)[0]
            if s > 255: 
                s=255
            print("Bubbles for {} seconds".format(s))
            ch.write(bytes([1,s]))
            return True
        return False

    def has_connection(self):
        if self.conn is None:
            return False
        try:
            status=self.conn.status()
            print(str(status))
            if status['state'][0] == 'conn':
            	return True
            return False
        except btle.BTLEException:
            return False

    def connect(self):
        # connect to BLE
        try:
            self.conn = btle.Peripheral(self.addr, "random")
        except btle.BTLEException as e:
            print(e)	
        return self.has_connection()

    def disconnect(self):
        self.conn.disconnect()
        self.conn=None


    def list_services(self):
        for svc in self.conn.services:
            print(str(svc), ":")
            for ch in svc.getCharacteristics():
                print("    {}, hnd={}, supports {}".format(ch, hex(ch.handle), ch.propertiesToString()))
                chName = btle.AssignedNumbers.getCommonName(ch.uuid)
                if (ch.supportsRead()):
                    try:
                        print("    ->", repr(ch.read()))
                    except btle.BTLEException as e:
                        print("    ->", e)



if __name__ == '__main__':
    canon=BubbleCanon()
    if canon.scan():
         print("scan successfull")
    try:
         canon.connect()
         # sleep(10)
         # canon.list_services()
         if canon.has_connection():
             canon.start_bubbles(1)
    finally:
         canon.disconnect()

