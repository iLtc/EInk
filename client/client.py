from .waveshare_epd import epd7in5bc_V2
from PIL import Image
import random


def main():
    black_layer = Image.open('../black.bmp')
    red_layer = Image.open('../red.bmp')

    epd = epd7in5bc_V2.EPD()
    epd.init()

    if random.random() <= 0.3:
        epd.Clear()

    epd.display(epd.getbuffer(black_layer), epd.getbuffer(red_layer))

    epd.sleep()


if __name__ == '__main__':
    main()
