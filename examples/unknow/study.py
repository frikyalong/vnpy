# CTP账户数据写入CSV的完善

def onRspQryTradingAccount(self, data, error, n, last):
    # 最后面加上
    recording = True
    # 周六周日不写入数据
    if datetime.today().weekday() == 5 or datetime.today().weekday() == 6:
        recording = False
    if recording:
        # 通过CTP接口查询账户资金
        vnTrader_dir = 'C:\\ProgramData\\Anaconda3\\Lib\\site-packages\\vnpy-1.9.0-py3.6.egg\\vnpy\\trader\\app\\ctaStrategy\\AccountInfo'  # AccountInfo 所在路径
        # 文件名称设置为今天名称,每天只写入一次
        path = vnTrader_dir + '\\CTPAccount' + '.csv'
        if not os.path.exists(path):  # 如果文件不存在，需要写header
            with open(path, 'w', newline="") as f:  # newline=""不自动换行
                w = csv.DictWriter(f, data.keys())
                w.writeheader()
                w.writerow(data)

        else:  # 文件存在，不需要写header
            with open(path, 'a', newline="") as f:  # a二进制追加形式写入
                if datetime.now().hour % 2 == 0 and datetime.now().minute == 0 and datetime.now().second == 0:  # 两小时记录一次
                    w = csv.DictWriter(f, data.keys())
                    w.writerow(data)