#!/usr/bin/python

from PIL import Image, ImageDraw,ImageStat,ImageEnhance
from easyprocess import Proc
import math
import os
import time

# the change in brightness needed to register the end of the bar graph
# might need adjusting
sens = 20

# where we store the raw photo of the meter
image_file = "meter.jpg"

# where we store the output photo
processed_file = "read.jpg"

# taken from the minim instructions
e_map = [ 10, 50, 100, 150, 200, 250, 350, 450, 550, 650, 750, 950, 1150, 1350, 1550, 2000, 2500, 3000, 3500, 4000, 4500, 5500, 6500, 7500, 8500, 10000, 12000, 14000, 16000, 18000, ]

class Meter_Exception(Exception):
    def __init__(self, message):
        super(Meter_Exception, self).__init__(message)
        self.message = message

# take a photo with a timeout
def take_photo(timeout,logger):
    # will almost certainly need adjusting for your setup
    cmd = '/usr/bin/fswebcam -q -d /dev/video0  -r 800x600 --no-banner  --set "Exposure, Auto"="Manual Mode" --set "Exposure (Absolute)"=200 --set brightness=50% --set "Exposure, Auto Priority"="False" ' + image_file
    proc=Proc(cmd).call(timeout=timeout)
    if proc.stderr:
        logger.warning(proc.stderr)
    return proc.return_code

# crop and adjust contrast
def adjust(im):
    im=im.convert('L')
    w = 500
    h = 350
    box = (80,60,w,h)
    region = im.crop(box)
    contr = ImageEnhance.Contrast(region)
    region = contr.enhance(2.0)
    return region

# returns the average value of a region of pixels
def avg_region(image,box):
    region = image.crop(box)
    stat = ImageStat.Stat(region)
    return stat.mean[0]

# read energy from a prepared image of the meter
# this works by looking at the circular bar graph
# and looking for big changes in image brightness
def read_energy(img,logger):
    draw = ImageDraw.Draw(img)
    img_width = img.size[0]
    img_height = img.size[1]
    sample_w = 7 # size of a block of pixels to look at
    cent_x = img_width / 2
    cent_y = img_height * 0.71
    length = img_width / 2.8 # radius of bar graph

    # half length of bar graph in degrees
    arc_l = 104
    segment = 1
    arc_step = 2
    d = -arc_l
    segs = 0
    last_bright = 255
    fill = 0
    change = False
    while d < arc_l:
        segs += 1
        d += arc_step
        # each segment in the bar is a bit bigger than the last
        arc_step += 0.37
        deg = d - 90
        x = cent_x + length * math.cos(math.radians(deg))
        y = cent_y + length * math.sin(math.radians(deg))
        x = int(x)
        y = int(y)

        # create a region over where we think the bar segment will be
        box = (x, y, x+sample_w, y+sample_w)
        bright = avg_region(img,box)
        logger.debug( "lb = %d, b= %d" % ( bright - last_bright, bright))
        if change == False and (bright - last_bright ) > sens:
            logger.debug( e_map[segs] )
            segment = segs
            fill = 255
            change = True
        draw.rectangle(box,fill=fill)

        # adapt to changing brightness
        last_bright = bright

    segment -= 1  # because list is 0 indexed
    logger.debug("total segs=%d" % segs)
    logger.debug("segment=%d energy=%dW" % (segment, e_map[segment])) 
    img.save(processed_file)
    return(e_map[segment])


def read_meter(logger, timeout=10):
    # remove existing image to guarantee we don't use an old image
    try:
        os.remove(image_file)
    except OSError:
        pass
    logger.debug("taking photo with timeout = %d", timeout)
    ret = take_photo(timeout,logger)
    if ret == -15:
        raise Meter_Exception("photo timed out")
    logger.debug("took photo")

    # check we have an image
    try:
        img = Image.open(image_file)
    except IOError:
        raise Meter_Exception("no photo taken")
        
    # adjust image - crop and contrast
    img = adjust(img)

    # read the bar graph
    energy = read_energy(img,logger)
    return energy

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info("energy=%dW" % read_meter(logging))
