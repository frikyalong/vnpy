

class dingRobot():

    def __init__(self):
        self.url = "https://oapi.dingtalk.com/robot/send?access_token=637a6624701c9393e8d2056e59951f024cfdbb5042c89dcf8fb4fcd489c7c4d5"

    def request(self, url, method, data=None, head={}):
        rq = requests.get(url=url, headers=head)
        httpRes = urllib.request.urlopen(rq, data)
        content = httpRes.read()
        httpRes.close()
        return content

    def postStart(self, infoContent):
        program = {
            "msgtype": "text",
            "text": {"content": infoContent},
        }
        headers = {'Content-Type': 'application/json'}
        f = requests.post(self.url, data=json.dumps(program), headers=headers)
