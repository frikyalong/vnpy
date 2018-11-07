import urllib
import json

class dingRobot():

    def __init__(self):
        self.url = "https://oapi.dingtalk.com/robot/send?access_token=637a6624701c9393e8d2056e59951f024cfdbb5042c89dcf8fb4fcd489c7c4d5"

    def request(self, url, method, data=None, head={}):
        request = urllib.Request(url=url, headers=head)
        request.get_method = lambda: method
        httpRes = urllib.urlopen(request, data)
        content = httpRes.read()
        httpRes.close()
        return content

    def postStart(self, infoContent):
        data = {}
        data['msgtype'] = 'markdown'
        data['markdown'] = {}
        data['markdown']['title'] = '监控信息'
        data['markdown']['text'] = infoContent
        data = json.dumps(data)
        head = {"Content-Type": "application/json"}
        content = self.request(self.url, "POST", data, head)
        return content
