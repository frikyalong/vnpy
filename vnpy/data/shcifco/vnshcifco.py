# encoding: UTF-8


from __future__ import print_function

from pymongo import MongoClient
from datetime import datetime, timedelta
import requests
from vnpy.trader.app.ctaStrategy.ctaBase import CtaBarData

HTTP_OK = 200

PERIOD_1MIN = '1m'
PERIOD_5MIN = '5m'
PERIOD_15MIN = '15m'
PERIOD_60MIN = '60m'
PERIOD_1DAY = '1d'


########################################################################
class ShcifcoApi(object):
    """数据接口"""

    #----------------------------------------------------------------------
    def __init__(self, ip, port, token):
        """Constructor"""
        self.ip = ip
        self.port = port
        self.token = token

        self.service = 'shcifco/dataapi'
        self.domain = 'http://' + ':'.join([self.ip, self.port])
    
    #----------------------------------------------------------------------
    def getData(self, path, params):
        """下载数据"""
        url = '/'.join([self.domain, self.service, path])
        params['token'] = self.token
        r = requests.get(url=url, params=params)
        
        if r.status_code != HTTP_OK:
            print(u'http请求失败，状态代码%s' %r.status_code)
            return None
        else:
            return r.text
    
    #----------------------------------------------------------------------
    def getLastTick(self, symbol):
        """获取最新Tick"""
        path = 'lasttick'
        params = {'ids': symbol}
        
        data = self.getData(path, params)
        if not data or data == ';':
            return None
        
        data = data.split(';')[0]
        l = data.split(',')
        d = {
            'symbol': l[1],
            'lastPrice': float(l[4]),
            'bidPrice': float(l[22]),
            'bidVolume': int(l[23]),
            'askPrice': float(l[24]),
            'askVolume': int(l[25]),
            'volume': int(l[11]),
            'openInterest': int(float(l[13]))
        }
        print(d)
        return d
    
    #----------------------------------------------------------------------
    def getLastPrice(self, symbol):
        """获取最新成交价"""
        path = 'lastprice'
        params = {'ids': symbol}
        
        data = self.getData(path, params)
        if not data:
            return None
        
        data = data.split(';')[0]
        price = float(data)
        return price
    
    #----------------------------------------------------------------------
    def getLastBar(self, symbol):
        """获取最新的一分钟K线数据"""
        path = 'lastbar'
        params = {'id': symbol}
        
        data = self.getData(path, params)
        if not data:
            return None
        
        data = data.split(';')[0]
        l = data.split(',')
        d = {
            'symbol': l[0],
            'time': l[1],
            'open': float(l[2]),
            'high': float(l[3]),
            'low': float(l[4]),
            'close': float(l[5]),
            'volume': int(l[6]),
            'openInterest': int(float(l[7]))
        }
        return d
    
    #----------------------------------------------------------------------
    def getHisBar(self, symbol, num, date='', period=''):
        """获取历史K线数据"""
        path = 'hisminbar'
        
        # 默认参数
        params = {
            'id': symbol,
            'num': num
        }
        # 可选参数
        if date:
            params['tradingday'] = date
        if period:
            params['period'] = period
        
        data = self.getData(path, params)
        if not data:
            return None
        
        barList = []        
        l = data.split(';')
        
        for barStr in l:
            # 过滤某些空数据
            if ',' not in barStr:
                continue
            
            barData = barStr.split(',')
            d = {
                'symbol': barData[0],
                # 'date': barData[1],   # trading day
                'tradingday': barData[1],
                'minute': barData[2],
                'time': barData[2],
                'open': float(barData[3]),
                'high': float(barData[4]),
                'low': float(barData[5]),
                'close': float(barData[6]),
                'volume': int(barData[7]),
                'openInterest': int(float(barData[8])),
                'date': barData[9]  # natural day
            }
            print(d)
            barList.append(d)
            
        return barList

    def loadMA40InitData(self, symbol, callback):
        bars = self.getHisBar(symbol, 168, period='15m')
        callback(bars)

    def getMinBars(self, symbol, callback):
        bars = []
        try:
            path = 'hisminbar'
            params = {
                'id': symbol,
                'num': 172,
                'period': '15m'
            }
            data = self.getData(path, params)
            if not data:
                return False
            barList = []
            l = data.split(';')
            for barStr in l:
                # 过滤某些空数据
                if ',' not in barStr:
                    continue

                barData = barStr.split(',')
                d = {
                    'symbol': barData[0],
                    # 'date': barData[1],   # trading day
                    'tradingDay': barData[1],
                    'minute': barData[2],
                    'time': barData[2],
                    'open': float(barData[3]),
                    'high': float(barData[4]),
                    'low': float(barData[5]),
                    'close': float(barData[6]),
                    'volume': int(barData[7]),
                    'openInterest': int(float(barData[8])),
                    'date': barData[9]  # natural day
                }
                barList.append(d)
            barList.reverse()
            for item in barList:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                bar.tradingDay = item['tradingDay']
                bar.datetime = datetime.strptime(
                    u'{0}-{1}-{2} {3}:{4}:00'.format(item['date'][0:4], item['date'][4:6], item['date'][6:8],
                                                     item['minute'][0:2], item['minute'][2:4]), '%Y-%m-%d %H:%M:00')
                bar.time = item['time']
                bar.open = item['open']
                bar.high = item['high']
                bar.low = item['low']
                bar.close = item['close']
                bar.volume = item['volume']
                bar.date = item['date']
                if bar.datetime.hour == 10 and bar.datetime.minute == 30:
                    continue
                # bar.datetime = bar.datetime - timedelta(seconds=5 * 60)
                callback(bar, bar_is_completed=False, bar_freq=15)
                # print(u'{0}, {1}, {2}, {3}, {4}'.format(bar.datetime, bar.open, bar.high, bar.low, bar.close))
            #     bars.append(bar)
            # print('*' * 20 + 'bars---' + '*' * 20)
            # print(bars)
            # if len(bars) > 0:
            #     for bar in bars:
            #         callback(bar)
            #     bars = []
            return True
            # else:
            #     self.strategy.writeCtaLog(u'从shcifo读取分钟数据失败')
            #     return False

        except Exception as e:
            self.strategy.writeCtaLog(u'加载shcifo历史分钟数据失败：'+str(e))
            return False

