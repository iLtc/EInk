import pickle
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def main(account):
    creds = None

    pickle_name = account + '.pickle'

    if os.path.exists(pickle_name):
        with open(pickle_name, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

            print('Credentials have been refreshed!')

        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_console()

        with open(pickle_name, 'wb') as token:
            pickle.dump(creds, token)

            print('Credentials have been saved!')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('python3 google_account.py ACCOUNT_NAME')

    else:
        main(sys.argv[1])
