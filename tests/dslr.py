import time
import gphoto2cffi as gp
cam=gp.Camera()
cam._get_config()['actions']['viewfinder'].set(True)
for i in range(20):
    t0=time.time()
    pic=cam.get_preview()
    print(str(int((time.time()-t0)*100)))
    #first frame takes 2 seconds



cam._get_config()['actions']['viewfinder'].set(False)
cam._get_config()['actions']['eosremoterelease'].set('Press Half')
time.sleep(1)
cam._get_config()['actions']['eosremoterelease'].set('Release Full')
cam._get_config()['actions']['viewfinder'].set(True)
time.sleep(1)
cam._get_config()['actions']['eosremoterelease'].set('Immediate')


cam._get_config()['actions']['viewfinder'].set(False)
cam._get_config()['actions']['manualfocusdrive'].set('Near 1')

#triggers focus (which is bad)
cam._get_config()['actions']['autofocusdrive'].set(False)

img=cam.capture()
