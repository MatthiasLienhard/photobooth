# the layouts (how pictures are arranged in result)
from PIL import Image
import numpy as np
import filter
import math

N_LAYOUTOPT=7



class Layout:
    def __init__(self, layout_type,  size=(2352, 1568), filter_type=0, frame_rel=.02, logo=None):
        # todo: add logo
        self.layout_type = layout_type
        self.size = size
        self.frame_rel = frame_rel
        (self.n_picture,self.img_size,self.offset,self.rotate)=self.get_parameters(layout_type)
        #self.n_picture=n_picture
        #self.img_size=img_size
        #self.offset=offset
        #self.rotate=rotate
        self.filter_list = filter.get_filters(filter_type, self.n_picture)

    def get_image_pos_and_size(self,field=0, grid_dim=4 , ratio=3/2,rotate=False, total_size=None, frame_rel=None, adj=(1,1)):
        if total_size is None:
            total_size=self.size
        if frame_rel is None:
            frame_rel=self.frame_rel
        f=frame_rel*total_size[0]
        if not isinstance(grid_dim, list) and not isinstance(grid_dim, tuple):
            grid_dim=(math.ceil(math.sqrt(grid_dim)), math.ceil(grid_dim/math.ceil(math.sqrt(grid_dim))))
        if not isinstance(field, list):
            field=(field % grid_dim[0],field// grid_dim[0])
        field_size=[round((total_size[i]-f)/grid_dim[i]-f) for i in range(2)]
        space=[0,0]
        if  (ratio > field_size[0] / field_size[1]):
            space[1] = field_size[1] - round(field_size[0]/ratio)
        elif(ratio < field_size[0] / field_size[1]):
            space[0]=field_size[0] - round(field_size[1]*ratio)
        #print("grid dim {}, field {}, size {}, cropping space: {}".format(grid_dim, field, field_size, space))
        image_size=[field_size[i]-space[i] for i in range(2)]
        if rotate:
            image_size=list(reversed(image_size))
        pos=[round(field[i]*(field_size[i]+f)+f+space[i]*adj[i]/2) for i in range(2)]
        return(pos,image_size)

    def get_parameters(self, layout_type, s=None):
        rotate=[False,False, False,False,True, False,False]
        n_picture=[1,2,4,6,6,3,2]
        offset=[(0,0)]*n_picture[layout_type]
        img_size=[(0,0)]*n_picture[layout_type]
        if layout_type < 5:
            ratio=[3/2,2/3,3/2,1/1,3/2]
            n=n_picture[layout_type]
            for i in range(n):
                offset[i],img_size[i]=self.get_image_pos_and_size(i,grid_dim=n, ratio=ratio[layout_type], rotate=rotate[layout_type], total_size=s)
            #print("layout {}: {} - {} - {} - {}".format(layout_type,n_picture[layout_type],img_size,offset,rotate[layout_type]))
        elif layout_type==5:
            offset[0],img_size[0] =self.get_image_pos_and_size(0,grid_dim=(1, 2), ratio=1, rotate=rotate[layout_type], total_size=s,adj=(0,1))
            offset[1],img_size[1] =self.get_image_pos_and_size(1,grid_dim=(1, 2), ratio=1, rotate=rotate[layout_type], total_size=s,adj=(0,1))
            offset[2],img_size[2] =self.get_image_pos_and_size(0,grid_dim=(1, 1), ratio=1, rotate=rotate[layout_type], total_size=s,adj=(2,1))
        elif layout_type==6:
            offset[0],img_size[0] =self.get_image_pos_and_size(0,grid_dim=(1, 2), ratio=3, rotate=rotate[layout_type], total_size=s,adj=(1,1))
            offset[1],img_size[1] =self.get_image_pos_and_size(1,grid_dim=(1, 2), ratio=3, rotate=rotate[layout_type], total_size=s,adj=(1,1))
        return (n_picture[layout_type],img_size,offset,rotate[layout_type])

    def assemble_pictures(self, input_imgs, size=None):
        if size is None: #use default
            (n_picture, img_size, offset, rotate)=(self.n_picture, self.img_size, self.offset, self.rotate)
            size=self.size
        else:
            (n_picture, img_size, offset, rotate) = self.get_parameters(self.layout_type, size)
        output_img = Image.new('RGB', tuple(size), (255, 255, 255))
        for i in range(n_picture):
            input_imgs[i]=filter.crop(input_imgs[i],img_size[i][0]/img_size[i][1] )
            input_imgs[i]=input_imgs[i].resize(img_size[i], Image.ANTIALIAS)
            input_imgs[i]=self.filter_list[i].apply(input_imgs[i])
            if rotate:
                input_imgs[i]=input_imgs[i].rotate(-90, expand=True)
            output_img.paste(input_imgs[i], tuple(offset[i]))
        return output_img

    def apply_filters(self, input_img, n=0):
        output_img = filter.crop(input_img, self.img_size[n][0]/self.img_size[n][1])
        output_img = self.filter_list[n].apply(output_img)
        #print("img size: {}x{}".format(output_img.size[0], output_img.size[1]))
        return output_img
