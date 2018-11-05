# -*- coding:utf-8 -*-
'''
发送Telegram的消息
'''

from threading import Lock,Thread
import requests
import json
import sys
import traceback
from urllib.parse import urlencode
from datetime import datetime

# 创建一个带附件的实例

global telegram_lock
telegram_lock = Lock()

BOT_TOKEN = "753918901:AAEEr4Pvmazp32XqI94TtOAsDrW6U_yXzgE"
BOT_URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
GROUP_CHAT_ID = -123123123
MY_CHAT_ID = 23456789

class telegram_thread(Thread):
    def __init__(self, chat_id,parse_mode,text):
        super(telegram_thread, self).__init__(name="telegram_thread")
        self.url = BOT_URL
        self.token = BOT_TOKEN
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.text = text
        self.lock = telegram_lock

    def run(self):
        if self.url is None or self.text is None:
            return
        params = {}
        params['chat_id'] = str(self.chat_id)
        if self.parse_mode is not None:
            params['parse_mode'] = self.parse_mode
        params['text'] = self.text

        url = self.url + 'sendMessage'

        # 发送请求
        try:
            response = requests.get(url,params=urlencode(params))
        except Exception as e:
            print("{} telegram sent failed! ex:{},trace:{}".format(datetime.now(),str(e),traceback.format_exc()),file=sys.stderr)
            return

        print("telegram sent successful!")

def sendTelegramMsg(chat_id=None, parse_mode=None, text = ''):
    """
    发送电报
    :param chat_id:  接收者ID,空值时，直接发发送给i-quant群组，列表时，就逐一发送
    :param parse_mode:  发送内容格式(普通文本，Markdown，html
    :param text:   发送内容

    :return:
    """
    if len(text) == 0:
        return
    chat_ids = []
    if chat_id is None:
        chat_ids.append(GROUP_CHAT_ID)
    if isinstance(chat_id,list):
        chat_ids.extend(chat_id)

    for c_id in chat_ids:
        t = telegram_thread(chat_id=c_id, parse_mode=parse_mode,text=text)
        t.daemon = False
        # t.run()
        t.start()

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates():
    url = BOT_URL + "getUpdates"
    js = get_json_from_url(url)
    return js

def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)

def send_message(text, chat_id):
    url = BOT_URL + "sendMessage?text={}&chat_id={}".format(text, chat_id)
    get_url(url)

if __name__ == '__main__':
    msgcontent = u'测试电报!!!!\n'

    # 发送给最后一次对话的人
    text,chat_id = get_last_chat_id_and_text(get_updates())
    #print('{},{}'.format(text, chat_id))
    #sendTelegramMsg(chat_id=chat_id,text=msgcontent)

    sendTelegramMsg(chat_id=MY_CHAT_ID,text=u'你好')
    # 发送给一个群组
    sendTelegramMsg(text=msgcontent)