# encoding: UTF-8

# 首先写系统内置模块
import sys
from datetime import datetime, timedelta, date
from time import sleep
import numpy

# 其次，导入vnpy的基础模块

from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate
from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_INT, DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, STATUS_CANCELLED,EMPTY_FLOAT

# 然后是自己编写的模块
from vnpy.trader.app.ctaStrategy.ctaTemplate import *
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.trader.app.ctaStrategy.ctaPolicy import  *
from vnpy.trader.app.ctaStrategy.ctaPosition import *
from vnpy.trader.util_sina import UtilSinaClient

cta_engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Strategy_TripleMa_v01(CtaTemplate):
    """螺纹钢、5分钟级别、macd信号+120均线过滤
    策略：
    macd在0轴上下的金叉死叉，120均线做多空过滤
    MA120之上、macd0轴之下
        macd快线 上穿 macd慢线，金叉，做多
        macd快线  下穿 macd慢线，死叉，平多
    MA120之下、macd0轴之上
        macd快线 下穿 macd慢线，死叉，做空
        macd快线 上穿 macd慢线，金叉，平空
    更新记录


    """
    className = 'Strategy_TripleMa'
    author = u'李来佳'

    # 策略在外部设置的参数
    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    minDiff = 1                # 商品的最小交易单位

#----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting=None):
        """Constructor"""
        super(Strategy_TripleMa_v01, self).__init__(ctaEngine, setting)

        # 增加监控参数项目
        self.paramList.append('inputSS')
        self.paramList.append('minDiff')
        self.paramList.append('vtSymbol')
        self.paramList.append('symbol')
        self.paramList.append('inputMa1Len')
        self.paramList.append('inputMa2Len')
        self.paramList.append('inputMa3Len')
        self.paramList.append('inputMacdFastPeriodLen')    #增加macd
        self.paramList.append('inputMacdSlowPeriodLen')    #增加macd
        self.paramList.append('inputMacdSignalPeriodLen')  #增加macd

        # 增加监控变量项目
        self.varList.append('pos')              # 仓位
        self.varList.append('entrust')          # 是否正在委托

        self.curDateTime = None                 # 当前Tick时间
        self.curTick = None                     # 最新的tick
        self.lastOrderTime = None               # 上一次委托时间
        self.cancelSeconds = 60                 # 撤单时间(秒)

        # 定义日内的交易窗口
        self.openWindow = False                 # 开市窗口
        self.tradeWindow = False                # 交易窗口
        self.closeWindow = False                # 收市平仓窗口

        self.inited = False                     # 是否完成了策略初始化
        self.backtesting = False                # 是否回测
        self.lineM5 = None                      # 5分钟K线

        if setting:
            # 根据配置文件更新参数
            self.setParam(setting)

            # 创建的M5 K线
            lineM5Setting = {}
            lineM5Setting['name'] = u'M5'            # k线名称
            lineM5Setting['barTimeInterval'] = 5    # K线的Bar时长
            lineM5Setting['inputMa1Len'] = 10        # 第1条均线
            lineM5Setting['inputMa2Len'] = 60        # 第2条均线
            lineM5Setting['inputMa3Len'] = 120       # 第3条均线
            lineM5Setting['inputMacdFastPeriodLen'] = 12  #macd快线
            lineM5Setting['inputMacdSlowPeriodLen'] = 26  #macd慢线
            lineM5Setting['inputMacdSignalPeriodLen'] = 9 #macd周期
            lineM5Setting['minDiff'] = self.minDiff
            lineM5Setting['shortSymbol'] = self.shortSymbol
            self.lineM5 = CtaMinuteBar(self, self.onBarM5, lineM5Setting)

            try:
                mode = setting['mode']
                if mode != EMPTY_STRING:
                    self.lineM5.setMode(setting['mode'])
            except KeyError:
                self.lineM5.setMode(self.lineM5.TICK_MODE)

        self.onInit()

    #----------------------------------------------------------------------
    def onInit(self, force = False):
        """初始化 """
        if force:
            self.writeCtaLog(u'策略强制初始化')
            self.inited = False
            self.trading = False                        # 控制是否启动交易
        else:
            self.writeCtaLog(u'策略初始化')
            if self.inited:
                self.writeCtaLog(u'已经初始化过，不再执行')
                return

        self.pos = EMPTY_INT                 # 初始化持仓
        self.entrust = EMPTY_INT             # 初始化委托状态
        if not self.backtesting:
            # 这里需要加载前置数据哦。
            if self.__initDataFromSina():
               self.inited = True                   # 更新初始化标识
            else:
               self.writeCtaError(u'从Sina初始数据失败')
               return

            # 这里是使用Ricequant的历史数据
            # if self.__initDataFromRq():
            #     self.inited = True
            # else:
            #     self.writeCtaError(u'从Ricequant初始数据失败')
            #     return

            # 这里是使用通达信的历史数据
            #if self.__initDataFromTdx():
            #    self.inited = True
            #else:
            #    self.writeCtaError(u'从Ricequant初始数据失败')
            #    return

        self.putEvent()
        self.writeCtaLog(u'策略初始化完成')

    def __initDataFromRq(self):
        """从ricequant初始化5分钟数据"""
        try:
            import rqdatac as rq
            rq.init()

            # 开始时间(120周期得5分钟）
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            # 结束时间，若有夜盘，一般是明天或下周一
            end_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')


            fields = ['open', 'close', 'high', 'low', 'volume', 'open_interest', 'limit_up', 'limit_down','trading_date']

            self.writeCtaLog(u'ds.get_price(order_book_id={}, start_date={}, end_date={}, frequency=1m, fields={}'
                             .format(self.getFullSymbol(self.symbol).upper(), start_date, end_date,  fields))

            # ricequant返回得bar，datetime属性是bar的结束时间，所以不能使用callback函数自动推送Bar
            df = rq.get_price(order_book_ids=self.getFullSymbol(self.symbol).upper(), start_date=start_date,
                              end_date=end_date, frequency='1m', fields=fields)

            self.writeCtaLog(u'一共获取{}条1分钟数据'.format(len(df)))
            for idx in df.index:
                row = df.loc[idx]
                bar = CtaBarData()
                bar.vtSymbol = self.symbol
                bar.symbol = self.symbol
                last_bar_dt = datetime.strptime(str(idx), '%Y-%m-%d %H:%M:00')
                self.curDateTime = last_bar_dt
                bar.datetime = last_bar_dt - timedelta(minutes=1)
                bar.date = bar.datetime.strftime('%Y-%m-%d')
                bar.time = bar.datetime.strftime('%H:%M:00')

                if bar.datetime.hour >= 21:
                    if bar.datetime.isoweekday() == 5:
                        # 星期五=》星期一
                        bar.tradingDay = (bar.datetime + timedelta(days=3)).strftime('%Y-%m-%d')
                    else:
                        # 第二天
                        bar.tradingDay = (bar.datetime + timedelta(days=1)).strftime('%Y-%m-%d')
                elif bar.datetime.hour < 8 and bar.datetime.isoweekday() == 6:
                    # 星期六=>星期一
                    bar.tradingDay = (bar.datetime + timedelta(days=2)).strftime('%Y-%m-%d')
                else:
                    bar.tradingDay = bar.date

                # 推送Bar到策略中
                bar.open = float(row['open'])
                bar.high = float(row['high'])
                bar.low = float(row['low'])
                bar.close = float(row['close'])
                bar.volume = int(row['volume'])

                # self.writeCtaLog(u'{} o:{};h:{};l:{};c:{},v:{},tradingDay:{}'
                #                 .format(bar.date+' '+bar.time, bar.open, bar.high,
                #                         bar.low, bar.close, bar.volume, bar.tradingDay))
                self.lineM5.addBar(bar,bar_freq=1)
            return True

        except Exception as ex:
            self.writeCtaError(u'__initDataFromRq Exception:{},{}'.format(str(ex),traceback.format_exc()))
            return False

    def __initDataFromTdx(self):
        """从通达信初始化五分钟数据"""
        try:
            from vnpy.data.tdx.tdx_future_data import TdxFutureData

            # 创建接口
            tdx = TdxFutureData(self)

            # 开始时间(120周期得5分钟）
            start_dt = datetime.now() - timedelta(days=30)

            # 通达信返回得bar，datetime属性是bar的结束时间，所以不能使用callback函数自动推送Bar
            # 这里可以直接取5分钟，也可以取一分钟数据
            result,min1_bars = tdx.get_bars(symbol=self.vtSymbol,period='1min',callback=None,bar_freq=1,start_dt=start_dt)

            if not result:
                self.writeCtaError(u'未能取回数据')
                return False

            for bar in min1_bars:
                bar.datetime = bar.datetime - timedelta(minutes=1)
                bar.time = bar.datetime.strftime('%H:%M:%S')
                self.lineM5.addBar(bar,bar_freq=1)

            return True

        except Exception as ex:
            self.writeCtaError(u'__initDataFromTdx Exception:{},{}'.format(str(ex),traceback.format_exc()))
            return False

    def __initDataFromSina(self):
        """从sina初始化5分钟数据"""
        sina = UtilSinaClient(self)
        ret = sina.getMinBars(symbol=self.symbol, minute=5, callback=self.lineM5.addBar)
        if not ret:
            self.writeCtaLog(u'获取M5数据失败')
            return False

        return True

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'启动')
        self.trading = True
        self.putEvent()

        #self.saveKLine(
        #    ['datetime', 'open', 'close', 'low', 'high', 'volume', 'openInterest', 'ma1', 'ma2',
        #     'ma3', 'macdfast', 'macdslow', 'macdsignal'])
        #self.savetns()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.uncompletedOrders.clear()
        self.pos = EMPTY_INT
        self.entrust = EMPTY_INT

        self.writeCtaLog(u'停止' )
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """交易更新"""
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.pos))

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """报单更新"""
        self.writeCtaLog(u'OnOrder()报单更新，orderID:{0},{1},totalVol:{2},tradedVol:{3},offset:{4},price:{5},direction:{6},status:{7}'
                         .format(order.orderID, order.vtSymbol, order.totalVolume,order.tradedVolume,
                                 order.offset, order.price, order.direction, order.status))

        # 委托单主键，vnpy使用 "gateway.orderid" 的组合
        orderkey = order.gatewayName+u'.'+order.orderID

        if orderkey in self.uncompletedOrders:
            if order.totalVolume == order.tradedVolume:
                # 开仓，平仓委托单全部成交
                # 平空仓完成(cover)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平空仓完成')
                    # 更新仓位
                    self.pos = EMPTY_INT

                # 平多仓完成(sell)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平多仓完成')
                    # 更新仓位
                    self.pos = EMPTY_INT

                # 开多仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开多仓完成')
                    # 更新仓位
                    self.pos = order.tradedVolume

                # 开空仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开空仓完成')
                    self.pos = 0 - order.tradedVolume

                del self.uncompletedOrders[orderkey]
                if len(self.uncompletedOrders) == 0:
                    self.entrust = 0

            elif order.tradedVolume > 0 and not order.totalVolume == order.tradedVolume and order.offset != OFFSET_OPEN:
                # 平仓委托单部分成交
                pass

            elif order.offset == OFFSET_OPEN and order.status == STATUS_CANCELLED:
                # 开仓委托单被撤销
                self.entrust = 0
                pass

            else:
                self.writeCtaLog(u'OnOrder()委托单返回，total:{0},traded:{1}'
                                 .format(order.totalVolume, order.tradedVolume,))

        self.putEvent()         # 更新监控事件

    # ----------------------------------------------------------------------
    def onStopOrder(self, orderRef):
        """停止单更新"""
        self.writeCtaLog(u'{0},停止单触发，orderRef:{1}'.format(self.curDateTime, orderRef))
        pass

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """行情更新
        :type tick: object
        """
        self.curTick = tick

        if (tick.datetime.hour >= 3 and tick.datetime.hour <= 8) or (tick.datetime.hour >= 16 and tick.datetime.hour <= 20):
            self.writeCtaLog(u'休市/集合竞价排名时数据不处理')
            return

        # 更新策略执行的时间（用于回测时记录发生的时间）
        self.curDateTime = tick.datetime

        # 2、计算交易时间和平仓时间
        self.__timeWindow(self.curDateTime)

        # 推送Tick到lineM5
        self.lineM5.onTick(tick)

        # 首先检查是否是实盘运行还是数据预处理阶段
        if not (self.inited and len(self.lineM5.lineMa3) > 0):
            return

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """分钟K线数据更新（仅用于回测时，从策略外部调用)"""

        # 更新策略执行的时间（用于回测时记录发生的时间）
        # 回测数据传送的bar.datetime，为bar的开始时间，所以，到达策略时，当前时间为bar的结束时间
        self.curDateTime = bar.datetime + timedelta(seconds=self.lineM5.barTimeInterval)

        # 2、计算交易时间和平仓时间
        self.__timeWindow(bar.datetime)

        # 推送tick到5分钟K线
        self.lineM5.addBar(bar)

        # 4、交易逻辑
        # 首先检查是否是实盘运行还是数据预处理阶段
        if not self.inited:
            if len(self.lineM5.lineBar) > 300 + 5:
                self.inited = True
            else:
                return

    def onBarM5(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineM5的回调"""

        # 调用lineM5的显示bar内容
        self.writeCtaLog(self.lineM5.displayLastBar())

        # 未初始化完成
        if not self.inited:
                return

        if len(self.lineM5.lineMa2)< 2:
            return

        # 执行撤单逻辑
        self.__cancelLogic(dt=self.curDateTime)

        if self.lineM5.mode == self.lineM5.TICK_MODE:
            idx = 2
        else:
            idx = 1

        if self.backtesting:
            t = {}
            t['datetime'] = bar.datetime
            t['open'] = bar.open
            t['close'] = bar.close
            t['low'] = bar.low
            t['high'] = bar.high
            t['volume'] = bar.volume
            t['openInterest'] = self.pos
            t['ma1'] = self.lineM5.lineMa1[-1]
            t['ma2'] = self.lineM5.lineMa2[-1]
            t['ma3'] = self.lineM5.lineMa3[-1]
            t['macdfast'] = self.lineM5.lineDif[-1] # DIF = EMA12 - EMA26，即为talib-MACD返回值macd
            t['macdslow'] = self.lineM5.lineDea[-1] # DEA = （前一日DEA X 8/10 + 今日DIF X 2/10），即为talib-MACD返回值
            t['macdsignal'] = self.lineM5.lineMacd[-1] # (dif-dea)*2，但是talib中MACD的计算是bar = (dif-dea)*1,国内一般是乘以2
            # self.KLinewriter.writerow(t)


        # 如果未持仓，检查是否符合开仓逻辑
        if self.pos == 0:
            # macd快 上穿 macd慢， macd柱子 < 0， bar.close > MA1200
            if self.lineM5.lineDif[-2] < self.lineM5.lineDea[-2] \
                    and self.lineM5.lineDif[-1] > self.lineM5.lineDea[-1] \
                    and bar.close > self.lineM5.lineMa3[-1]:
                    #and self.lineM5.lineDif[-1] > self.lineM5.lineDea[-1] \
                    #and self.lineM5.lineMacd[-1] < 0 \
                    #and bar.close > self.lineM5.lineMa3[-1]:


                self.writeCtaLog(u'{0},开仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                if self.backtesting:
                    t1 = {}
                    t1['datetime'] = bar.datetime
                    t1['direction'] = 'long'
                    t1['price'] = bar.close
                    self.tnswriter.writerow(t1)

                orderid = self.buy(price=bar.close+self.minDiff, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return

            # macd快 下穿 macd慢， macd柱子 > 0， bar.close < MA1200
            if self.lineM5.lineDif[-2] > self.lineM5.lineDea[-2] \
                    and self.lineM5.lineDif[-1] < self.lineM5.lineDea[-1] \
                    and bar.close < self.lineM5.lineMa3[-1]:
                    #and self.lineM5.lineDif[-1] < self.lineM5.lineDea[-1] \
                    #and self.lineM5.lineMacd[-1] > 0 \
                    #and bar.close < self.lineM5.lineMa3[-1]:
                self.writeCtaLog(u'{0},开仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))

                if self.backtesting:
                    t3 = {}
                    t3['datetime'] = bar.datetime
                    t3['direction'] = 'short'
                    t3['price'] = bar.close
                    self.tnswriter.writerow(t3)

                orderid = self.short(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return

        # 持仓，检查是否满足平仓条件
        else:
            # macd快下穿macd慢，多单离场
            if self.lineM5.lineDif[0-idx] < self.lineM5.lineDea[0-idx] \
                    and self.pos > 0 and self.entrust != -1:
                self.writeCtaLog(u'{0},平仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                if self.backtesting:
                    t2 = {}
                    t2['datetime'] = bar.datetime
                    t2['direction'] = 'long'
                    t2['price'] = bar.close
                    self.tnswriter.writerow(t2)

                orderid = self.sell(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return

            # macd快上穿macd慢，空离场
            if self.lineM5.lineDif[0-idx] > self.lineM5.lineDea[0-idx] \
                    and self.pos < 0 and self.entrust != 1:
                self.writeCtaLog(u'{0},平仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))

                if self.backtesting:
                    t4 = {}
                    t4['datetime'] = bar.datetime
                    t4['direction'] = 'short'
                    t4['price'] = bar.close
                    self.tnswriter.writerow(t4)

                orderid = self.cover(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return


    # ----------------------------------------------------------------------
    def __cancelLogic(self, dt, force=False):
        "撤单逻辑"""

        if len(self.uncompletedOrders) < 1:
            return

        if not self.lastOrderTime:
            self.writeCtaLog(u'异常，上一交易时间为None')
            return

        # 平仓检查时间比开开仓时间需要短一倍
        if (self.pos >= 0 and self.entrust == 1) \
                or (self.pos <= 0 and self.entrust == -1):
            i = 1
        else:
            i = 1  # 原来是2，暂时取消

        canceled = False

        if ((dt - self.lastOrderTime).seconds > self.cancelSeconds / i ) or force:  # 超过设置的时间还未成交

            for order in self.uncompletedOrders.keys():
                self.writeCtaLog(u'{0}超时{1}秒未成交，取消委托单：{2}'.format(dt, (dt - self.lastOrderTime).seconds, order))

                self.cancelOrder(str(order))

                canceled = True

            # 取消未完成的订单
            self.uncompletedOrders.clear()

            if canceled:
                self.entrust = 0
            else:
                self.writeCtaLog(u'异常：没有撤单')

    def __timeWindow(self, dt):
        """交易与平仓窗口"""
        # 交易窗口 避开早盘和夜盘的前5分钟，防止隔夜跳空。

        self.closeWindow = False
        self.tradeWindow = False
        self.openWindow = False

        # 初始化当日的首次交易
        # if (tick.datetime.hour == 9 or tick.datetime.hour == 21) and tick.datetime.minute == 0 and tick.datetime.second ==0:
        #  self.firstTrade = True

        # 开市期，波动较大，用于判断止损止盈，或开仓
        if (dt.hour == 9 or dt.hour == 21) and dt.minute < 2:
            self.openWindow = True

        # 日盘
        if dt.hour == 9 and dt.minute >= 0:
            self.tradeWindow = True
            return

        if dt.hour == 10:
            if dt.minute <= 15 or dt.minute >= 30:
                self.tradeWindow = True
                return

        if dt.hour == 11 and dt.minute <= 30:
            self.tradeWindow = True
            return

        if dt.hour == 13 and dt.minute >= 30:
            self.tradeWindow = True
            return

        if dt.hour == 14:

            if dt.minute < 59:
                self.tradeWindow = True
                return

            if dt.minute == 59:  # 日盘平仓
                self.closeWindow = True
                return

        # 夜盘

        if dt.hour == 21 and dt.minute >= 0:
            self.tradeWindow = True
            return

        # 上期 贵金属， 次日凌晨2:30
        if self.shortSymbol in NIGHT_MARKET_SQ1:

            if dt.hour == 22 or dt.hour == 23 or dt.hour == 0 or dt.hour == 1:
                self.tradeWindow = True
                return

            if dt.hour == 2:
                if dt.minute < 29:  # 收市前29分钟
                    self.tradeWindow = True
                    return
                if dt.minute == 29:  # 夜盘平仓
                    self.closeWindow = True
                    return
            return

        # 上期 有色金属，黑色金属，沥青 次日01:00
        if self.shortSymbol in NIGHT_MARKET_SQ2:
            if dt.hour == 22 or dt.hour == 23:
                self.tradeWindow = True
                return

            if dt.hour == 0:
                if dt.minute < 59:  # 收市前29分钟
                    self.tradeWindow = True
                    return

                if dt.minute == 59:  # 夜盘平仓
                    self.closeWindow = True
                    return

            return

        # 上期 天然橡胶  23:00
        if self.shortSymbol in NIGHT_MARKET_SQ3:

            if dt.hour == 22:
                if dt.minute < 59:  # 收市前1分钟
                    self.tradeWindow = True
                    return

                if dt.minute == 59:  # 夜盘平仓
                    self.closeWindow = True
                    return

        # 郑商、大连 23:30
        if self.shortSymbol in NIGHT_MARKET_ZZ or self.shortSymbol in NIGHT_MARKET_DL:
            if dt.hour == 22:
                self.tradeWindow = True
                return

            if dt.hour == 23:
                if dt.minute < 29:  # 收市前1分钟
                    self.tradeWindow = True
                    return
                if dt.minute == 29 and dt.second > 30:  # 夜盘平仓
                    self.closeWindow = True
                    return
            return

    #----------------------------------------------------------------------
    def strToTime(self, t, ms):
        """从字符串时间转化为time格式的时间"""
        hh, mm, ss = t.split(':')
        tt = datetime.time(int(hh), int(mm), int(ss), microsecond=ms)
        return tt

     #----------------------------------------------------------------------
    def saveData(self, id):
        """保存过程数据"""
        # 保存K线
        if not self.backtesting:
            return

def testRbByTick():

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20160101')

    # 设置回测用的数据结束日期
    engine.setEndDate('20160330')

    # engine.connectMysql()
    engine.setDatabase(dbName='stockcn', symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小

    settings = {}
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'TripleMa'
    settings['mode'] = 'tick'
    settings['backtesting'] = True

    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_TripleMa, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 100000  # 设置期初资金
    engine.percentLimit = 30  # 设置资金使用上限比例(%)
    engine.barTimeInterval = 60*5  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 10  # 固定交易费用（每次开平仓收费）
    # 开始跑回测
    engine.runBacktestingWithMysql()

    # 显示回测结果
    engine.showBacktestingResult()

def testRbByBar():
    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为bar
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20110613')

    # 设置回测用的数据结束日期
    engine.setEndDate('20131202')

    engine.setDatabase(dbName=MINUTE_DB_NAME,symbol='rb00000')

    # 设置产品相关参数
    engine.setSlippage(1)     # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))    # 万1
    engine.setSize(10)         # 合约大小

    settings = {}
    settings['vtSymbol'] = 'rb00000'
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'TripleMa'
    settings['mode'] = 'bar'
    settings['backtesting'] = True
    settings['percentLimit'] = 30
    settings['inputMa1Len'] = 10
    settings['inputMa2Len'] = 60
    settings['inputMa3Len'] = 1200
    settings['inputMacdFastPeriodLen'] = 12  # macd快线
    settings['inputMacdSlowPeriodLen'] = 26  # macd慢线
    settings['inputMacdSignalPeriodLen'] = 9  # macd周期


    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_TripleMa, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False     # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 100000      # 设置期初资金
    engine.percentLimit = 30        # 设置资金使用上限比例(%)
    engine.barTimeInterval = 300    # bar的周期秒数，用于csv文件自动减时间

    # 开始跑回测
    # engine.runBackTestingWithBarFile(os.getcwd() + '/RB88_20100101_20161231_M5.csv')
    engine.runBacktesting()
    # 显示回测结果
    engine.showBacktestingResult()


# 从csv文件进行回测
if __name__ == '__main__':

    from vnpy.trader.app.ctaStrategy.ctaBacktesting import *
    #from vnpy.trader.setup_logger import setup_logger

    #setup_logger(
        #filename=u'TestLogs/{0}_{1}.log'.format(Strategy_TripleMa.className, datetime.now().strftime('%m%d_%H%M')),
        #debug=False)
    # 回测螺纹
    testRbByBar()
    #testRbByTick()




