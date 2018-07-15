import math
import numpy as np
from PIL import Image

#import cv2

N_FILTEROPT=5

def get_filters(filter_type, n):
    if filter_type == 0:
        return [ ImageFilter("None") for i in range(n) ]
    elif filter_type == 1:
        return [ HighContrastMonochrome() for i in range(n) ]
    elif filter_type == 2:
        samples=np.random.choice(np.arange(9),n,replace=False )
        return [ WarholCheGuevaraSerigraph(i) for i in samples ]
    elif filter_type == 3:
        return [Sepia() for i in range(n)]
    elif filter_type == 4:
        return [ Rainbowify() for i in range(n) ]

    # todo: add more filters
    else:
        raise ValueError()


def crop(img:Image, new_ratio):
    width = img.size[0]
    height = img.size[1]
    ratio=width/height
    space=[0,0]
    dev=ratio/new_ratio-1
    #print ("cropping dev={}%".format(round(dev*100)))
    if abs(dev)<0.05: #don't crop with less than ~5% deviance
        return img
    elif ratio < new_ratio: #crop top/bottom
        space[1]=height - round(width/new_ratio)
    elif ratio > new_ratio: #crop left/right
        space[0]=width - round(height*new_ratio)


    return img.crop((space[0]//2, space[1]//2, width-space[0]//2, height-space[1]//2))


class ImageFilter:
    @classmethod
    def change_contrast(cls, img, level):
        factor = (259 * (level + 255)) / (255 * (259 - level))
        def contrast(c):
            return 128 + factor * (c - 128)
        return img.point(contrast)

    @classmethod
    def monochrome(cls, img):
        return (img.convert("L"))

    @classmethod
    def hsl(cls,  h, s, l):
        # convert a given hsl color into rgb
        # (function written on the 11th of July 2017)
        # value range

        c = (1-abs(2*l-1))*s

        x = c*(1-abs(h/60%2-1))
        r,g,b = ( (c,x,0), (x,c,0), (0,c,x), (0,x,c), (x,0,c), (c,0,x) )[int(h//60)]
        m = l-c/2.
        return int((r+m)*255.), int((g+m)*255.), int((b+m)*255.)

    def __init__(self, name):
        self.name = name

    def apply(self, img):
        return img


class HighContrastMonochrome(ImageFilter):
    def __init__(self, level=100):
        ImageFilter.__init__(self,"HighContrastMonochrome")
        self.level=level

    def apply(self,img): #set b/w and increase contrast
        img=self.monochrome(img)
        return(self.change_contrast(img,self.level))

class Rainbowify(ImageFilter):
    # inspired by Jonathan Frech, jfrech.com/jblog/post180/rainbowify.py
    def __init__(self, width=20):
        ImageFilter.__init__(self,"Rainbowify")
        self.width=width

    def apply(self, img):
        w, h=img.size
        img = self.monochrome(img)
        hue = (np.array(img) / 256 * 360 + np.linspace(0,360,w*h).reshape((h,w))) % 360
        s,l=1,.5
        c = (1 - abs(2 * l - 1)) * s
        m = l - c / 2.
        x = c * (1 - abs(hue / 60 % 2 - 1)).reshape(h,w,1)
        pixels=np.empty((h,w,3))
        idx = (hue // 60).astype(int)

        sel_x = x[idx == 0]
        pixels[idx == 0] = np.concatenate((np.full_like(sel_x, c), sel_x, np.full_like(sel_x, 0)), axis=1)
        sel_x = x[idx == 1]
        pixels[idx == 1] = np.concatenate((sel_x, np.full_like(sel_x, c), np.full_like(sel_x, 0)), axis=1)
        sel_x = x[idx == 2]
        pixels[idx == 2] = np.concatenate((np.full_like(sel_x, 0), np.full_like(sel_x, c), sel_x), axis=1)
        sel_x = x[idx == 3]
        pixels[idx == 3] = np.concatenate((np.full_like(sel_x, 0), sel_x,  np.full_like(sel_x, c)), axis=1)
        sel_x = x[idx == 4]
        pixels[idx == 4] = np.concatenate((sel_x, np.full_like(sel_x, 0), np.full_like(sel_x, c)), axis=1)
        sel_x = x[idx == 5]
        pixels[idx == 5] = np.concatenate((np.full_like(sel_x, c), np.full_like(sel_x, 0), sel_x), axis=1)
        #pixels = np.concatenate((np.full_like(x, c), x, np.full_like(x, 0)), axis=2)


        pixels=(pixels+m)*255

        return (Image.fromarray(pixels.astype('uint8'), 'RGB'))
        pix=img.load()
        j=0
        # rainbowify image
        for y in range(h):
            for x in range(w):
                v = sum(pix[x, y])/3./255.
                pix[x, y] = ImageFilter.hsl((v*360+j)%360, 1, .5)
                j += 1./w/h*360

        return(img)


class Sepia(ImageFilter):
    def __init__(self):#, contrast=100, sepia=(255, 240, 192)):
        ImageFilter.__init__(self,"Sepia")
        #self.contrast=contrast
        #self.sepia=sepia

    def apply(self,img): #set b/w and increase contrast
        #img=self.monochrome(img)
        #img=self.change_contrast(img,self.contrast)
        #r,g,b=self.sepia
        #sepia_palette=np.array([ [r*i//255, g*i//255, b*i//255] for i in range(255) ]).flatten().tolist()
        #img.putpalette(sepia_palette)
        #return (img)
        pixels=np.array(img)
        # https://www.dyclassroom.com/image-processing-project/how-to-convert-a-color-image-into-sepia-image
        r = np.expand_dims(np.sum(pixels * [0.393, 0.769, 0.189], axis=2), 2)
        g = np.expand_dims(np.sum(pixels * [0.349, 0.686, 0.168], axis=2), 2)
        b = np.expand_dims(np.sum(pixels * [0.272, 0.534, 0.131], axis=2), 2)
        pixels=np.concatenate([r, g, b], axis=2)
        pixels[pixels>255]=255
        return Image.fromarray(pixels.astype('uint8'), 'RGB')


class WarholCheGuevaraSerigraph(ImageFilter):

    colorset = [
        [(255, 255, 0), (50, 9, 125), (118, 192, 0)],
        [(0, 122, 240), (255, 0, 112), (255, 255, 0)],
        [(50, 0, 130), (255, 0, 0), (243, 145, 192)],
        [(255, 126, 0), (134, 48, 149), (111, 185, 248)],
        [(255, 0, 0), (35, 35, 35), (255, 255, 255)],
        [(122, 192, 0), (255, 89, 0), (250, 255, 160)],
        [(0, 114, 100), (252, 0, 116), (250, 250, 230)],
        [(250, 255, 0), (254, 0, 0), (139, 198, 46)],
        [(253, 0, 118), (51, 2, 126), (255, 105, 0)]
    ]

    # found here: http: // www.mosesschwartz.com /?tag = python - imaging - library
    def __init__(self, idx=0):
        self.idx = idx % 9
        ImageFilter.__init__(self, "WarholCheGuevaraSerigraph_"+str(self.idx))
        # self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        # self.fgbg=cv2.BackgroundSubtractorMOG2()

    def apply(self,img):

        #get fg(face)/bg
        #img_fg=self.fgbg.apply(img)


        #fg gets bw
        img=self.monochrome(img)

        #apply colors
        pixels=np.array(self.colorset[self.idx])[(np.array(img)/256*3).astype(int)]
        return(Image.fromarray(pixels.astype('uint8'), 'RGB'))



if __name__ == "__main__":


    fn="2018-05-26/raw/photobooth_2018-05-26_00001_1.jpg"

    img=Image.open(fn)
    img=img.resize([450,300], Image.ANTIALIAS)

    #img.show()
    filter=Sepia()
    sepia=filter.apply(img)
    sepia.show()
