from PIL import Image, ImageDraw, ImageFont
import datetime
import requests
import config
from google.oauth2 import service_account
import googleapiclient.discovery
import sys
import pickle
from eink import debug, client, weather_card
import os
from google.auth.transport.requests import Request


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

    for name, cal in config.GOOGLE_CALENDARID_WITH_SERVICE_ACCOUNT.items():
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

    for name, cal in config.GOOGLE_CALENDARID_WITH_CREDENTIALS.items():
        creds = None

        pickle_name = name + '.pickle'

        if os.path.exists(pickle_name):
            with open(pickle_name, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

                with open(pickle_name, 'wb') as token:
                    pickle.dump(creds, token)

            else:
                item = {
                    'left': 'Alert',
                    'left_red': True,
                    'main': '!!! {} needs to be authenticated !!!'.format(name),
                    'main_red': True,
                    'right': '',
                    'right_red': False
                }

                urgent_important.append(item)

                continue

        calendar_service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)

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
            'left': '[{:02d}:{:02d}-{:02d}:{:02d}]'.format(start.hour, start.minute, end.hour, end.minute),
            'left_red': True if start <= (NOW + datetime.timedelta(hours=3)) else False,
            'main': event['summary'] if NOW < start else '>>> {} <<<'.format(event['summary']),
            'main_red': True if NOW >= start else False,
            'right': '[{}]'.format(event['cal']),
            'right_red': False
        }

        if event['cal'] in config.GOOGLE_IMPORTANT_CALENDARS:  # Important
            if start <= (NOW + datetime.timedelta(hours=8)):  # Urgent
                urgent_important.append(item)

            else:  # Not Urgent
                not_urgent_important.append(item)

        else:
            if start <= (NOW + datetime.timedelta(hours=8)):  # Urgent
                urgent_not_important.append(item)

            else:  # Not Urgent
                not_urgent_not_important.append(item)


def google_events_simple():
    results = []

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    credentials = service_account.Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    calendar_service = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)

    events = []

    for name, cal in config.GOOGLE_CALENDARID_WITH_SERVICE_ACCOUNT.items():
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

    for name, cal in config.GOOGLE_CALENDARID_WITH_CREDENTIALS.items():
        creds = None

        pickle_name = name + '.pickle'

        if os.path.exists(pickle_name):
            with open(pickle_name, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

                with open(pickle_name, 'wb') as token:
                    pickle.dump(creds, token)

            else:
                item = {
                    'left': '',
                    'left_red': False,
                    'main': '!!! {} needs to be authenticated !!!'.format(name),
                    'main_red': True,
                    'right': '',
                    'right_red': False
                }

                results.append(item)

                continue

        calendar_service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)

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

        results.append({
            'left': '[{:02d}:{:02d}]'.format(start.hour, start.minute) if start > NOW else '',
            'left_red': True if start <= (NOW + datetime.timedelta(hours=3)) else False,
            'main': event['summary'],
            'main_red': True if NOW >= start else False,
            'right': '[{:02d}:{:02d}]'.format(end.hour, end.minute) if start <= NOW else '',
            'right_red': True
        })

    return results


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
        'https://api.todoist.com/rest/v1/sections',
        headers={'Authorization': config.TODOIST_TOKEN}).json()

    for section in data:
        projects[section['id']] = section

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

            task['parents'] = []

            project_id = task['project_id']
            project_title = projects[project_id]['name']

            task['parents'].append([project_id, project_title])

            # if 'parent' in task:
            #     project_id = task['parent']
            #
            #     if 'name' in projects[project_id]:
            #         project_title = projects[project_id]['name']
            #     else:
            #         project_title = projects[project_id]['content']
            #
            #     task['parents'].append([project_id, project_title])
            #
            # elif task['section_id'] != 0:
            #     project_id = task['section_id']
            #     project_title = projects[project_id]['name']
            #
            #     task['parents'].append([project_id, project_title])
            #
            # else:
            #     project_id = task['project_id']
            #     project_title = projects[project_id]['name']
            #
            #     task['parents'].append([project_id, project_title])

            # if 'parent' in projects[project_id]:
            #     project_id = projects[project_id]['parent']
            #     project_title = projects[project_id]['name']
            #
            #     task['parents'].append([project_id, project_title])
            #
            # elif 'section_id' in projects[project_id] and projects[project_id]['section_id'] != 0:
            #     project_id = projects[project_id]['section_id']
            #     project_title = projects[project_id]['name']
            #
            #     task['parents'].append([project_id, project_title])
            #
            # elif 'project_id' in projects[project_id]:
            #     project_id = projects[project_id]['project_id']
            #     project_title = projects[project_id]['name']
            #
            #     task['parents'].append([project_id, project_title])

            if len(task['parents']) == 2:
                task['project'] = '{} > {}'.format(task['parents'][1][1], task['parents'][0][1])
            else:
                task['project'] = task['parents'][0][1]

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
    weather_today = weather_data['daily'][0]
    weather_tomorrow = weather_data['daily'][1]

    not_urgent_not_important.append({
        'left': '[Now]',
        'left_red': True,
        'main': weather_current['weather'][0]['description'].title(),
        'main_red': False,
        'main_x': 100,
        'right': '{} °F / {} °F'.format(round(weather_current['feels_like']), round(weather_current['temp'])),
        'right_red': False
    })

    not_urgent_not_important.append({
        'left': '[Today]',
        'left_red': True,
        'main': weather_today['weather'][0]['description'].title(),
        'main_red': False,
        'main_x': 100,
        'right': '{} °F / {} °F'.format(round(weather_today['temp']['min']), round(weather_today['temp']['max'])),
        'right_red': False
    })

    not_urgent_not_important.append({
        'left': '[Tomorrow]',
        'left_red': False,
        'main': weather_tomorrow['weather'][0]['description'].title(),
        'main_red': False,
        'main_x': 100,
        'right': '{} °F / {} °F'.format(round(weather_tomorrow['temp']['min']), round(weather_tomorrow['temp']['max'])),
        'right_red': False
    })


def weather_simple(width, height):
    red_layer = Image.new('1', (width, height), 1)
    black_layer = Image.new('1', (width, height), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    weather_data = requests.get(
        'https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&units=imperial&appid={}'.format(
            WEATHER_LAT,
            WEATHER_LON,
            config.OPENWEATHERMAP_APPID
        )).json()

    weather_current = weather_data['current']

    red_card_layer, black_card_layer = weather_card(
        weather_current['weather'][0]['icon'],
        weather_current['weather'][0]['main'],
        '{} °F / {} °F'.format(round(weather_current['feels_like']), round(weather_current['temp'])),
        'Now: ' + weather_current['weather'][0]['description'].title(),
        width=width,
        height=int(height / 2)
    )

    red_layer.paste(red_card_layer, (0, 0))
    black_layer.paste(black_card_layer, (0, 0))

    if NOW.hour < 19:
        weather_today = weather_data['daily'][0]

        red_card_layer, black_card_layer = weather_card(
            weather_today['weather'][0]['icon'],
            weather_today['weather'][0]['main'],
            '{} °F / {} °F'.format(round(weather_today['temp']['min']), round(weather_today['temp']['max'])),
            'Today: ' + weather_today['weather'][0]['description'].title(),
            width=width,
            height=int(height / 2)
        )

    else:
        weather_tomorrow = weather_data['daily'][1]

        red_card_layer, black_card_layer = weather_card(
            weather_tomorrow['weather'][0]['icon'],
            weather_tomorrow['weather'][0]['main'],
            '{} °F / {} °F'.format(round(weather_tomorrow['temp']['min']), round(weather_tomorrow['temp']['max'])),
            'Tomorrow: ' + weather_tomorrow['weather'][0]['description'].title(),
            width=width,
            height=int(height / 2)
        )

    red_layer.paste(red_card_layer, (0, int(height / 2)))
    black_layer.paste(black_card_layer, (0, int(height / 2)))

    return red_layer, black_layer


def habitica(urgent_not_important):
    data = requests.get(
        'https://habitica.com/api/v3/tasks/user',
        headers={'x-api-user': config.HABITICA_USERID, 'x-api-key': config.HABITICA_TOKEN}).json()['data']

    for item in data:
        if item['type'] != 'daily' or not item['isDue'] or item['completed']:
            continue

        urgent_not_important.append({
            'left': NOW.strftime('%b %m'),
            'left_red': False,
            'main': item['text'],
            'main_red': False,
            'right': '[Habitica]',
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

        mw, h = font.getsize(item['main'])
        y = h / 2 + h_offset

        lw, _ = font.getsize(item['left'])
        lx = 0

        rw, _ = font.getsize(item['right'])
        rx = width - rw

        while width - lw - rw - 10 < mw:
            item['main'] = item['main'][:-4] + '...'
            mw, _ = font.getsize(item['main'])

        if 'main_x' not in item:
            if lw > 0:
                mx = lw + 5
            else:
                mx = 0
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

        # if h_offset + 2 * h >= height and len(items) - count > 1:
        #     text = 'And {} more ......'.format(len(items) - count)
        #
        #     w, h = font.getsize(text)
        #     x = width / 2 - w / 2
        #     y = h / 2 + h_offset
        #
        #     red_layer_draw.text((x, y), text, font=font, fill=0)

        if h_offset + h >= height:
            break

    return red_layer, black_layer, items[count:]


def four_quadrants(even_day=True, width=EPD_WIDTH, height=EPD_HEIGHT, header_h=HEADER_HEIGHT):
    urgent_important = []
    urgent_not_important = []
    not_urgent_important = []
    not_urgent_not_important = []

    # google_events(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important)
    todo_tasks(urgent_important, not_urgent_important, urgent_not_important, not_urgent_not_important)
    habitica(urgent_not_important)
    # weather(not_urgent_not_important)

    red_layer = Image.new('1', (EPD_WIDTH, height), 1)
    black_layer = Image.new('1', (EPD_WIDTH, height), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    font_title = ImageFont.truetype('fonts/Roboto-Regular.ttf', 20)

    titles = [{'text': 'Urgent',
               'x': ((width - header_h) / 4 + header_h) if even_day else ((width - header_h) / 4),
               'y': (header_h / 2) if even_day else (height - (header_h / 2)),
               'rotate': False},
              {'text': 'Not Urgent',
               'x': ((width - header_h) / 4 * 3 + header_h) if even_day else ((width - header_h) / 4 * 3),
               'y': (header_h / 2) if even_day else (height - (header_h / 2)),
               'rotate': False},
              {'text': 'Important',
               'x': (header_h / 2) if even_day else (width - header_h / 2),
               'y': ((height - header_h) / 4 + header_h) if even_day else ((height - header_h) / 4),
               'rotate': True},
              {'text': 'Not Important',
               'x': (header_h / 2) if even_day else (width - header_h / 2),
               'y': ((height - header_h) / 4 * 3 + header_h) if even_day else ((height - header_h) / 4 * 3),
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
              'x': (header_h + 2) if even_day else 0,
              'y': (header_h + 2) if even_day else 0,
              'accept_left': False},
             {'data': urgent_not_important,
              'x': (header_h + 2) if even_day else 0,
              'y': (header_h + (height - header_h) / 2 + 2) if even_day else ((height - header_h) / 2 + 2),
              'accept_left': True},
             {'data': not_urgent_important,
              'x': (header_h + (width - header_h) / 2 + 2) if even_day else ((width - header_h) / 2),
              'y': (header_h + 2) if even_day else 0,
              'accept_left': False},
             {'data': not_urgent_not_important,
              'x': (header_h + (width - header_h) / 2 + 2) if even_day else ((width - header_h) / 2),
              'y': (header_h + (height - header_h) / 2 + 2) if even_day else ((height - header_h) / 2 + 2),
              'accept_left': True}]

    tasks_left = []

    for card in cards:
        if not card['accept_left']:
            tasks_left = []

        red_card_layer, black_card_layer, tasks_left = quadrant_card(
            tasks_left + card['data'],
            (width - header_h) / 2 - 2,
            (height - header_h) / 2 - 4)

        red_layer.paste(red_card_layer, (int(card['x']), int(card['y'])))
        black_layer.paste(black_card_layer, (int(card['x']), int(card['y'])))

    if even_day:
        black_layer_draw.line((0, header_h, width, header_h), 0, 2)
        black_layer_draw.line((header_h, 0, header_h, height), 0, 2)
        black_layer_draw.line((0, header_h + (height - header_h) / 2, width, header_h + (height - header_h) / 2), 0, 2)
        black_layer_draw.line((header_h + (width - header_h) / 2, 0, header_h + (width - header_h) / 2, height), 0, 2)
    else:
        black_layer_draw.line((0, height - header_h, width, height - header_h), 0, 2)
        black_layer_draw.line((width - header_h - 2, 0, width - header_h - 2, height), 0, 2)
        black_layer_draw.line((0, (height - header_h) / 2, width, (height - header_h) / 2), 0, 2)
        black_layer_draw.line(((width - header_h) / 2 - 2, 0, (width - header_h) / 2 - 2, height), 0, 2)

    return red_layer, black_layer


def today_calendar(width=200, height=EPD_HEIGHT):
    red_layer = Image.new('1', (width, height), 1)
    black_layer = Image.new('1', (width, height), 1)

    red_layer_draw = ImageDraw.Draw(red_layer)
    black_layer_draw = ImageDraw.Draw(black_layer)

    black_layer_draw.rectangle((0, 0, width, height), fill=0)

    week_day_name = NOW.strftime("%A")
    day_number = NOW.strftime("%d")
    month_year_str = NOW.strftime("%b") + ' ' + NOW.strftime("%Y")

    font_week_day_name = ImageFont.truetype('fonts/Roboto-Regular.ttf', 30)
    font_day_number = ImageFont.truetype('fonts/Roboto-Black.ttf', 90)
    font_month_year_str = ImageFont.truetype('fonts/Roboto-Regular.ttf', 30)
    font_status = ImageFont.truetype('fonts/Roboto-Light.ttf', 16)

    w_week_day_name, h_week_day_name = font_week_day_name.getsize(week_day_name)
    x_week_day_name = (width / 2) - (w_week_day_name / 2)

    w_day_number, h_day_number = font_day_number.getsize(day_number)
    x_day_number = (width / 2) - (w_day_number / 2)

    w_month_year_str, h_month_year_str = font_month_year_str.getsize(month_year_str)
    x_month_year_str = (width / 2) - (w_month_year_str / 2)

    black_layer_draw.text((x_week_day_name, 5), week_day_name, font=font_week_day_name, fill=255)
    black_layer_draw.text((x_day_number, 20), day_number, font=font_day_number, fill=255)
    red_layer_draw.text((x_day_number, 20), day_number, font=font_day_number, fill=0)
    black_layer_draw.text((x_month_year_str, 100), month_year_str, font=font_month_year_str, fill=255)

    events = google_events_simple()

    red_card, black_card, _ = quadrant_card(events, width, 145)

    red_layer.paste(red_card, (0, 140))
    black_layer.paste(black_card, (0, 140))

    red_card, black_card = weather_simple(width, 170)

    red_layer.paste(red_card, (0, 287))
    black_layer.paste(black_card, (0, 287))

    status_text = 'Updated: ' + NOW.strftime('%H:%M:%S')
    w_status, h_status = font_status.getsize(status_text)

    black_layer_draw.text(
        (width / 2 - w_status / 2, height - 20),
        status_text,
        font=font_status, fill=255)

    return red_layer, black_layer


def server():
    red_layer = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
    black_layer = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)

    black_draw = ImageDraw.Draw(black_layer)

    even_day = (NOW.day % 2 == 0)

    red_card_layer, black_card_layer = four_quadrants(even_day, width=EPD_WIDTH - 182)

    red_calendar_card, black_calendar_card = today_calendar(180)

    if even_day:
        red_layer.paste(red_card_layer, (0, 0))
        black_layer.paste(black_card_layer, (0, 0))

        red_layer.paste(red_calendar_card, (EPD_WIDTH - 180, 0))
        black_layer.paste(black_calendar_card, (EPD_WIDTH - 180, 0))

        black_draw.line((EPD_WIDTH - 182, 0, EPD_WIDTH - 182, EPD_HEIGHT), 0, 2)

    else:
        red_layer.paste(red_calendar_card, (0, 0))
        black_layer.paste(black_calendar_card, (0, 0))

        red_layer.paste(red_card_layer, (182, 0))
        black_layer.paste(black_card_layer, (182, 0))

        black_draw.line((180, 0, 180, EPD_HEIGHT), 0, 2)

    black_layer.save('black.bmp')
    red_layer.save('red.bmp')

    return red_layer, black_layer


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('python3 four_quadrants.py [server [debug]] [client [clear]]')

    else:
        if 'server' in sys.argv:
            red_image, black_image = server()

            if 'debug' in sys.argv:
                debug(red_image, black_image)

        if 'client' in sys.argv:
            if 'clear' in sys.argv:
                client(clear=True)
            else:
                client(clear=False)
