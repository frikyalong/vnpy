# -*- coding:utf-8 -*-
'''
通过FTQQ发送Weixin的消息
http://sc.ftqq.com/3.version
'''

from threading import Lock,Thread
import urllib, requests
import json
import sys
import traceback
from urllib.parse import urlencode
from datetime import datetime

global wxft_lock
wxft_lock = Lock()


# 这里可以设置多个微信接受者的Token,列表方式添加就好
SEC_TOKENS = ['SCU38098Td00e41e93bfb0a9ff9968654a998e7625c1ef02297145']

class wxft_thread(Thread):
    def __init__(self,token, text, desp):

        # text：消息标题，最长为256，必填。
        # desp：消息内容，最长64Kb，可空，支持MarkDown。

        super(wxft_thread, self).__init__(name="wxft_thread")
        self.url = "https://sc.ftqq.com/{}.send".format(token)
        self.token = token
        self.text = text
        self.desp = desp
        self.lock = wxft_lock

    def run(self):
        if self.text is None or len(self.text)==0:
            return
        params = {}
        params['text'] = self.text
        params['desp'] = self.desp

        # 发送请求
        try:
            response = requests.get(self.url,params=urlencode(params))
        except Exception as e:
            print("{} wx_ft sent failed! ex:{},trace:{}".format(datetime.now(),str(e),traceback.format_exc()),file=sys.stderr)
            return

        print("wx_ft sent successful!")

def send_wx_msg(text = '',desp = ''):
    """
    发送微信Msg
    :param chat_id:  接收者ID,空值时，直接发发送给i-quant群组，列表时，就逐一发送
    :param parse_mode:  发送内容格式(普通文本，Markdown，html
    :param text:   发送内容

    :return:
    """
    if len(text) == 0:
        return

    for token in SEC_TOKENS:
        t = wxft_thread(token=token,text=text,desp=desp)
        t.daemon = False
        # t.run()
        t.start()


def send_wx_group_msg(text = '',desp = ''):
    """
    发送微信Msg
    :param chat_id:  接收者ID,空值时，直接发发送给i-quant群组，列表时，就逐一发送
    :param parse_mode:  发送内容格式(普通文本，Markdown，html
    :param text:   发送内容

    :return:
    """
    if len(text) == 0:
        return
    url = "https://pushbear.ftqq.com/sub"
    params = {}
    params['sendkey'] = "7578-d89410116dbc7810e7e44e4e7eace283"
    params['text'] = text
    params['desp'] = desp

    try:
        response = requests.get(url, params=urlencode(params))
    except Exception as e:
        print("{} wx_ft sent failed! ex:{},trace:{}".format(datetime.now(), str(e), traceback.format_exc()), file
              =sys.stderr)
        returnstrategsdfsdfsdfsdf

    print("wx_ft sent successful!")


def send_dingding_group_msg(text='', desp=''):
    if len(text) == 0:
        return
    url = "https://oapi.dingtalk.com/robot/send?access_token=637a6624701c9393e8d2056e59951f024cfdbb5042c89dcf8fb4fcd489c7c4d5"
    params = {}
    params['msgtype'] = text
    params['text'] = desp
    headers = {'Content-Type': 'application/json'}
    try:
        f = requests.post(url, data=json.dumps(program), headers=headers)
    except Exception as e:
        print("{} dingding sent failed! ex:{},trace:{}".format(datetime.now(), str(e), traceback.format_exc()), file
              =sys.stderr)
        return

    print("dingding sent successful!")


if __name__ == '__main__':
    text = u'wx message测试标题!!!!\n第二行'
    desp = u'测试备注\n第二行备注'

    send_wx_msg(text,desp)

    text = u'wx group message测试标题!!!!\n第二行'
    desp = u'测试备注\n第二行备注'

    send_wx_group_msg(text,desp)

    # text = u'dingding message测试标题!!!!\n第二行'
    # desp = u'测试备注\n第二行备注'

    send_dingding_group_msg(text,desp)
