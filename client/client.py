from .waveshare_epd import epd7in5bc_V2
from PIL import Image


def main():
    epd = epd7in5bc_V2.EPD()
    epd.init()
    epd.Clear()

    black_layer = Image.open('black.bmp')
    red_layer = Image.open('red.bmp')

    epd.display(epd.getbuffer(black_layer), epd.getbuffer(red_layer))

    epd.sleep()


if __name__ == '__main__':
    main()
