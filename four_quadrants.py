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
            'left': '[{}] [{}]'.format('{:02d}:{:02d}-{:02d}:{:02d}'.format(start.hour, start.minute, end.hour, end.minute), event['cal']),
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
            task['inbox'] = True
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

    tasks.sort(key=lambda e: e['due']['date'])

    today = NOW.strftime('%Y-%m-%d')

    for task in tasks:
        item = {
            'left': '[Inbox]' if 'inbox' in task else task['due']['string'],
            'left_red': True if task['due']['date'] < today else False,
            'main': task['content'],
            'main_red': False,
            'right': '[{}]'.format(task['project']),
            'right_red': False
        }

        if task['priority'] > 1:  # Important
            if task['due']['date'] <= today:  # Urgent
                urgent_important.append(item)

            else:
                not_urgent_important.append(item)

        else:
            if task['due']['date'] <= today:  # Urgent
                urgent_not_important.append(item)

            else:
                not_urgent_not_important.append(item)


def quadrant_card(items, width, height):
    width = int(width)
    height = int(height)

    red_layer = Image.new('1', (width, height), 1)
    black_layer = Image.new('1', (width, height), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font = ImageFont.truetype('fonts/timr45w.ttf', 18)
    h_offset = -10

    if len(items) == 0:
        text = 'All down! Good job!'

        w, h = font.getsize(text)
        x = width / 2 - w / 2
        y = h / 2 + h_offset

        black_layer_draw.text((x, y), text, font=font, fill=0)

        h_offset += 31

        black_layer_draw.line((0, h_offset, width, h_offset), 0, 1)

        h_offset += -7

    count = 0

    for item in items:
        count += 1

        w, h = font.getsize(item['left'])
        x = 0
        y = h / 2 + h_offset

        if item['left_red']:
            red_layer_draw.text((x, y), item['left'], font=font, fill=0)
        else:
            black_layer_draw.text((x, y), item['left'], font=font, fill=0)

        w1, _ = font.getsize(item['main'])
        x = w + 10
        y = h / 2 + h_offset

        if item['main_red']:
            red_layer_draw.text((x, y), item['main'], font=font, fill=0)
        else:
            black_layer_draw.text((x, y), item['main'], font=font, fill=0)

        w, _ = font.getsize(item['right'])
        x = width - w
        y = h / 2 + h_offset

        if item['right_red']:
            red_layer_draw.text((x, y), item['right'], font=font, fill=0)
        else:
            black_layer_draw.text((x, y), item['right'], font=font, fill=0)

        h_offset += 31

        black_layer_draw.line((0, h_offset, width, h_offset), 0, 1)

        h_offset += -7

        if h_offset + 2 * h >= height and len(item) - count > 1:
            text = 'And {} more tasks or events for the next 3 days ......'.format(len(item) - count)

            w, h = font.getsize(text)
            x = width / 2 - w / 2
            y = h / 2 + h_offset

            red_layer_draw.text((x, y), text, font=font, fill=0)

            break

    return red_layer, black_layer


def four_quadrants():
    urgent_important = []
    urgent_not_important = []
    not_urgent_important = []
    not_urgent_not_important = []

    google_events(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important)
    todo_tasks(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important)

    red_layer = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
    black_layer = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font_title = ImageFont.truetype('fonts/Roboto-Regular.ttf', 20)

    titles = [{'text': 'Urgent',
               'x': (EPD_WIDTH - HEADER_HEIGHT) / 4 + HEADER_HEIGHT,
               'y': HEADER_HEIGHT / 2,
               'rotate': False},
              {'text': 'Not Urgent',
               'x': (EPD_WIDTH - HEADER_HEIGHT) / 4 * 3 + HEADER_HEIGHT,
               'y': HEADER_HEIGHT / 2,
               'rotate': False},
              {'text': 'Important',
               'x': HEADER_HEIGHT / 2,
               'y': (EPD_HEIGHT - HEADER_HEIGHT) / 4 + HEADER_HEIGHT,
               'rotate': True},
              {'text': 'Not Important',
               'x': HEADER_HEIGHT / 2,
               'y': (EPD_HEIGHT - HEADER_HEIGHT) / 4 * 3 + HEADER_HEIGHT,
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

            temp_img = temp_img.rotate(90)

            x = int(title['x'] - w / 2)
            y = int(title['y'] - w / 2)

            black_layer.paste(temp_img, (x, y))

    cards = [{'data': urgent_important,
              'x': HEADER_HEIGHT + 2,
              'y': HEADER_HEIGHT + 2},
             {'data': not_urgent_important,
              'x': HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2 + 2,
              'y': HEADER_HEIGHT + 2},
             {'data': urgent_not_important,
              'x': HEADER_HEIGHT + 2,
              'y': HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2 + 2},
             {'data': not_urgent_not_important,
              'x': HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2 + 2,
              'y': HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2 + 2}]

    for card in cards:
        red_card_layer, black_card_layer = quadrant_card(
            card['data'],
            (EPD_WIDTH - HEADER_HEIGHT) / 2 - 2,
            (EPD_HEIGHT - HEADER_HEIGHT) / 2 - 4)

        red_layer.paste(red_card_layer, (int(card['x']), int(card['y'])))
        black_layer.paste(black_card_layer, (int(card['x']), int(card['y'])))

    black_layer_draw.line((0, HEADER_HEIGHT, EPD_WIDTH, HEADER_HEIGHT), 0, 2)
    black_layer_draw.line((HEADER_HEIGHT, 0, HEADER_HEIGHT, EPD_HEIGHT), 0, 2)
    black_layer_draw.line((0, HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2, EPD_WIDTH, HEADER_HEIGHT + (EPD_HEIGHT - HEADER_HEIGHT) / 2), 0, 2)
    black_layer_draw.line((HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2, 0, HEADER_HEIGHT + (EPD_WIDTH - HEADER_HEIGHT) / 2, EPD_HEIGHT), 0, 2)

    return red_layer, black_layer


def server():
    red_layer, black_layer = four_quadrants()

    black_layer_draw = ImageDraw.Draw(black_layer)

    font_status = ImageFont.truetype('fonts/Roboto-Light.ttf', 16)
    black_layer_draw.text(
        (EPD_WIDTH - 220, EPD_HEIGHT - 20),
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
