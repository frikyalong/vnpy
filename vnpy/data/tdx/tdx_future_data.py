# encoding: UTF-8

# 从tdx下载期货数据.
# 收盘后的数据基本正确, 但盘中实时拿数据时:
# 1. 1Min的Bar可能不是最新的, 会缺几分钟.
# 2. 当周期>1Min时, 最后一根Bar可能不是完整的, 强制修改后
#    - 5min修改后freq基本正确
#    - 1day在VNPY合成时不关心已经收到多少Bar, 所以影响也不大
#    - 但其它分钟周期因为不好精确到每个品种, 修改后的freq可能有错

from datetime import datetime, timezone, timedelta, time
import sys
import requests
import execjs
import traceback
from vnpy.trader.app.ctaStrategy.ctaBase import CtaBarData
from pytdx.exhq import TdxExHq_API
from pytdx.params import TDXParams
from vnpy.trader.vtFunction import getJsonPath
from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtObject import VtErrorData
import json
import pandas as pd

IP_LIST = [{'ip': '112.74.214.43', 'port': 7727},
           {'ip': '59.175.238.38', 'port': 7727},
           {'ip': '124.74.236.94', 'port': 7721},
           {'ip': '218.80.248.229', 'port': 7721},
           {'ip': '124.74.236.94', 'port': 7721},
           {'ip': '58.246.109.27', 'port': 7721}
           ]

# 通达信 K 线种类
# 0 -   5 分钟K 线
# 1 -   15 分钟K 线
# 2 -   30 分钟K 线
# 3 -   1 小时K 线
# 4 -   日K 线
# 5 -   周K 线
# 6 -   月K 线
# 7 -   1 分钟
# 8 -   1 分钟K 线
# 9 -   日K 线
# 10 -  季K 线
# 11 -  年K 线
PERIOD_MAPPING = {}
PERIOD_MAPPING['1min']   = 8
PERIOD_MAPPING['5min']   = 0
PERIOD_MAPPING['15min']  = 1
PERIOD_MAPPING['30min']  = 2
PERIOD_MAPPING['1hour']  = 3
PERIOD_MAPPING['1day']   = 4
PERIOD_MAPPING['1week']  = 5
PERIOD_MAPPING['1month'] = 6

# 每个周期包含多少分钟 (估算值, 没考虑夜盘和10:15的影响)
NUM_MINUTE_MAPPING = {}
NUM_MINUTE_MAPPING['1min']   = 1
NUM_MINUTE_MAPPING['5min']   = 5
NUM_MINUTE_MAPPING['15min']  = 15
NUM_MINUTE_MAPPING['30min']  = 30
NUM_MINUTE_MAPPING['1hour']  = 60
NUM_MINUTE_MAPPING['1day']   = 60*24
NUM_MINUTE_MAPPING['1week']  = 60*24*7
NUM_MINUTE_MAPPING['1month'] = 60*24*7*30

# 常量
QSIZE = 500
ALL_MARKET_BEGIN_HOUR = 8
ALL_MARKET_END_HOUR = 16

class TdxFutureData(object):

    api = None
    connection_status = False  # 连接状态
    symbol_exchange_dict = {}  # tdx合约与vn交易所的字典
    symbol_market_dict = {}  # tdx合约与tdx市场的字典

    # ----------------------------------------------------------------------
    def __init__(self, strategy):
        """
        构造函数
        :param strategy: 上层策略，主要用与使用strategy.writeCtaLog（）
        """
        self.strategy = strategy

        self.connect()

    def connect(self):
        """
        连接API
        :return:
        """

        # 创建api连接对象实例
        try:
            if self.api is None or self.connection_status == False:
                self.strategy.writeCtaLog(u'开始连接通达信行情服务器')
                TdxFutureData.api = TdxExHq_API(heartbeat=True, auto_retry=True, raise_exception=True)

                # 选取最佳服务器
                self.best_ip = self.select_best_ip()

                self.api.connect(self.best_ip['ip'], self.best_ip['port'])
                # 尝试获取市场合约统计
                c = self.api.get_instrument_count()
                if c < 10:
                    err_msg = u'该服务器IP {}/{}无响应'.format(self.best_ip['ip'], self.best_ip['port'])
                    self.strategy.writeCtaError(err_msg)
                else:
                    self.strategy.writeCtaLog(u'创建tdx连接, IP: {}/{}'.format(self.best_ip['ip'], self.best_ip['port']))
                    # print(u'创建tdx连接, IP: {}/{}'.format(self.best_ip['ip'], self.best_ip['port']))
                    TdxFutureData.connection_status = True

                # 更新 symbol_exchange_dict , symbol_market_dict
                self.qryInstrument()
        except Exception as ex:
            self.strategy.writeCtaLog(u'连接服务器tdx异常:{},{}'.format(str(ex), traceback.format_exc()))
            return

    # ----------------------------------------------------------------------
    def ping(self, ip, port=7709):
        """
        ping行情服务器
        :param ip:
        :param port:
        :param type_:
        :return:
        """
        apix = TdxExHq_API()
        __time1 = datetime.now()
        try:
            with apix.connect(ip, port):
                if apix.get_instrument_count() > 10000:
                    _timestamp = datetime.now() - __time1
                    self.strategy.writeCtaLog('服务器{}:{},耗时:{}'.format(ip,port,_timestamp))
                    return _timestamp
                else:
                    self.strategy.writeCtaLog(u'该服务器IP {}无响应'.format(ip))
                    return timedelta(9, 9, 0)
        except:
            self.strategy.writeCtaError(u'tdx ping服务器，异常的响应{}'.format(ip))
            return timedelta(9, 9, 0)

    # ----------------------------------------------------------------------
    def select_best_ip(self):
        """
        选择行情服务器
        :return:
        """
        self.strategy.writeCtaLog(u'选择通达信行情服务器')

        data_future = [self.ping(x['ip'], x['port']) for x in IP_LIST]

        best_future_ip = IP_LIST[data_future.index(min(data_future))]

        self.strategy.writeCtaLog(u'选取 {}:{}'.format(best_future_ip['ip'], best_future_ip['port']))
        # print(u'选取 {}:{}'.format(best_future_ip['ip'], best_future_ip['port']))
        return best_future_ip

    # ----------------------------------------------------------------------
    def qryInstrument(self):
        """
        查询/更新合约信息
        :return:
        """
        if not self.connection_status:
            return

        if self.api is None:
            self.strategy.writeCtaLog(u'取不到api连接，更新合约信息失败')
            # print(u'取不到api连接，更新合约信息失败')
            return

        # 取得所有的合约信息
        num = self.api.get_instrument_count()
        if not isinstance(num,int):
            return

        all_contacts = sum([self.api.get_instrument_info((int(num / 500) - i) * 500, 500) for i in range(int(num / 500) + 1)],[])
        #[{"category":category,"market": int,"code":sting,"name":string,"desc":string},{}]

        # 对所有合约处理，更新字典 指数合约-tdx市场，指数合约-交易所
        for tdx_contract in all_contacts:
            tdx_symbol = tdx_contract.get('code', None)
            if tdx_symbol is None:
                continue
            tdx_market_id = tdx_contract.get('market')
            if tdx_market_id == 47:     # 中金所
                TdxFutureData.symbol_exchange_dict.update({tdx_symbol: 'CFFEX'})
                TdxFutureData.symbol_market_dict.update({tdx_symbol:tdx_market_id})
            elif tdx_market_id == 28:   # 郑商所
                TdxFutureData.symbol_exchange_dict.update({tdx_symbol: 'CZCE'})
                TdxFutureData.symbol_market_dict.update({tdx_symbol:tdx_market_id})
            elif tdx_market_id == 29:   # 大商所
                TdxFutureData.symbol_exchange_dict.update({tdx_symbol: 'DCE'})
                TdxFutureData.symbol_market_dict.update({tdx_symbol:tdx_market_id})
            elif tdx_market_id == 30:   # 上期所+能源
                TdxFutureData.symbol_exchange_dict.update({tdx_symbol: 'SHFE'})
                TdxFutureData.symbol_market_dict.update({tdx_symbol:tdx_market_id})

    # ----------------------------------------------------------------------
    def get_bars(self, symbol, period, callback, bar_is_completed=False, bar_freq=1, start_dt=None):
        """
        返回k线数据
        symbol：合约
        period: 周期: 1min,3min,5min,15min,30min,1day,3day,1hour,2hour,4hour,6hour,12hour
        """

        ret_bars = []
        tdx_symbol = symbol.upper().replace('_' , '')
        tdx_symbol = tdx_symbol.replace('99' , 'L9')
        if tdx_symbol not in self.symbol_exchange_dict.keys():
            self.strategy.writeCtaError(u'{} 合约{}/{}不在下载清单中: {}'.format(datetime.now(), symbol, tdx_symbol, self.symbol_exchange_dict.keys()))
            # print(u'{} 合约{}/{}不在下载清单中: {}'.format(datetime.now(), symbol, tdx_symbol, self.symbol_exchange_dict.keys()))
            return False,ret_bars
        if period not in PERIOD_MAPPING.keys():
            self.strategy.writeCtaError(u'{} 周期{}不在下载清单中: {}'.format(datetime.now(), period, list(PERIOD_MAPPING.keys())))
            # print(u'{} 周期{}不在下载清单中: {}'.format(datetime.now(), period, list(PERIOD_MAPPING.keys())))
            return False,ret_bars
        if self.api is None:
            return False,ret_bars

        tdx_period = PERIOD_MAPPING.get(period)

        if start_dt is None:
            self.strategy.writeCtaLog(u'没有设置开始时间，缺省为10天前')
            qry_start_date = datetime.now() - timedelta(days=10)
        else:
            qry_start_date = start_dt
        end_date = datetime.combine(datetime.now() + timedelta(days=1),time(ALL_MARKET_END_HOUR, 0))
        if qry_start_date > end_date:
            qry_start_date = end_date
        self.strategy.writeCtaLog('{}开始下载tdx:{} {}数据, {} to {}.'.format(datetime.now(), tdx_symbol, tdx_period, qry_start_date, end_date))
        # print('{}开始下载tdx:{} {}数据, {} to {}.'.format(datetime.now(), tdx_symbol, tdx_period, last_date, end_date))

        try:
            _start_date = end_date
            _bars = []
            _pos = 0
            while _start_date > qry_start_date:
                _res = self.api.get_instrument_bars(
                    PERIOD_MAPPING[period],
                    self.symbol_market_dict[tdx_symbol],
                    tdx_symbol,
                    _pos,
                    QSIZE)
                if _res is not None:
                    _bars = _res + _bars
                _pos += QSIZE
                if _res is not None and len(_res) > 0:
                    _start_date = _res[0]['datetime']
                    _start_date = datetime.strptime(_start_date, '%Y-%m-%d %H:%M')
                    self.strategy.writeCtaLog(u'分段取数据开始:{}'.format(_start_date))
                else:
                    break
            if len(_bars) == 0:
                self.strategy.writeCtaError('{} Handling {}, len1={}..., continue'.format(
                    str(datetime.now()), tdx_symbol, len(_bars)))
                return False, ret_bars

            current_datetime = datetime.now()
            data = self.api.to_df(_bars)
            data = data.assign(datetime=pd.to_datetime(data['datetime']))
            data = data.assign(ticker=symbol)
            data['instrument_id'] = data['ticker']
            # if future['market'] == 28 or future['market'] == 47:
            #     # 大写字母: 郑州商品 or 中金所期货
            #     data['instrument_id'] = data['ticker']
            # else:
            #     data['instrument_id'] = data['ticker'].apply(lambda x: x.lower())

            data['symbol'] = symbol
            data = data.drop(
                ['year', 'month', 'day', 'hour', 'minute', 'price', 'amount', 'ticker'],
                errors='ignore',
                axis=1)
            data = data.rename(
                index=str,
                columns={
                    'position': 'open_interest',
                    'trade': 'volume',
                })
            if len(data) == 0:
                print('{} Handling {}, len2={}..., continue'.format(
                    str(datetime.now()), tdx_symbol, len(data)))
                return False, ret_bars

            data['total_turnover'] = data['volume']
            data["limit_down"] = 0
            data["limit_up"] = 999999
            data['trading_date'] = data['datetime']
            data['trading_date'] = data['trading_date'].apply(lambda x: (x.strftime('%Y-%m-%d')))
            monday_ts = data['datetime'].dt.weekday == 0  # 星期一
            night_ts1 = data['datetime'].dt.hour > ALL_MARKET_END_HOUR
            night_ts2 = data['datetime'].dt.hour < ALL_MARKET_BEGIN_HOUR
            data.loc[night_ts1, 'datetime'] -= timedelta(days=1)  # 所有日期的夜盘(21:00~24:00), 减一天
            monday_ts1 = monday_ts & night_ts1  # 星期一的夜盘(21:00~24:00), 再减两天
            data.loc[monday_ts1, 'datetime'] -= timedelta(days=2)
            monday_ts2 = monday_ts & night_ts2  # 星期一的夜盘(00:00~04:00), 再减两天
            data.loc[monday_ts2, 'datetime'] -= timedelta(days=2)
            # data['datetime'] -= timedelta(minutes=1) # 直接给Strategy使用, RiceQuant格式, 不需要减1分钟
            data['dt_datetime'] = data['datetime']
            data['date'] = data['datetime'].apply(lambda x: (x.strftime('%Y-%m-%d')))
            data['time'] = data['datetime'].apply(lambda x: (x.strftime('%H:%M:%S')))
            data['datetime'] = data['datetime'].apply(lambda x: float(x.strftime('%Y%m%d%H%M%S')))
            data = data.set_index('dt_datetime', drop=False)
            # data = data[int(last_date.strftime('%Y%m%d%H%M%S')):int(end_date.strftime('%Y%m%d%H%M%S'))]
            # data = data[str(last_date):str(end_date)]

            for index, row in data.iterrows():
                add_bar = CtaBarData()
                try:
                    add_bar.vtSymbol = row['symbol']
                    add_bar.symbol = row['symbol']
                    add_bar.datetime = index
                    add_bar.date = row['date']
                    add_bar.time = row['time']
                    add_bar.tradingDay = row['trading_date']
                    add_bar.open = float(row['open'])
                    add_bar.high = float(row['high'])
                    add_bar.low = float(row['low'])
                    add_bar.close = float(row['close'])
                    add_bar.volume = float(row['volume'])
                except Exception as ex:
                    self.strategy.writeCtaError('error when convert bar:{},ex:{},t:{}'.format(row, str(ex), traceback.format_exc()))
                    # print('error when convert bar:{},ex:{},t:{}'.format(row, str(ex), traceback.format_exc()))
                    return False

                if start_dt is not None and index < start_dt:
                    continue
                ret_bars.append(add_bar)

                if callback is not None:
                    freq = bar_freq
                    bar_is_completed = True
                    if period != '1min' and index == data['dt_datetime'][-1]:
                        # 最后一个bar，可能是不完整的，强制修改
                        # - 5min修改后freq基本正确
                        # - 1day在VNPY合成时不关心已经收到多少Bar, 所以影响也不大
                        # - 但其它分钟周期因为不好精确到每个品种, 修改后的freq可能有错
                        if index > current_datetime:
                            bar_is_completed = False
                            # 根据秒数算的话，要+1，例如13:31,freq=31，第31根bar
                            freq = NUM_MINUTE_MAPPING[period] - int((index - current_datetime).total_seconds() / 60)
                    callback(add_bar, bar_is_completed, freq)

            return True,ret_bars
        except Exception as ex:
            self.strategy.writeCtaError('exception in get:{},{},{}'.format(tdx_symbol,str(ex), traceback.format_exc()))
            # print('exception in get:{},{},{}'.format(tdx_symbol,str(ex), traceback.format_exc()))
            self.strategy.writeCtaLog(u'重置连接')
            TdxFutureData.api = None
            self.connect()
            return False,ret_bars


if __name__ == "__main__":
    class T(object):

        def writeCtaError(self,content):
            print(content,file=sys.stderr)

        def writeCtaLog(self,content):
            print(content)

        def display_bar(self,bar, bar_is_completed=True, freq=1):
            print(u'{} {}'.format(bar.vtSymbol,bar.datetime))

    t1 = T()
    t2 = T()
    # 创建API对象
    api_01 = TdxFutureData(t1)

    # 获取历史分钟线
    api_01.get_bars('rb1905', period='5min', callback=t1.display_bar)
    # api.get_bars(symbol, period='5min', callback=display_bar)
   # api_01.get_bars('IF99', period='1day', callback=t1.display_bar)

   # 测试单实例
   # api_02 = TdxFutureData(t2)
    #api_02.get_bars('IF99', period='1min', callback=t1.display_bar)