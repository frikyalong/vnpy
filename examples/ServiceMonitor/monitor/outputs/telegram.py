import json

import requests

from .base import BaseOutput

BOT_TOKEN = "657938518:XXXXXXX"
BOT_URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
MY_CHAT_ID = 1234123123

class Telegram(BaseOutput):
    def get_default_options(self):
        return {
            "level": "INFO",
            "msg_type": "ALERT",
            "source_key": "input",
        }

    def __call__(self, event):
        if "source" in self.options:
            source = self.options["source"]
        elif "source_key" in self.options:
            key = self.options["source_key"]
            source = self.options[key]
        else:
            source = "XXX"

        content = self.render(event)
        url = BOT_URL + "sendMessage?text={}&chat_id={}".format(content, MY_CHAT_ID)
        resp = requests.get(url)


