from PIL import Image, ImageOps
import numpy as np
import cv2

N_FILTEROPT=3

def get_filters(filter_type, n):
    if filter_type == 0:
        return [ ImageFilter("None") for i in range(n) ]
    elif filter_type == 1:
        return [ HighContrastMonochrome() for i in range(n) ]
    elif filter_type == 2:
        return [ WarholCheGuevaraSerigraph(i) for i in range(n) ]
    # todo: add more filters
    else:
        raise ValueError()


def crop(img:Image, mode):
    width = img.size[0]
    height = img.size[1]
    ratio=width/height
    if mode is "none":
        return img
    elif mode is "square":
        new_width = height
    elif mode is "portrait":
        new_width=height/ratio
    else:
        raise ValueError('crop mode should be "none", "square", or "portrait"')
    return img.crop((int((width-new_width)/2),0,int((width+new_width)/2), height))


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
        #self.fgbg=cv2.BackgroundSubtractorMOG2()

    def apply(self,img):

        #get fg(face)/bg
        #img_fg=self.fgbg.apply(img)


        #fg gets bw
        img=self.monochrome(img)

        #apply colors
        pixels=np.array(self.colorset[self.idx])[(np.array(img)/256*3).astype(int)]
        return(Image.fromarray(pixels.astype('uint8'), 'RGB'))




#"projects/github/photobooth/2018-04-14/photobooth_2018-04-14_00001.jpg"

#img=Image.open(fn)