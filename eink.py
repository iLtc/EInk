from PIL import Image, ImageDraw, ImageFont
import calendar
import datetime
import time
import requests
import utils
import config
from google.oauth2 import service_account
import googleapiclient.discovery
from .waveshare_epd import epd7in5bc_V2
import random


EPD_WIDTH = 800
EPD_HEIGHT = 480

CALENDAR_WIDTH = 300

WEATHER_HEIGHT = 100
WEATHER_WIDTH = EPD_WIDTH - CALENDAR_WIDTH

WEATHER_LAT = 40.7305044
WEATHER_LON = -74.0343007

GOOGLE_CALENDAR_WIDTH = EPD_WIDTH - CALENDAR_WIDTH
GOOGLE_CALENDAR_HEIGHT = (EPD_HEIGHT - WEATHER_HEIGHT) / 2

TASK_WIDTH = EPD_WIDTH - CALENDAR_WIDTH
TASK_HEIGHT = (EPD_HEIGHT - WEATHER_HEIGHT) / 2

red_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
black_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)

red_draw = ImageDraw.Draw(red_image)
black_draw = ImageDraw.Draw(black_image)

NOW = datetime.datetime.now(datetime.timezone.utc).astimezone()


def left_calendar():
    black_draw.rectangle((0, 0, CALENDAR_WIDTH, EPD_HEIGHT), fill=0)

    week_day_name = time.strftime("%A")
    day_number = time.strftime("%d")
    month_year_str = time.strftime("%B")+' '+ time.strftime("%Y")

    calendar.setfirstweekday(6)
    month_str = calendar.month(NOW.year, NOW.month).replace(time.strftime("%B") + ' ' + time.strftime("%Y"), '')

    month_today_str = month_str
    for i in range(31, 0, -1):
        if i != NOW.day:
            month_today_str = month_today_str.replace(str(i).rjust(2), '  ')

    font_week_day_name = ImageFont.truetype('fonts/Roboto-Light.ttf', 35)
    font_day_number = ImageFont.truetype('fonts/Roboto-Black.ttf', 110)
    font_month_year_str = ImageFont.truetype('fonts/Roboto-Light.ttf', 25)
    font_month_str = ImageFont.truetype('fonts/FreeMonoBold.ttf', 22)
    font_status = ImageFont.truetype('fonts/Roboto-Light.ttf', 16)

    w_week_day_name, h_week_day_name = font_week_day_name.getsize(week_day_name)
    x_week_day_name = (CALENDAR_WIDTH / 2) - (w_week_day_name / 2)

    w_day_number, h_day_number = font_day_number.getsize(day_number)
    x_day_number = (CALENDAR_WIDTH / 2) - (w_day_number / 2)

    w_month_year_str, h_month_year_str = font_month_year_str.getsize(month_year_str)
    x_month_year_str = (CALENDAR_WIDTH / 2) - (w_month_year_str / 2)

    w_month_str, h_month_str = font_month_str.getsize(month_str)
    x_month_str = (CALENDAR_WIDTH / 2) - (w_month_str / 2 / (month_str.count('\n') - 1))

    black_draw.text((x_week_day_name, 30), week_day_name, font=font_week_day_name, fill=255)
    black_draw.text((x_day_number, 55), day_number, font=font_day_number, fill=255)
    red_draw.text((x_day_number, 55), day_number, font=font_day_number, fill=0)
    black_draw.text((x_month_year_str, 185), month_year_str, font=font_month_year_str, fill=255)
    black_draw.text((x_month_str, 220), month_str, font=font_month_str, fill=255)
    red_draw.text((x_month_str, 220), month_today_str, font=font_month_str, fill=0)

    black_draw.text((10, EPD_HEIGHT - 30), 'Updated: ' + time.strftime('%H:%M:%S'), font=font_status, fill=255)


def right_bottom_weather():
    red_layer = Image.new('1', (WEATHER_WIDTH, WEATHER_HEIGHT), 1)
    black_layer = Image.new('1', (WEATHER_WIDTH, WEATHER_HEIGHT), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    black_layer_draw.line((0, 1, WEATHER_WIDTH, 1), 0, 3)

    weather_data = requests.get(
        'https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&units=imperial&appid={}'.format(
            WEATHER_LAT,
            WEATHER_LON,
            config.OPENWEATHERMAP_APPID
        )).json()

    weather_current = weather_data['current']

    red_card_layer, black_card_layer = weather_card(
        weather_current['weather'][0]['icon'],
        weather_current['weather'][0]['description'],
        '{} °F / {} °F'.format(weather_current['temp'], weather_current['feels_like']),
        'Now'
    )

    red_layer.paste(red_card_layer, (0, 3))
    black_layer.paste(black_card_layer, (0, 3))

    if NOW.hour < 19:
        weather_today = weather_data['daily'][0]

        red_card_layer, black_card_layer = weather_card(
            weather_today['weather'][0]['icon'],
            weather_today['weather'][0]['description'],
            '{} °F / {} °F'.format(weather_today['temp']['min'], weather_today['temp']['max']),
            'Today'
        )

    else:
        weather_tomorrow = weather_data['daily'][1]

        red_card_layer, black_card_layer = weather_card(
            weather_tomorrow['weather'][0]['icon'],
            weather_tomorrow['weather'][0]['description'],
            '{} °F / {} °F'.format(weather_tomorrow['temp']['min'], weather_tomorrow['temp']['max']),
            'Tomorrow'
        )

    red_layer.paste(red_card_layer, (int(WEATHER_WIDTH / 2), 3))
    black_layer.paste(black_card_layer, (int(WEATHER_WIDTH / 2), 3))

    return red_layer, black_layer


def weather_card(icon, title, temp, subtitle):
    red_layer = Image.new('1', (int(WEATHER_WIDTH / 2), WEATHER_HEIGHT - 3), 1)
    black_layer = Image.new('1', (int(WEATHER_WIDTH / 2), WEATHER_HEIGHT - 3), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    red_icon_layer, black_icon_layer = utils.open_weather_map_icon(icon)
    red_layer.paste(red_icon_layer, (0, int(WEATHER_HEIGHT / 2 - red_icon_layer.size[1] / 2)))
    black_layer.paste(black_icon_layer, (0, int(WEATHER_HEIGHT / 2 - black_icon_layer.size[1] / 2)))

    black_layer_draw.line((red_icon_layer.size[0], WEATHER_HEIGHT / 2, WEATHER_WIDTH, WEATHER_HEIGHT / 2), 0, 1)

    title = title.title()

    font_title = ImageFont.truetype('fonts/Roboto-Light.ttf', 22)
    font_temp = ImageFont.truetype('fonts/Roboto-Light.ttf', 15)
    font_subtitle = ImageFont.truetype('fonts/Roboto-Light.ttf', 12)

    w_title, h_title = font_title.getsize(title)
    x_title = ((WEATHER_WIDTH / 2) - red_icon_layer.size[0]) / 2 - (w_title / 2) + red_icon_layer.size[0]
    y_title = WEATHER_HEIGHT / 4 - h_title / 2

    w_temp, h_temp = font_temp.getsize(temp)
    x_temp = ((WEATHER_WIDTH / 2) - red_icon_layer.size[0]) / 2 - (w_temp / 2) + red_icon_layer.size[0]
    y_temp = WEATHER_HEIGHT / 4 * 3 - h_temp / 2 - 10

    w_subtitle, h_subtitle = font_subtitle.getsize(subtitle)
    x_subtitle = ((WEATHER_WIDTH / 2) - red_icon_layer.size[0]) / 2 - (w_subtitle / 2) + red_icon_layer.size[0]
    y_subtitle = WEATHER_HEIGHT / 4 * 3 - h_subtitle / 2 + 10

    black_layer_draw.text((x_title, y_title), title, font=font_title, fill=0)
    black_layer_draw.text((x_temp, y_temp), temp, font=font_temp, fill=0)
    black_layer_draw.text((x_subtitle, y_subtitle), subtitle, font=font_subtitle, fill=0)

    return red_layer, black_layer


def right_top_calendar():
    global GOOGLE_CALENDAR_HEIGHT
    global TASK_HEIGHT

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    credentials = service_account.Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    calendar_service = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)

    events = []

    for name, cal in config.GOOGLE_CALENDARID.items():
        data = calendar_service.events().list(
            calendarId=cal,
            orderBy='startTime',
            singleEvents=True,
            timeMin=NOW.isoformat(),
            timeMax=(NOW + datetime.timedelta(days=1)).isoformat()
        ).execute()

        for event in data['items']:
            event['cal'] = name

            events.append(event)

    events.sort(key=lambda e: e['start']['dateTime'])

    results = []

    for event in events:
        start = datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%S%z')
        end = datetime.datetime.strptime(event['end']['dateTime'], '%Y-%m-%dT%H:%M:%S%z')

        results.append([
            event['cal'],
            event['summary'],
            '{:02d}:{:02d}-{:02d}:{:02d}'.format(start.hour, start.minute, end.hour, end.minute),
            True if NOW >= start else False
        ])

    red_layer = Image.new('1', (GOOGLE_CALENDAR_WIDTH, int(GOOGLE_CALENDAR_HEIGHT)), 1)
    black_layer = Image.new('1', (GOOGLE_CALENDAR_WIDTH, int(GOOGLE_CALENDAR_HEIGHT)), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font = ImageFont.truetype('fonts/timr45w.ttf', 17)
    h_offset = -5

    for event in results:
        text = '[{}][{}]'.format(event[2], event[0])

        w, h = font.getsize(text)
        x = 0
        y = h / 2 + h_offset

        red_layer_draw.text((x, y), text, font=font, fill=0)

        if event[3]:
            red_layer_draw.text((165, y), '>>> {} <<<'.format(event[1]), font=font, fill=0)
        else:
            black_layer_draw.text((165, y), event[1], font=font, fill=0)

        h_offset += h + 12

        black_layer_draw.line((0, h_offset, GOOGLE_CALENDAR_WIDTH, h_offset), 0, 1)

        h_offset += -5

        if h_offset + h >= GOOGLE_CALENDAR_HEIGHT:
            break

    if h_offset + 10 < GOOGLE_CALENDAR_HEIGHT:
        GOOGLE_CALENDAR_HEIGHT = h_offset + 10
        TASK_HEIGHT = EPD_HEIGHT - WEATHER_HEIGHT - GOOGLE_CALENDAR_HEIGHT

    return red_layer, black_layer


def right_middle_task():
    data = requests.get(
        'https://api.todoist.com/rest/v1/projects',
        headers={'Authorization': config.TODOIST_TOKEN}).json()

    projects = {}

    for project in data:
        projects[project['id']] = project

    data = requests.get(
        'https://api.todoist.com/rest/v1/tasks',
        headers={'Authorization': config.TODOIST_TOKEN}).json()

    tasks = []

    for task in data:
        if 'due' in task:
            project_title = projects[task['project_id']]['name']

            if 'parent' in projects[task['project_id']]:
                project_title = projects[projects[task['project_id']]['parent']]['name'] + ' > ' + project_title

            task['project'] = project_title

            tasks.append(task)

    tasks.sort(key=lambda e: e['due']['date'])

    today = NOW.strftime('%Y-%m-%d')

    red_layer = Image.new('1', (TASK_WIDTH, int(TASK_HEIGHT)), 1)
    black_layer = Image.new('1', (TASK_WIDTH, int(TASK_HEIGHT)), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font = ImageFont.truetype('fonts/timr45w.ttf', 17)
    h_offset = -5

    for task in tasks:
        date = task['due']['string']
        text = task['content']
        project = '[{}]'.format(task['project'])

        w, h = font.getsize(date)
        x = 0
        y = h / 2 + h_offset

        if task['due']['date'] < today:
            red_layer_draw.text((x, y), date, font=font, fill=0)
        else:
            black_layer_draw.text((x, y), date, font=font, fill=0)

        black_layer_draw.text((55, y), text, font=font, fill=0)

        w, h = font.getsize(project)
        x = TASK_WIDTH - w
        y = h / 2 + h_offset

        black_layer_draw.text((x, y), project, font=font, fill=0)

        h_offset += h + 12

        black_layer_draw.line((0, h_offset, GOOGLE_CALENDAR_WIDTH, h_offset), 0, 1)

        h_offset += -5

        if h_offset + h >= TASK_HEIGHT:
            break

    return red_layer, black_layer


def debug():
    debug_image = Image.new('RGB', (EPD_WIDTH, EPD_HEIGHT), (255, 255, 255))
    pixels = debug_image.load()

    for i in range(debug_image.size[0]):
        for j in range(debug_image.size[1]):
            if red_image.getpixel((i, j)) == 0:
                pixels[i, j] = (255, 0, 0)
            elif black_image.getpixel((i, j)) == 0:
                pixels[i, j] = (0, 0, 0)

    debug_image.save('../debug.bmp')
    debug_image.show()


def server():
    left_calendar()

    red_layer, black_layer = right_bottom_weather()

    red_image.paste(red_layer, (CALENDAR_WIDTH + 1, EPD_HEIGHT - WEATHER_HEIGHT))
    black_image.paste(black_layer, (CALENDAR_WIDTH + 1, EPD_HEIGHT - WEATHER_HEIGHT))

    red_layer, black_layer = right_top_calendar()

    red_image.paste(red_layer, (CALENDAR_WIDTH + 1, 0))
    black_image.paste(black_layer, (CALENDAR_WIDTH + 1, 0))

    red_layer, black_layer = right_middle_task()

    red_image.paste(red_layer, (CALENDAR_WIDTH + 1, int(GOOGLE_CALENDAR_HEIGHT + 1)))
    black_image.paste(black_layer, (CALENDAR_WIDTH + 1, int(GOOGLE_CALENDAR_HEIGHT + 1)))

    black_image.save('black.bmp')
    red_image.save('red.bmp')

    # debug()


def client():
    black_layer = Image.open('black.bmp')
    red_layer = Image.open('red.bmp')

    epd = epd7in5bc_V2.EPD()
    epd.init()

    if random.random() <= 0.3:
        epd.Clear()

    epd.display(epd.getbuffer(black_layer), epd.getbuffer(red_layer))

    epd.sleep()


if __name__ == '__main__':
    server()
    client()

