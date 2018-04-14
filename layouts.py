# the layouts (how pictures are arranged in result)

from PIL import Image
from filter import *

class Layout:
    def __init__(self, type, size=(2352, 1568), frame_rel=(.05,.05)):
        self.type = type
        self.size = size
        self.frame_rel=frame_rel
        self.frame_width=tuple(int(self.size[i]*self.frame_rel[i]) for i in range(2))
        if type is 0:
            self.n_picture=1
            self.img_size=tuple(int(self.size[i]-self.frame_width[i]) for i in range(2))
        elif type is 1:
            self.n_picture=4
            self.img_size=tuple(int((self.size[i]-self.frame_width[i])/2) for i in range(2))
        elif type is 2:
            self.n_picture=6
            self.img_size=tuple(int((self.size[i]-self.frame_width[i])/3) for i in range(2))
        else:
            raise ValueError('no layout of type ' + str(type))
    def assemble_pictures(self, input_filenames, output_filename, filter=None):
        # Thumbnail size of pictures
        # todo: use values from class
        outer_border = 50
        inner_border = 20
        thumb_box = ( int( self.size[0] / 2 ) ,
                      int( self.size[1] / 2 ) )
        thumb_size = ( thumb_box[0] - outer_border - inner_border ,
                       thumb_box[1] - outer_border - inner_border )

        # Create output image with white background
        output_image = Image.new('RGB', self.size, (255, 255, 255))

        # Image 0
        img = Image.open(input_filenames[0])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] - inner_border - img.size[0] ,
                   thumb_box[1] - inner_border - img.size[1] )
        output_image.paste(img, offset)

        # Image 1
        img = Image.open(input_filenames[1])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] + inner_border,
                   thumb_box[1] - inner_border - img.size[1] )
        output_image.paste(img, offset)

        # Image 2
        img = Image.open(input_filenames[2])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] - inner_border - img.size[0] ,
                   thumb_box[1] + inner_border )
        output_image.paste(img, offset)

        # Image 3
        img = Image.open(input_filenames[3])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] + inner_border ,
                   thumb_box[1] + inner_border )
        output_image.paste(img, offset)

        if filter is not None:
            output_image = filter.apply(output_image)

        # Save assembled image

        output_image.save(output_filename, "JPEG")
        return output_filename
