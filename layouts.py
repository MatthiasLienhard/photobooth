# the layouts (how pictures are arranged in result)
from PIL import Image
import numpy as np
import filter


N_LAYOUTOPT=3



class Layout:
    def __init__(self, layout_type,  size=(2352, 1568), filter_type=0, frame_rel=.02, logo=None):
        # todo: add logo
        self.layout_type = layout_type
        self.size = size
        self.frame_rel = frame_rel
        (self.n_picture,self.img_size,self.offset,self.crop,self.rotate)=self.get_parameters(layout_type)
        #self.n_picture=n_picture
        #self.img_size=img_size
        #self.offset=offset
        #self.crop=crop
        #self.rotate=rotate
        self.filter_list = filter.get_filters(filter_type, self.n_picture)

    def get_parameters(self, layout_type, s=None):
        if s is None:
            s = self.size
        f = int(s[0]*self.frame_rel)
        rotate=False
        if layout_type is 0:
            n_picture = 1
            img_size = np.array([s[0]-2*f, s[1]-2*f], dtype=int).reshape(-1, 2)
            offset =  np.array([f,f], dtype=int).reshape(-1, 2)
            crop = ["none"]
        elif layout_type is 1:
            n_picture=4
            a,b=[(s[i] - 3 * f) / 2 for i in range(2)]
            img_size=np.array([a,b]*4, dtype=int).reshape((-1,2))
            offset=np.array([f,f,2*f+a,f,f,2*f+b,2*f+a, 2*f+b], dtype=int).reshape((-1,2))
            crop = ["none"]*n_picture
        elif layout_type is 2:
            n_picture=6
            a=(s[0]-4*f)/3
            img_size=np.array([a]*12, dtype=int).reshape((-1,2))
            offset=np.array([f,f, a+2*f,f, 2*a+3*f,f, f,a+2*f,a+2*f,a+2*f,2*a+3*f,a+2*f], dtype=int).reshape((-1,2))
            crop = ["square"] *n_picture
            rotate=False
        else:
            raise ValueError('no layout of type ' + str(type))
        return (n_picture,img_size,offset,crop,rotate)

    def assemble_pictures(self, input_imgs, size=None):
        if size is None:
            size=self.size
        (n_picture, img_size, offset, crop, rotate) = self.get_parameters(self.layout_type, size)

        output_img = Image.new('RGB', size, (255, 255, 255))
        for i in range(n_picture):
            input_imgs[i]=filter.crop(input_imgs[i], crop[i])
            input_imgs[i]=input_imgs[i].resize(img_size[i], Image.ANTIALIAS)
            input_imgs[i]=self.filter_list[i].apply(input_imgs[i])
            output_img.paste(input_imgs[i], tuple(offset[i]))
        return output_img

    def apply_filters(self, input_img,n=0):
        output_img = filter.crop(input_img, self.crop[n])
        output_img = self.filter_list[n].apply(output_img)
        return output_img