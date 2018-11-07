# encoding: UTF-8

# AUTHOR:李来佳
# WeChat/QQ: 28888502
# 广东华富资产管理

from vnpy.trader.app.ctaStrategy.ctaLineBar import *

class ExportStrategy(object):

    def __init__(self):

        self.minDiff = 0.01
        self.shortSymbol = 'ETH'
        self.vtSymbol = 'eth_usdt'
        self.bar_freq = 1
        
        self.lineM5 = None
        self.lineM15 = None       
        self.lineH1 = None
        self.lineD = None


        self.save_m5_bars = []
        self.save_m15_bars = []
        self.save_h1_bars = []        
        self.save_d_bars = []
    

    def createLineM5(self):
        # 创建5分钟K线
        lineM5Setting = {}
        lineM5Setting['name'] = u'M5'
        lineM5Setting['period'] = PERIOD_MINUTE
        lineM5Setting['barTimeInterval'] = 5
        lineM5Setting['inputBollLen'] = 26
        lineM5Setting['inputSkd'] = True
        lineM5Setting['mode'] = CtaLineBar.TICK_MODE
        lineM5Setting['minDiff'] = self.minDiff
        lineM5Setting['shortSymbol'] = self.shortSymbol
        lineM5Setting['is_7x24'] = True
        self.lineM5 = CtaMinuteBar(self, self.onBarM5, lineM5Setting)

    def createLineM15(self):
        # 创建M15 K线
        lineM15Setting = {}
        lineM15Setting['name'] = u'M15'
        lineM15Setting['period'] = PERIOD_MINUTE
        lineM15Setting['barTimeInterval'] = 15
        lineM15Setting['inputBollLen'] = 26
        lineM15Setting['inputSkd'] = True
        lineM15Setting['mode'] = CtaLineBar.TICK_MODE
        lineM15Setting['minDiff'] = self.minDiff
        lineM15Setting['shortSymbol'] = self.shortSymbol
        lineM15Setting['is_7x24'] = True
        self.lineM15 = CtaMinuteBar(self, self.onBarM15, lineM15Setting)

    def createLineH1(self):
        # 创建1小时K线
        lineH1Setting = {}
        lineH1Setting['name'] = u'H1'
        lineH1Setting['period'] = PERIOD_HOUR
        lineH1Setting['barTimeInterval'] = 1
        lineH1Setting['inputBollLen'] = 26       
        lineH1Setting['inputSkd'] = True
        lineH1Setting['mode'] = CtaLineBar.TICK_MODE
        lineH1Setting['minDiff'] = self.minDiff
        lineH1Setting['shortSymbol'] = self.shortSymbol
        lineH1Setting['is_7x24'] = True
        self.lineH1 = CtaHourBar(self, self.onBarH1, lineH1Setting)

    def createLineD(self):
        # 创建的日K线
        lineDaySetting = {}
        lineDaySetting['name'] = u'D1'
        lineDaySetting['barTimeInterval'] = 1
        lineDaySetting['inputPreLen'] = 5
        lineDaySetting['inputBollLen'] = 26
        lineDaySetting['inputSkd'] = True
        lineDaySetting['mode'] = CtaDayBar.TICK_MODE
        lineDaySetting['minDiff'] = self.minDiff
        lineDaySetting['shortSymbol'] = self.shortSymbol
        lineDaySetting['is_7x24'] = True
        self.lineD = CtaDayBar(self, self.onBarD, lineDaySetting)

    def onBar(self, bar):
        #print(u'tradingDay:{},dt:{},o:{},h:{},l:{},c:{},v:{}'.format(bar.tradingDay,bar.datetime, bar.open, bar.high, bar.low, bar.close, bar.volume))
        if self.lineD:
            self.lineD.addBar(bar, bar_freq=self.bar_freq)
        if self.lineH1:
            self.lineH1.addBar(bar, bar_freq=self.bar_freq)
        if self.lineM15:
            self.lineM15.addBar(bar, bar_freq=self.bar_freq)
        if self.lineM5:
            self.lineM5.addBar(bar, bar_freq=self.bar_freq)

    def onBarM5(self, bar):
        self.writeCtaLog(self.lineM5.displayLastBar())

        if len(self.lineM5.lineUpperBand)>0:
            self.save_m5_bars.append({
            'datetime': bar.datetime,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'turnover':0,
            'volume': bar.volume,
            'openInterest': 0,
            'upper': self.lineM5.lineUpperBand[-1] ,
            'middle': self.lineM5.lineMiddleBand[-1] ,
            'lower': self.lineM5.lineLowerBand[-1] ,
            'sk': self.lineM5.lineSK[-1] if len(self.lineM5.lineSK) > 0 else 0,
            'sd': self.lineM5.lineSD[-1] if len(self.lineM5.lineSD) > 0 else 0
        })

    def onBarM15(self, bar):
        self.writeCtaLog(self.lineM15.displayLastBar())
        if len(self.lineM15.lineUpperBand) > 0:
            self.save_m15_bars.append({
                'datetime': bar.datetime,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'turnover':0,
                'volume': bar.volume,
                'openInterest': 0,
                'upper': self.lineM15.lineUpperBand[-1],
                'middle': self.lineM15.lineMiddleBand[-1] ,
                'lower': self.lineM15.lineLowerBand[-1] ,
                'sk': self.lineM15.lineSK[-1] if len(self.lineM15.lineSK) > 0 else 0,
                'sd': self.lineM15.lineSD[-1] if len(self.lineM15.lineSD) > 0 else 0
            })

    def onBarH1(self, bar):
        self.writeCtaLog(self.lineH1.displayLastBar())
        if len(self.lineH1.lineUpperBand) > 0:
            self.save_h1_bars.append({
                'datetime': bar.datetime,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'turnover':0,
                'volume': bar.volume,
                'openInterest': 0,
                'upper': self.lineH1.lineUpperBand[-1] ,
                'middle': self.lineH1.lineMiddleBand[-1],
                'lower': self.lineH1.lineLowerBand[-1],
                'sk': self.lineH1.lineSK[-1] if len(self.lineH1.lineSK) > 0 else 0,
                'sd': self.lineH1.lineSD[-1] if len(self.lineH1.lineSD) > 0 else 0
            })


    def onBarD(self, bar):
        self.writeCtaLog(self.lineD.displayLastBar())
        if len(self.lineD.lineUpperBand) > 0:
            self.save_d_bars.append({
                'datetime': bar.datetime,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'turnover': 0,
                'volume': bar.volume,
                'openInterest': 0,
                'upper': self.lineD.lineUpperBand[-1] ,
                'middle': self.lineD.lineMiddleBand[-1],
                'lower': self.lineD.lineLowerBand[-1] ,
                'sk': self.lineD.lineSK[-1] if len(self.lineD.lineSK) > 0 else 0,
                'sd': self.lineD.lineSD[-1] if len(self.lineD.lineSD) > 0 else 0
                })

    def onTick(self, tick):
        print(u'{0},{1},ap:{2},av:{3},bp:{4},bv:{5}'.format(tick.datetime, tick.lastPrice, tick.askPrice1, tick.askVolume1, tick.bidPrice1, tick.bidVolume1))

    def writeCtaLog(self, content):
        print(content)

    def saveData(self):

        if len(self.save_m5_bars) > 0:
            outputFile = 'data/{}_M5.csv'.format(self.vtSymbol)
            with open(outputFile, 'w', encoding='utf8', newline='') as f:
                fieldnames = ['datetime', 'open', 'price', 'high','low','close','turnover','volume','openInterest','upper','middle','lower','sk','sd']
                writer = csv.DictWriter(f=f, fieldnames=fieldnames, dialect='excel')
                writer.writeheader()
                for row in self.save_m5_bars:
                    writer.writerow(row)

        if len(self.save_m15_bars) > 0:
            outputFile = 'data/{}_M15.csv'.format(self.vtSymbol)
            with open(outputFile, 'w', encoding='utf8', newline='') as f:
                fieldnames = ['datetime', 'open', 'price', 'high','low','close','turnover','volume','openInterest','upper','middle','lower','sk','sd']
                writer = csv.DictWriter(f=f, fieldnames=fieldnames, dialect='excel')
                writer.writeheader()
                for row in self.save_m15_bars:
                    writer.writerow(row)

        if len(self.save_h1_bars) > 0:
            outputFile = 'data/{}_H1.csv'.format(self.vtSymbol)
            with open(outputFile, 'w', encoding='utf8', newline='') as f:
                fieldnames = ['datetime', 'open', 'price', 'high','low','close','turnover','volume','openInterest','upper','middle','lower','sk','sd']
                writer = csv.DictWriter(f=f, fieldnames=fieldnames, dialect='excel')
                writer.writeheader()
                for row in self.save_h1_bars:
                    writer.writerow(row)

        if len(self.save_d_bars) > 0:
            outputFile = 'data/{}_D.csv'.format(self.vtSymbol)
            with open(outputFile, 'w', encoding='utf8', newline='') as f:
                fieldnames = ['datetime', 'open', 'price', 'high','low','close','turnover','volume','openInterest','upper','middle','lower', 'sk','sd']
                writer = csv.DictWriter(f=f, fieldnames=fieldnames, dialect='excel')
                writer.writeheader()
                for row in self.save_d_bars:
                    writer.writerow(row)

if __name__ == '__main__':

    t = ExportStrategy()
    t.shortSymbol = 'eth_usdt'
    t.vtSymbol = 'eth_usdt'
    t.bar_freq = 1
    t.minDiff = 0.00000001

    # 回测M5线
    t.createLineM5()

    # 回测M15线
    t.createLineM15()

    # 回测1小时线
    t.createLineH1()

    # 回测日线
    t.createLineD()

    #filename = 'data/btc_usd_min5.csv'
    filename = 'data/okex_eth_usdt_20180101_20180808_1min.csv'
    barTimeInterval = 60        # 60秒*5
    minDiff = 0.00000001       #回测数据的最小跳动

    def pickPrice(price, minDiff):
        return int(price / minDiff) * minDiff

    import csv
    csvfile = open(filename,'r',encoding='utf8')
    reader = csv.DictReader((line.replace('\0', '') for line in csvfile), delimiter=",")
    last_tradingDay = None
    for row in reader:
        try:
            bar = CtaBarData()
            bar.symbol = t.vtSymbol
            bar.vtSymbol = t.vtSymbol

            bar.open = pickPrice(float(row['open']), minDiff)
            bar.high = pickPrice(float(row['high']), minDiff)
            bar.low = pickPrice(float(row['low']), minDiff)
            bar.close = pickPrice(float(row['close']), minDiff)

            bar.volume = float(row['volume'])
            barEndTime = datetime.strptime(row['index'], '%Y-%m-%d %H:%M:%S')

            # 使用Bar的开始时间作为datetime
            bar.datetime = barEndTime

            bar.date = bar.datetime.strftime('%Y-%m-%d')
            bar.time = bar.datetime.strftime('%H:%M:%S')
            if 'trading_date' in row:
                bar.tradingDay = row['trading_date']
            else:
                bar.tradingDay = bar.date

            t.onBar(bar)

        except Exception as ex:
            t.writeCtaLog(u'{0}:{1}'.format(Exception, ex))
            traceback.print_exc()
            break

    t.saveData()