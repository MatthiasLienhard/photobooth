from PIL import Image

N_FILTEROPT=2

def get_filters(filter_type, n):
    if filter_type == 0:
        return [ ImageFilter("None") for i in range(n) ]
    elif filter_type == 1:
        return [ HighContrastMonochrome() for i in range(n) ]
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



