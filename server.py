from PIL import Image, ImageDraw, ImageFont
import calendar
import datetime
import time

EPD_WIDTH = 800
EPD_HEIGHT = 480

red_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
black_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)

red_draw = ImageDraw.Draw(red_image)
black_draw = ImageDraw.Draw(black_image)

now = datetime.datetime.now()


def left_calendar():
    calendar_width = 315

    black_draw.rectangle((0, 0, calendar_width, EPD_HEIGHT), fill=0)

    week_day_name = time.strftime("%A")
    day_number = time.strftime("%d")
    month_year_str = time.strftime("%B")+' '+ time.strftime("%Y")

    calendar.setfirstweekday(6)
    month_str = calendar.month(now.year, now.month).replace(time.strftime("%B") + ' ' + time.strftime("%Y"), '')

    month_today_str = month_str
    for i in range(31, 0, -1):
        if i != now.day:
            month_today_str = month_today_str.replace(str(i).rjust(2), '  ')

    font_week_day_name = ImageFont.truetype('fonts/Roboto-Light.ttf', 35)
    font_day_number = ImageFont.truetype('fonts/Roboto-Black.ttf', 110)
    font_month_year_str = ImageFont.truetype('fonts/Roboto-Light.ttf', 25)
    font_month_str = ImageFont.truetype('fonts/FreeMonoBold.ttf', 22)
    font_status = ImageFont.truetype('fonts/Roboto-Light.ttf', 16)

    w_week_day_name, h_week_day_name = font_week_day_name.getsize(week_day_name)
    x_week_day_name = (calendar_width / 2) - (w_week_day_name / 2)

    w_day_number, h_day_number = font_day_number.getsize(day_number)
    x_day_number = (calendar_width / 2) - (w_day_number / 2)

    w_month_year_str, h_month_year_str = font_month_year_str.getsize(month_year_str)
    x_month_year_str = (calendar_width / 2) - (w_month_year_str / 2)

    w_month_str, h_month_str = font_month_str.getsize(month_str)
    x_month_str = (calendar_width / 2) - (w_month_str / 2 / (month_str.count('\n') - 1))

    black_draw.text((x_week_day_name, 30), week_day_name, font=font_week_day_name, fill=255)
    black_draw.text((x_day_number, 55), day_number, font=font_day_number, fill=255)
    red_draw.text((x_day_number, 55), day_number, font=font_day_number, fill=0)
    black_draw.text((x_month_year_str, 185), month_year_str, font=font_month_year_str, fill=255)
    black_draw.text((x_month_str + 5, 220), month_str, font=font_month_str, fill=255)
    red_draw.text((x_month_str + 5, 220), month_today_str, font=font_month_str, fill=0)

    black_draw.text((10, EPD_HEIGHT - 30), 'Updated: ' + time.strftime('%H:%M:%S'), font=font_status, fill=255)


def debug_image():
    debug_image = Image.new('RGB', (EPD_WIDTH, EPD_HEIGHT), (255, 255, 255))
    pixels = debug_image.load()

    for i in range(debug_image.size[0]):
        for j in range(debug_image.size[1]):
            if red_image.getpixel((i, j)) == 0:
                pixels[i, j] = (255, 0, 0)
            elif black_image.getpixel((i, j)) == 0:
                pixels[i, j] = (0, 0, 0)

    debug_image.show()


if __name__ == '__main__':
    left_calendar()

    black_image.save('black.bmp')
    red_image.save('red.bmp')

    # red_image.show()

    debug_image()