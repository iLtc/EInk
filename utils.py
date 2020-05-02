import requests
from PIL import Image
from io import BytesIO


def open_weather_map_icon(code):
    icon = requests.get('https://openweathermap.org/img/wn/{}@2x.png'.format(code))

    image = Image.open(BytesIO(icon.content))

    # image.show()

    canvas = Image.new('RGB', image.size, (255, 255, 255))

    canvas.paste(image, mask=image)

    # canvas.show()

    red_image = Image.new('1', canvas.size, 1)
    black_image = Image.new('1', canvas.size, 1)

    red_pixels = red_image.load()
    black_pixels = black_image.load()

    red, green, blue = canvas.split()

    for i in range(canvas.size[0]):
        for j in range(canvas.size[1]):
            if red.getpixel((i, j)) == 255:
                continue

            if red.getpixel((i, j)) > 220 and blue.getpixel((i, j)) < 235:
                red_pixels[i, j] = 0
            else:
                black_pixels[i, j] = 0

    return red_image, black_image


if __name__ == '__main__':
    open_weather_map_icon('11d')
