import logging
try:
    import cups
    _has_cups=True
except ImportError:
    _has_cups=False
    logging.info("for printer support, install pycups")
import threading

class PrintQueue:
    def __init__(self, printer_name):
        if _has_cups:
            self.count=0
            self.printing=False
            self.print_time=60 # time in seconds
            self.queue=[]
            self.cups_conn = cups.Connection()
            printers = self.cups_conn.getPrinters()
            logging.info("found printers: " + ",".join(printers.keys()))
            if printer_name is not None and printer_name in printers.keys():
                self.printer = printer_name
                logging.info("found specified printer " + printer_name)
            else:
                self.printer = None
                if printer_name is not None: logging.info(printer_name + " not found")

            #self.subscription_id = self.cups_conn.createSubscription(
            #    uri='ipp://localhost:631',
            #    recipient_uri='http://localhost:9988',
            #    events=['job-completed']
            #)
        else:
            logging.info("for printer support, install pycups")

    def get_printer_state(self):
        if _has_cups:
            msg = "no print support"
            ready=False
            if self.printer is not None:
                attr = self.cups_conn.getPrinterAttributes(self.printer)
                reasons=attr['printer-state-reasons']
                msg=attr['printer-state-message']
                nqueue=attr['queued-job-count']
                stateID=attr['printer-state']
                epolicy=attr['printer-error-policy']
                state=['0','1','2','idle','transfering','stopped','6','7']
                if stateID ==3 : #3= idle, 5=stopped
                    ready=True
                else:
                    ready=False

                if msg == 'Unplugged or turned off':
                    ready = False
                ret_msg=state[stateID]+" queue: {} ".format(nqueue)+",".join(reasons)+" "+msg
            return ready, ret_msg
        else:
            return False, "for printer support, install pycups"

    def cancel_printjobs(self):
        if _has_cups:
            nqueue = len(self.cups_conn.getJobs())
            if nqueue>0 :
                logging.info("cancle {} jobs in printing queue".format(nqueue))
                #attr=self.cups_conn.getPrinterAttributes(self.printer)

                #self.pb.cups_conn.cancelAllJobs(attr['device-uri'])
                for j in self.cups_conn.getJobs().keys():
                    self.cups_conn.cancelJob(j)
        else:
            logging.info("for printer support, install pycups")

    def printFile(self, file):
        if _has_cups:
            self.count+=1
            self.queue.append( file)
            if not self.printing:
                self.print_next()
            else:
                self.cancel_printjobs()
                self.cups_conn.printFile(self.printer, file, " ", {})
                t = threading.Timer(self.print_time, self.print_next)
                t.start()
        else:
            logging.info("for printer support, install pycups")

    def print_next(self):
        self.cancel_printjobs()
        if len(self.queue) > 0:
            self.cups_conn.printFile(self.printer, self.queue.pop(), " ", {})
            self.printing=True
            t = threading.Timer(self.print_time, self.print_next)
            t.start()
        else:
            self.printing=False