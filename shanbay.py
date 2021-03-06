#!/usr/bin/env python
# coding: utf-8

import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import urllib
import urllib2
import json
import time
import argparse
from urlparse import urlparse
import subprocess

from alfred.feedback import Feedback


TOKEN_FILE = os.path.abspath('token')
ALFRED_WORD_AUDIO_MP3_FILE = '/tmp/alfred_word_audio.mp3'

CLIENT_ID = '7f652079ade6d4fa4eec'

SEARCH_API = 'https://api.shanbay.com/bdc/search/'
LEARNING_API = 'https://api.shanbay.com/bdc/learning/'
AUTHORIZE_API = 'https://api.shanbay.com/oauth2/authorize/'
REDIRECT_URL = 'https://api.shanbay.com/oauth2/auth/success/'
VOCABULARY_URL = 'https://www.shanbay.com/bdc/vocabulary/%d/'


def _request(path, params=None, method='GET', data=None, headers=None):
    params = params or {}
    headers = headers or {}
    if params:
        url = path + '?' + urllib.urlencode(params)
    else:
        url = path

    request = urllib2.Request(url, data, headers)
    request.get_method = lambda: method
    response = urllib2.urlopen(request)
    return response.read()


def _api(path, params=None, method='GET', data=None, headers=None):
    response = _request(path=path, params=params, method=method, data=data,
                        headers=headers)
    result = json.loads(response)
    if result['status_code'] != 0:
        return None
    return result['data']


def save_token(url):
    parse_result = urlparse(url)
    data = dict(map(lambda x: x.split('='), parse_result.fragment.split('&')))
    data['expires_in'] = int(data['expires_in'])
    data['timestamp'] = time.time()
    with(open(TOKEN_FILE, 'w')) as token_file:
        token_file.write(json.dumps(data))


def read_token():
    if not os.path.isfile(TOKEN_FILE):
        return False
    token_json = json.loads(open(TOKEN_FILE).read())
    if token_json['timestamp'] + token_json['expires_in'] < int(time.time()):
        return False
    return token_json['access_token']


def search(word):
    feedback = Feedback()
    data = _api(SEARCH_API, params={'word': word})
    if data is None:
        return

    word = data['content']
    pron = data['pron']
    title = "%s [%s]" % (word, pron)
    feedback.addItem(title=title, arg=word)
    for chinese in data['definition'].decode("utf-8").split('\n'):
        feedback.addItem(title=chinese, arg=word)

    if data.has_key('en_definitions') and data['en_definitions']:
        for type in data['en_definitions']:
            for line in data['en_definitions'][type]:
                title = type+', '+line
                if not title:
                    continue
                feedback.addItem(title = title, arg = word)
    feedback.output()


def token_url(url):
    if not url.startswith('%s#' % REDIRECT_URL):
        return
    save_token(url)
    print('Authorize successful')


def learning(word):
    access_token = read_token()
    if not access_token:
        return authorize()
    search_data = _api(SEARCH_API, params={'word': word})
    if search_data is None:
        return
    try:
        data = _api(LEARNING_API,
                    data=urllib.urlencode({'id': search_data['id']}),
                    headers={'Authorization': 'Bearer %s' % access_token},
                    method='POST')
    except urllib2.HTTPError, e:
        if e.code == 401:
            return authorize()
        else:
            print('"%s" Add Fail, e: %s' % (word, e))
    if data is None:
        print('"%s" Add Fail' % word)
        return
    print('"%s" Add Successful' % word)


def authorize():
    url = '%s?client_id=%s&response_type=token' % (AUTHORIZE_API, CLIENT_ID)
    os.system('open "%s"' % url)


def sound(word):
    data = _api(SEARCH_API, params={'word': word})
    if data is None:
        return
    audio_address = data['audio_addresses']['us'][0]
    with open(ALFRED_WORD_AUDIO_MP3_FILE, 'w') as f:
        f.write(_request(audio_address))
    subprocess.call(['/usr/bin/afplay', ALFRED_WORD_AUDIO_MP3_FILE])


def open_word(word):
    data = _api(SEARCH_API, params={'word': word})
    if data is None:
        return
    url = VOCABULARY_URL % data['id']
    os.system('open "%s"' % url)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--search', nargs='?', type=str)
    parser.add_argument('--learning', nargs='?')
    parser.add_argument('--tokenurl', nargs='?')
    parser.add_argument('--sound', nargs='?')
    parser.add_argument('--open', nargs='?')
    args = parser.parse_args()

    if args.search:
        search(args.search)
    elif args.learning:
        learning(args.learning)
    elif args.tokenurl:
        token_url(args.tokenurl)
    elif args.sound:
        sound(args.sound)
    elif args.open:
        open_word(args.open)
    else:
        pass


if __name__ == '__main__':
    main()
