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

    def apply(self,img):
        img=self.monochrome(img)
        return(self.change_contrast(img,self.level))



