from PIL import Image, ImageDraw, ImageFont
import datetime
import requests
import config
from google.oauth2 import service_account
import googleapiclient.discovery
import sys
from eink import debug, client


EPD_WIDTH = 800
EPD_HEIGHT = 480

HEADER_HEIGHT = 30

WEATHER_LAT = 40.7305044
WEATHER_LON = -74.0343007

NOW = datetime.datetime.now(datetime.timezone.utc).astimezone()


def google_events(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important):
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

    for event in events:
        start = datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%S%z')
        end = datetime.datetime.strptime(event['end']['dateTime'], '%Y-%m-%dT%H:%M:%S%z')

        item = {
            'left': '[{}][{}]'.format('{:02d}:{:02d}-{:02d}:{:02d}'.format(start.hour, start.minute, end.hour, end.minute), event['cal']),
            'left_red': True,
            'main': event['summary'] if NOW < start else '>>> {} <<<'.format(event['summary']),
            'main_red': True if NOW >= start else False,
            'right': '',
            'right_red': False
        }

        if event['cal'] in ['Study', 'Work', 'NYU']:  # Important
            if start <= (NOW + datetime.timedelta(hours=8)):  # Urgent
                urgent_important.append(item)

            else:  # Not Urgent
                not_urgent_important.append(item)

        else:
            if start <= (NOW + datetime.timedelta(hours=8)):  # Urgent
                urgent_not_important.append(item)

            else:  # Not Urgent
                not_urgent_not_important.append(item)


def todo_tasks(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important):
    data = requests.get(
        'https://api.todoist.com/rest/v1/projects',
        headers={'Authorization': config.TODOIST_TOKEN}).json()

    projects = {}
    inbox_id = 0

    for project in data:
        projects[project['id']] = project

        if project['name'] == 'Inbox':
            inbox_id = project['id']

    data = requests.get(
        'https://api.todoist.com/rest/v1/tasks',
        headers={'Authorization': config.TODOIST_TOKEN}).json()

    for task in data:
        projects[task['id']] = task

    inbox_tasks = []

    for task in data:
        if task['project_id'] == inbox_id:
            task['project'] = 'Inbox'
            inbox_tasks.append(task)

    tasks = []

    three_days = (NOW + datetime.timedelta(days=3)).strftime('%Y-%m-%d')

    for task in data:
        if 'due' in task:
            if task['due']['date'] > three_days:
                continue

            if 'parent' in task:
                project_id = task['parent']

                if 'name' in projects[project_id]:
                    project_title = projects[project_id]['name']
                else:
                    project_title = projects[project_id]['content']
            else:
                project_id = task['project_id']
                project_title = projects[project_id]['name']

            if 'parent' in projects[task['project_id']]:
                project_title = projects[projects[task['project_id']]['parent']]['name'] + ' > ' + project_title

            task['project'] = project_title

            tasks.append(task)

    tasks.sort(key=lambda e: (e['due']['date'], -e['priority'], e['content']))

    tasks += inbox_tasks

    today = NOW.strftime('%Y-%m-%d')

    for task in tasks:
        item = {
            'left': task['due']['string'] if 'due' in task else 'No Due',
            'left_red': True if 'due' in task and task['due']['date'] < today else False,
            'main': task['content'],
            'main_red': False,
            'right': '[{}]'.format(task['project']),
            'right_red': False
        }

        if task['priority'] > 1:  # Important
            if 'due' in task and task['due']['date'] <= today:  # Urgent
                urgent_important.append(item)

            else:
                not_urgent_important.append(item)

        else:
            if 'due' in task and task['due']['date'] <= today:  # Urgent
                urgent_not_important.append(item)

            else:
                not_urgent_not_important.append(item)


def weather(not_urgent_not_important):
    weather_data = requests.get(
        'https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&units=imperial&appid={}'.format(
            WEATHER_LAT,
            WEATHER_LON,
            config.OPENWEATHERMAP_APPID
        )).json()

    weather_current = weather_data['current']

    not_urgent_not_important.append({
        'left': '[Now]',
        'left_red': True,
        'main': weather_current['weather'][0]['description'].title(),
        'main_red': False,
        'main_x': 100,
        'right': '{} °F / {} °F'.format(round(weather_current['feels_like']), round(weather_current['temp'])),
        'right_red': False
    })

    weather_today = weather_data['daily'][0]

    not_urgent_not_important.append({
        'left': '[Today]',
        'left_red': True,
        'main': weather_today['weather'][0]['description'].title(),
        'main_red': False,
        'main_x': 100,
        'right': '{} °F / {} °F'.format(round(weather_today['temp']['min']), round(weather_today['temp']['max'])),
        'right_red': False
    })

    weather_tomorrow = weather_data['daily'][1]

    not_urgent_not_important.append({
        'left': '[Tomorrow]',
        'left_red': False,
        'main': weather_tomorrow['weather'][0]['description'].title(),
        'main_red': False,
        'main_x': 100,
        'right': '{} °F / {} °F'.format(round(weather_tomorrow['temp']['min']), round(weather_tomorrow['temp']['max'])),
        'right_red': False
    })


def quadrant_card(items, width, height):
    width = int(width)
    height = int(height)

    red_layer = Image.new('1', (width, height), 1)
    black_layer = Image.new('1', (width, height), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font = ImageFont.truetype('fonts/timr45w.ttf', 18)
    h_offset = -9

    if len(items) == 0:
        text = 'All down! Good job!'

        w, h = font.getsize(text)
        x = width / 2 - w / 2
        y = h / 2 + h_offset

        black_layer_draw.text((x, y), text, font=font, fill=0)

        h_offset += 31

        black_layer_draw.line((0, h_offset, width, h_offset), 0, 1)

        h_offset += -6

    count = 0

    for item in items:
        count += 1

        lw, h = font.getsize(item['left'])
        lx = 0
        y = h / 2 + h_offset

        rw, _ = font.getsize(item['right'])
        rx = width - rw

        mw, _ = font.getsize(item['main'])

        while width - lw - rw - 15 < mw:
            item['main'] = item['main'][:-4] + '...'
            mw, _ = font.getsize(item['main'])

        if 'main_x' not in item:
            mx = lw + 10
        else:
            mx = item['main_x']

        if item['left_red']:
            red_layer_draw.text((lx, y), item['left'], font=font, fill=0)
        else:
            black_layer_draw.text((lx, y), item['left'], font=font, fill=0)

        if item['main_red']:
            red_layer_draw.text((mx, y), item['main'], font=font, fill=0)
        else:
            black_layer_draw.text((mx, y), item['main'], font=font, fill=0)

        if item['right_red']:
            red_layer_draw.text((rx, y), item['right'], font=font, fill=0)
        else:
            black_layer_draw.text((rx, y), item['right'], font=font, fill=0)

        h_offset += 31

        black_layer_draw.line((0, h_offset, width, h_offset), 0, 1)

        h_offset += -6

        if h_offset + 2 * h >= height and len(item) - count > 1:
            text = 'And {} more tasks or events for the next 3 days ......'.format(len(item) - count)

            w, h = font.getsize(text)
            x = width / 2 - w / 2
            y = h / 2 + h_offset

            red_layer_draw.text((x, y), text, font=font, fill=0)

            break

    return red_layer, black_layer


def four_quadrants(even_day):
    urgent_important = []
    urgent_not_important = []
    not_urgent_important = []
    not_urgent_not_important = []

    google_events(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important)
    todo_tasks(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important)
    weather(not_urgent_not_important)

    red_layer = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
    black_layer = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font_title = ImageFont.truetype('fonts/Roboto-Regular.ttf', 20)

    titles = [{'text': 'Urgent',
               'x': ((EPD_WIDTH - HEADER_HEIGHT) / 4 + HEADER_HEIGHT) if even_day else ((EPD_WIDTH - HEADER_HEIGHT) / 4),
               'y': (HEADER_HEIGHT / 2) if even_day else (EPD_HEIGHT - (HEADER_HEIGHT / 2)),
               'rotate': False},
              {'text': 'Not Urgent',
               'x': ((EPD_WIDTH - HEADER_HEIGHT) / 4 * 3 + HEADER_HEIGHT) if even_day else ((EPD_WIDTH - HEADER_HEIGHT) / 4 * 3),
               'y': (HEADER_HEIGHT / 2) if even_day else (EPD_HEIGHT - (HEADER_HEIGHT / 2)),
               'rotate': False},
              {'text': 'Important',
               'x': (HEADER_HEIGHT / 2) if even_day else (EPD_WIDTH - HEADER_HEIGHT / 2),
               'y': ((EPD_HEIGHT - HEADER_HEIGHT) / 4 + HEADER_HEIGHT) if even_day else ((EPD_HEIGHT - HEADER_HEIGHT) / 4),
               'rotate': True},
              {'text': 'Not Important',
               'x': (HEADER_HEIGHT / 2) if even_day else (EPD_WIDTH - HEADER_HEIGHT / 2),
               'y': ((EPD_HEIGHT - HEADER_HEIGHT) / 4 * 3 + HEADER_HEIGHT) if even_day else ((EPD_HEIGHT - HEADER_HEIGHT) / 4 * 3),
               'rotate': True}]

    for title in titles:
        w, h = font_title.getsize(title['text'])

        if not title['rotate']:
            x = int(title['x'] - w / 2)
            y = int(title['y'] - h / 2)

            black_layer_draw.text((x, y), title['text'], font=font_title)
        else:
            temp_img = Image.new('1', (w, w), 1)
            temp_draw = ImageDraw.Draw(temp_img)

            temp_draw.text((0, w / 2 - h / 2), title['text'], font=font_title)

            temp_img = temp_img.rotate(90) if even_day else temp_img.rotate(-90)

            x = int(title['x'] - w / 2)
            y = int(title['y'] - w / 2)

            black_layer.paste(temp_img, (x, y))

    cards = [{'data': urgent_important,
              'x': (HEADER_HEIGHT + 2) if even_day else 0,
              'y': (HEADER_HEIGHT + 2) if even_day else 0},
             {'data': not_urgent_important,
              'x': (HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2 + 2) if even_day else ((EPD_WIDTH - HEADER_HEIGHT) / 2),
              'y': (HEADER_HEIGHT + 2) if even_day else 0},
             {'data': urgent_not_important,
              'x': (HEADER_HEIGHT + 2) if even_day else 0,
              'y': (HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2 + 2) if even_day else ((EPD_HEIGHT - HEADER_HEIGHT) / 2 + 2)},
             {'data': not_urgent_not_important,
              'x': (HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2 + 2) if even_day else ((EPD_WIDTH - HEADER_HEIGHT) / 2),
              'y': (HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2 + 2) if even_day else ((EPD_HEIGHT - HEADER_HEIGHT) / 2 + 2)}]

    for card in cards:
        red_card_layer, black_card_layer = quadrant_card(
            card['data'],
            (EPD_WIDTH - HEADER_HEIGHT) / 2 - 2,
            (EPD_HEIGHT - HEADER_HEIGHT) / 2 - 4)

        red_layer.paste(red_card_layer, (int(card['x']), int(card['y'])))
        black_layer.paste(black_card_layer, (int(card['x']), int(card['y'])))

    if even_day:
        black_layer_draw.line((0, HEADER_HEIGHT, EPD_WIDTH, HEADER_HEIGHT), 0, 2)
        black_layer_draw.line((HEADER_HEIGHT, 0, HEADER_HEIGHT, EPD_HEIGHT), 0, 2)
        black_layer_draw.line((0, HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2, EPD_WIDTH, HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2), 0, 2)
        black_layer_draw.line((HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2, 0, HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2, EPD_HEIGHT), 0, 2)
    else:
        black_layer_draw.line((0, EPD_HEIGHT - HEADER_HEIGHT, EPD_WIDTH, EPD_HEIGHT - HEADER_HEIGHT), 0, 2)
        black_layer_draw.line((EPD_WIDTH - HEADER_HEIGHT - 2, 0, EPD_WIDTH - HEADER_HEIGHT - 2, EPD_HEIGHT), 0, 2)
        black_layer_draw.line((0, (EPD_HEIGHT - HEADER_HEIGHT) / 2, EPD_WIDTH, (EPD_HEIGHT - HEADER_HEIGHT) / 2), 0, 2)
        black_layer_draw.line(((EPD_WIDTH - HEADER_HEIGHT) / 2 - 2, 0, (EPD_WIDTH - HEADER_HEIGHT) / 2 - 2, EPD_HEIGHT), 0, 2)

    return red_layer, black_layer


def server():
    even_day = (NOW.day % 2 == 0)

    red_layer, black_layer = four_quadrants(even_day)

    black_layer_draw = ImageDraw.Draw(black_layer)

    font_status = ImageFont.truetype('fonts/Roboto-Light.ttf', 16)

    if even_day:
        black_layer_draw.text(
            (EPD_WIDTH - 220, EPD_HEIGHT - 20),
            'Updated: ' + NOW.strftime('%m/%d/%Y %H:%M:%S'),
            font=font_status
        )
    else:
        black_layer_draw.text(
            (EPD_WIDTH - 250, EPD_HEIGHT - 50),
            'Updated: ' + NOW.strftime('%m/%d/%Y %H:%M:%S'),
            font=font_status
        )

    black_layer.save('black.bmp')
    red_layer.save('red.bmp')

    return red_layer, black_layer


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('python3 four_quadrants.py [server [debug]] [client [clear]]')

    if len(sys.argv) >= 2:
        if 'server' in sys.argv:
            red_image, black_image = server()

            if 'debug' in sys.argv:
                debug(red_image, black_image)

        if 'client' in sys.argv:
            if 'clear' in sys.argv:
                client(clear=True)
            else:
                client(clear=False)
