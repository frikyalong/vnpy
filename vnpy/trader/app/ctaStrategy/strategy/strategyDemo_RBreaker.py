# encoding: UTF-8

# 首先写系统内置模块
import sys
import os
from datetime import datetime, timedelta, time, date
import copy
import traceback
from time import sleep
import execjs
from collections import OrderedDict

# 其次，导入vnpy的基础模块
TREND_cta_engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 然后是自己编写的模块
from vnpy.trader.app.ctaStrategy.ctaTemplate import *
from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.vtConstant import DIRECTION_LONG, DIRECTION_SHORT
from vnpy.trader.vtConstant import PRICETYPE_LIMITPRICE,  OFFSET_OPEN, OFFSET_CLOSE, STATUS_ALLTRADED, STATUS_CANCELLED, STATUS_REJECTED
from vnpy.trader.vtConstant import EXCHANGE_OKEX, EXCHANGE_BINANCE
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.trader.app.ctaStrategy.ctaPosition import *
from vnpy.trader.app.ctaStrategy.ctaPolicy import CtaPolicy
from vnpy.trader.app.ctaStrategy.ctaGridTrade import *

class SDemo_Policy(CtaPolicy):
    """策略事务"""
    def __init__(self, strategy):
        super(SDemo_Policy, self).__init__(strategy)
        self.tns_start_price = 0  # 事务开始时得参考价格
        self.tns_start_date = ''  # 事务开启的交易日
        self.tns_direction = None  # 日线方向 DIRECTION_LONG 向上/ DIRECTION_SHORT向下

    def toJson(self):
        """
        将数据转换成dict
        :return:
        """
        j = OrderedDict()
        j['create_time']       = self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time is not None else EMPTY_STRING
        j['save_time']         = self.save_time.strftime('%Y-%m-%d %H:%M:%S') if self.save_time is not None else EMPTY_STRING
        j['tns_start_date']    = self.tns_start_date
        j['tns_start_price']   = self.tns_start_price if self.tns_start_price is not None else 0
        j['tns_direction']     = self.tns_direction if self.tns_direction is not None else EMPTY_STRING

        return j

    def fromJson(self, json_data):
        """
        将dict转化为属性
        :param json_data:
        :return:
        """
        if not isinstance(json_data,dict):
            return

        if 'create_time' in json_data:
            try:
                self.create_time = datetime.strptime(json_data['create_time'], '%Y-%m-%d %H:%M:%S')
            except Exception as ex:
                self.writeCtaError(u'解释create_time异常:{}'.format(str(ex)))
                self.create_time = datetime.now()

        if 'save_time' in json_data:
            try:
                self.save_time = datetime.strptime(json_data['save_time'], '%Y-%m-%d %H:%M:%S')
            except Exception as ex:
                self.writeCtaError(u'解释save_time异常:{}'.format(str(ex)))
                self.save_time = datetime.now()

        self.tns_start_price    = json_data.get('tns_start_price',0)
        self.tns_start_date     = json_data.get('tns_start_date',EMPTY_STRING)

    def clean(self):
        """
        清空数据
        :return:
        """
        self.writeCtaLog(u'清空policy数据')
        self.tns_direction = None
        self.tns_start_date = EMPTY_STRING
        self.tns_start_price = 0

#######################################################################
class StrategyDemo_RBreaker(MatrixTemplate):
    """趋势突破模型(数字货币）
    1、；
    2、具体规则：
        //	名称：RANGEBREAK
         //	适应行情：趋势行情
         //   基本思想：入场条件：
         //             分别计算昨天高点，低点，收盘；根据昨天的高低收和今天的开盘计算上下轨道
         //              开多条件：突破上轨；
         //              开空条件：突破下轨；
         //初始参数：
         //LMULT:0.3;1;0.8
         //SMULT:0.3;1;0.8

    配置参考
        {
              "long_mult": 0.8,
              "short_mult": 0.8,
              "mode": "tick",
              "className": "StrategyDemo",
              "kline_name": "D1",
              "kline_period": "day",
              "kline_len": 1,
              "name": "SDemo_btc_usdt_D1,
              "vtSymbol": "btc_usdt",
              "shortSymbol": "btc_usdt",
              "symbol": "btc_usdt",
              "debug": false,
              "auto_init": true,
              "auto_start": true,
              "minDiff": 0.0001,
              "bar_interval": 1,
              "TMinInterval": 1,
              "backtesting": false,
              "inputSS": 1,
              "is_7x24": true
        },
    """
    className = 'StrategyDemo'
    author = u'李来佳'

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting=None):
        """Constructor"""
        super(StrategyDemo_RBreaker, self).__init__(ctaEngine, setting)

        self.paramList.append('inputSS')           # 每次下单得volume数量
        self.paramList.append('symbol')            # symbol，跟vtSymbol一样就行
        self.paramList.append('shortSymbol')       #  短合约名称，暂时用不到
        self.paramList.append('TMinInterval')      # 回测数据的bar时间长度,1 = 一分钟
        self.paramList.append('minDiff')           # 最小跳动
        self.paramList.append('mode')              # 运行模式（tick/bar，一般用tick）

        self.paramList.append('kline_name')        # R-Break得参照K线（缺省日线）
        self.paramList.append('kline_period')      # hour,day
        self.paramList.append('kline_len')         # 1~12

        self.paramList.append('long_mult')         # 上轨修正参数
        self.paramList.append('short_mult')        # 上轨修正参数
        self.paramList.append('fixed_stoplose')    # 止损参数 > 1 ，代表固定多少跳止损; 在 0~1 之间,代表价格百分比计算止损

        self.paramList.append('min_trade_volume')  # 下单量最小单位
        self.paramList.append('max_trade_volume')  # 最大下单volume
        self.paramList.append('min_notional')      # 最小委托金额(币安一般要求10美金

        self.varList.append('pos')
        self.varList.append('entrust')
        self.varList.append('line_lower_band')
        self.varList.append('line_upper_band')
        self.varList.append('base_info')
        self.varList.append('quote_info')

        # 策略在外部设置的参数
        self.inputSS = 1                    # 参数SS，Grid下单的初始volume，范围是1~100，步长为1，默认=1
        self.min_trade_volume = 0.01        # 数字货币，下单量最小单位
        self.max_trade_volume = 100         # 最大下单volume
        self.min_notional = 1               # 最小委托量（price* volume)

        self.long_mult = 0.8                # 参数
        self.short_mult = 0.8               # 参数
        self.fixed_stoplose = 0             # 止损参数, 做多时默认为下轨 > 1 ，代表固定多少跳止损; 在 0~1 之间,代表价格百分比计算止损

        self.cur_short_set = set()          # 当前做空信号集合
        self.cur_long_set = set()           # 当前做多信号集合

        self.minDiff = 1  # 商品的最小交易单位
        self.MinInterval = 1  # 缺省分钟周期
        self.mode = CtaDayBar.TICK_MODE

        self.cur_tick = None  # 最新的tick
        self.curDateTime = None  # 当前Tick时间
        self.cur_price = 0

        # 仓位状态
        self.position = CtaPosition(self)  # 0 表示没有仓位，1 表示持有多头，-1 表示持有空头
        self.pos_long = 0
        self.pos_short = 0
        self.gridpos = 0
        self.position.maxPos = 1000
        self.last_traded_time = datetime.now()  # 上一交易时间
        self.cancel_seconds = 120  # 未成交撤单的秒数

        # 创建网格交易,用来记录
        self.gt = CtaGridTrade(strategy=self, maxlots=10, height=self.minDiff * 20, win=self.minDiff * 20,
                               vol=self.inputSS, minDiff=self.minDiff)

        self.inited = False  # 是否完成了策略初始化
        self.backtesting = False  # 是否为回测

        self.policy = SDemo_Policy(self)             # 执行策略

        self.kline_name = 'D1'
        self.kline_period = PERIOD_DAY
        self.kline_len = 1
        self.lineB = None   # 大周期，4小时线以上/日线

        self.min_rt_upline_touched = False
        self.min_rt_dnline_touched = False

        self.line_lower_band = 0
        self.line_upper_band = 0

        self.base_asset = 'btc'         # 现货代码
        self.quote_asset = 'usdt'       # 参照资金币代码
        self.exchange = EXCHANGE_OKEX
        self.base_info = EMPTY_STRING
        self.quote_info = EMPTY_STRING
        self.virtual_quote = EMPTY_INT

        self.TMinInterval = 1
        self.last_minute = None

        self.is_7x24 = True                 # 数字货币，设置为1

        self.fail_in_hour = {}              # 健康记录检查,记录当前小时，一共失败了多少次下单指令,超过五次就发出警告

        # 读取策略配置json文件
        if setting:
            self.setParam(setting)

            # 分拆 币对.交易所
            symbol_pair = self.vtSymbol.split('.')[0]
            symbol_list = symbol_pair.split('_')

            self.base_asset = symbol_list[0].lower()            # 现货币
            self.quote_asset = symbol_list[1].lower()           # 资金币

            self.base_pos = None                                # 现货币仓位
            self.quote_pos = None                               # 资金币仓位
            self.virtual_quote = 0                              # 虚拟资金币值

            self.writeCtaLog(u'拆分symobl{} => 现货币:{},资金币: {}'.format(self.vtSymbol, self.base_asset, self.quote_asset))
            self.shortSymbol = symbol_pair

            # 创建大周期K线
            lineBigSetting = {}
            lineBigSetting['name'] = self.kline_name
            lineBigSetting['period'] = self.kline_period
            lineBigSetting['barTimeInterval'] = self.kline_len
            lineBigSetting['mode'] = CtaLineBar.TICK_MODE
            lineBigSetting['minDiff'] = self.minDiff
            lineBigSetting['shortSymbol'] = self.shortSymbol
            lineBigSetting['is_7x24'] = self.is_7x24
            bar_class = getCtaBarClass(self.kline_period)
            self.lineB = bar_class(self, self.onBarB, lineBigSetting)

        # 策略内保存过程数据，
        self.dist_fieldnames = ['datetime', 'volume', 'price', 'operation','stop','pos']

        if self.backtesting:
            self.trading = True
            self.onInit()
        else:
            # 实盘时，根据配置得vtSymbol后缀，选择交易所
            exchange = self.vtSymbol.split('.')[-1]
            if exchange == EXCHANGE_OKEX:
                self.exchange = EXCHANGE_OKEX
            elif exchange == EXCHANGE_BINANCE:
                self.exchange = EXCHANGE_BINANCE

    # ----------------------------------------------------------------------
    def onInit(self, force=False):
        """初始化"""
        self.writeCtaLog(u'策略初始化')

        if self.inited:
            if force:
                self.writeCtaLog(u'策略强制初始化')
                # self.inited = False
                # self.trading = False  # 控制是否启动交易
            else:
                self.writeCtaLog(u'已经初始化过，不再执行')
                return

        if not self.backtesting:
            if self.exchange == EXCHANGE_OKEX:
                from vnpy.data.okex.okex_data import OkexData
                history_data = OkexData(self)
            elif self.exchange == EXCHANGE_BINANCE:
                from vnpy.data.binance.binance_data import BinanceData
                history_data = BinanceData(self)
            else:
                msg = u'策略{}没有找到对应的接口数据包:{}'.format(self.name, self.exchange)
                self.writeCtaCritical(msg)

                return False

            try:
                # 初始化5分钟数据
                self.writeCtaLog(u'初始化5分钟数据')
                rt,_ = history_data.get_bars(symbol=self.shortSymbol,
                                             period='5min',
                                             callback=self.lineB.addBar,
                                             bar_freq=5)

                if not rt:
                    self.writeCtaError(u'导入5分钟数据错误')

            except Exception as e:
                self.writeCtaCritical(u'策略初始化加载历史数据失败：{},{}'.format(str(e), traceback.format_exc()))

                return False

        # 得到持久化的Policy中的子事务数据
        self.__loadPolicy()
        self.display_tns()

        self.writeCtaLog(u'策略初始化,加载历史数据完成')

        self.__initPosition()  # 初始持仓数据
        self.inited = True
        if not self.backtesting:
            self.trading = True  # 控制是否启动交易

        self.display_grids()
        self.writeCtaLog(u'策略初始化完成: Strategy({}) Init Finished!'.format(self.name))

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'{}启动'.format(self.name))
        self.trading = True

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.uncompletedOrders.clear()
        self.position.pos = 0
        self.entrust = 0
        self.trading = False
        self.writeCtaLog(u'停止')

    def digits(self, f_num, pickSize):
        """数字精度截取"""
        digit = decimal.Decimal(str(pickSize))
        digit_len = abs(digit.as_tuple().exponent)
        site = pow(10, digit_len)
        d_num = decimal.Decimal(str(f_num))
        tmp = d_num * site
        tmp = math.floor(tmp) / site
        return tmp

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """交易更新"""
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.position.pos))

        # 记录该策略得开平仓，便于复盘
        dist_record = OrderedDict()
        dist_record['datetime'] = trade.tradeTime
        dist_record['volume'] = trade.volume
        dist_record['price'] = trade.price
        if trade.direction == DIRECTION_LONG:
            dist_record['operation'] = 'buy'
        elif trade.direction == DIRECTION_SHORT:
            dist_record['operation'] = 'sell'
        self.save_dist(dist_record)

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """报单更新"""
        # 未执行的订单中，存在是异常，删除
        # self.writeCtaLog(u'报单更新，gateway:{0},orderID:{1}'.format(order.gatewayName,order.orderID))
        orderkey = order.gatewayName + u'.' + str(order.orderID)
        if orderkey in self.uncompletedOrders:

            if order.totalVolume == order.tradedVolume and order.status in [STATUS_ALLTRADED]:
                self.__onOrderAllTraded(order)

            elif order.offset == OFFSET_OPEN and order.status in [STATUS_CANCELLED]:
                # 开仓委托单被撤销
                self.__onOpenOrderCanceled(order)

            elif order.offset != OFFSET_OPEN and order.status in [STATUS_CANCELLED]:
                # 平仓委托单被撤销
                self.__onCloseOrderCanceled(order)

            elif order.status == STATUS_REJECTED:
                if order.offset == OFFSET_OPEN:
                    self.writeCtaCritical(u'OnOrder({})委托单开{}被拒，price:{},total:{},traded:{}，status:{}'
                                          .format(order.vtSymbol, order.direction, order.price, order.totalVolume,
                                                  order.tradedVolume, order.status))
                    self.__onOpenOrderCanceled(order)
                else:
                    self.writeCtaCritical(u'OnOrder({})委托单平{}被拒，price:{},total:{},traded:{}，status:{}'
                                          .format(order.vtSymbol, order.direction, order.price, order.totalVolume,
                                                  order.tradedVolume, order.status))
                    self.__onCloseOrderCanceled(order)
            else:
                self.writeCtaLog(u'委托单未完成,total:{},traded:{},tradeStatus:{}'
                                 .format(order.totalVolume, order.tradedVolume, order.status))
        pass

    def __onOrderAllTraded(self, order):
        """
        订单全部成交
        :param order:
        :return:
        """
        self.writeCtaLog(u'onOrderAllTraded(),{0},委托单全部完成'.format(order.orderTime))
        orderkey = order.gatewayName + u'.' + str(order.orderID)
        msg = u'{} {} {} {} {} {}'.format(
            self.name, self.curDateTime, order.offset, order.direction, order.vtSymbol, order.price, order.tradedVolume)

        # 平多仓完成(sell)
        if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT:
            self.writeCtaLog(u'{}平多仓完成(sell),价格:{}'.format(order.vtSymbol, order.price))
            self.entrust = 0

            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey].get('Grid', None)
            if grid is not None:
                grid.orderRef = EMPTY_STRING
                grid.tradedVolume += order.tradedVolume
                self.gt.save()


        # 开多仓完成
        if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG:
            self.writeCtaLog(u'{}开多单完成'.format(order.vtSymbol))
            self.entrust = 0
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey].get('Grid', None)
            if grid is not None:
                grid.orderRef = EMPTY_STRING
                grid.tradedVolume += order.tradedVolume
                self.gt.save()


        try:
            del self.uncompletedOrders[orderkey]
        except Exception as ex:
            self.writeCtaLog(u'onOrder uncompletedOrders中找不到{},ex:'.format(orderkey, str(ex)))

        self.display_grids()

        if not self.backtesting:
            self.writeCtaNotification(msg)

    def __onOpenOrderCanceled(self, order):
        """
        委托开仓单撤销
        :param order:
        :return:
        """
        self.writeCtaLog(
            u'__onOpenOrderCanceled(),{},{} {} 委托开仓单已撤销'.format(order.orderTime, order.direction, order.vtSymbol))

        self.entrust = 0

        # 回测时不需要执行后续追单
        if self.backtesting:
            return

        if not self.trading:
            self.writeCtaError(u'当前不允许交易')
            return

        orderkey = order.gatewayName + u'.' + str(order.orderID)

        if orderkey in self.uncompletedOrders:
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey].get('Grid', None)
            if grid is not None:
                grid.orderRef = EMPTY_STRING


            del self.uncompletedOrders[orderkey]

    def __onCloseOrderCanceled(self, order):
        """委托平仓单撤销"""
        self.writeCtaLog(u'__onCloseOrderCanceled{},{}委托平仓单已撤销，委托数:{},成交数:{},未成交:{}'
                         .format(order.orderTime, order.vtSymbol,
                                 order.totalVolume, order.tradedVolume,
                                 order.totalVolume - order.tradedVolume))

        orderkey = order.gatewayName + u'.' + str(order.orderID)

        if orderkey in self.uncompletedOrders:
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey].get('Grid', None)
            if grid is not None:
                grid.orderRef = EMPTY_STRING

            del self.uncompletedOrders[orderkey]

        self.entrust = 0

    # ----------------------------------------------------------------------
    def onStopOrder(self, orderRef):
        """停止单更新"""
        self.writeCtaLog(u'{0},停止单触发，orderRef:{1}'.format(self.curDateTime, orderRef))
        pass

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """行情更新
        1、执行延时任务
        2、推送Tick到 lineB
        3、强制清仓逻辑
        4、止损逻辑
        4、加仓逻辑
        :type tick: object
        """
        self.cur_tick = tick
        # 更新策略执行的时间（用于回测时记录发生的时间）
        self.curDateTime = tick.datetime
        self.cur_price = tick.lastPrice

        self.lineB.onTick(copy.copy(tick))

        # 更新持仓 btc.OKEX  usdt.OKEX
        self.base_pos = self.ctaEngine.posBufferDict.get('.'.join([self.base_asset, self.exchange]), None)
        self.quote_pos = self.ctaEngine.posBufferDict.get('.'.join([self.quote_asset, self.exchange]), None)

        # 4、交易逻辑

        # 首先检查是否是实盘运行还是数据预处理阶段
        if not self.inited:
            return

        # 执行撤单逻辑
        self.cancelLogic(tick.datetime)

        # 网格逐一止损/止盈检查
        self.grid_check_stop()

        # 事务判断逻辑
        self.tns_logic()

        # 对买入任务的网格执行逐笔买入动作
        self.tns_execute_long_grids()

        # 对卖出任务的网格执行逐笔卖出动作
        self.tns_excute_short_grids()

        # 每分钟处理逻辑
        if self.last_minute != tick.datetime.minute:
            self.last_minute = tick.datetime.minute

            self.display_position()
            self.display_grids()
            self.display_tns()
            self.putEvent()

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """
        分钟K线数据（仅用于回测时，从策略外部调用"
        :param bar:
        :return:
        """

        if self.mode == CtaDayBar.BAR_MODE and self.backtesting:
            self.curDateTime = bar.datetime + timedelta(seconds=self.TMinInterval * 60)
        else:
            self.curDateTime = bar.datetime

        if  bar.datetime.day == 1 and bar.datetime.hour == 20:
            a = 1

        self.cur_price = bar.close

        if self.inited:
            if self.mode == CtaDayBar.BAR_MODE and self.entrust != 0:
                self.cancelLogic(dt=self.curDateTime)

            # 网格逐一止损/止盈检查
            self.grid_check_stop(bar=bar)

        # 推送bar到大周期K线
        try:
            self.lineB.addBar(copy.copy(bar), bar_freq=self.TMinInterval)  # 需要先生成日线，分钟时才好得到当天的开盘价

        except Exception as ex:
            self.writeCtaError(u'{},{}'.format(str(ex), traceback.format_exc()))

        if len(self.lineB.lineBar) < 3:
            return

        if not self.inited:
            return

        self.tns_logic()

        # 对买入任务的网格执行逐笔买入动作
        self.tns_execute_long_grids()

        # 对卖出任务的网格执行逐笔卖出动作
        self.tns_excute_short_grids()

        self.display_position()
        self.display_grids()
        self.display_tns()

    def grid_check_stop(self, bar=None):
        """
        网格逐一止损/止盈检查
        :return:
        """
        # 多单网格逐一止损/止盈检查：
        if self.position.longPos > 0 and self.entrust == 0:
            has_changed = False
            long_grids = self.gt.getOpenedGrids(direction=DIRECTION_LONG)
            pre_longPos = self.position.longPos
            remove_gids = []
            for g in long_grids:
                grid_close_pos = 0
                # Backtest时使用最低价作为成交价
                cur_price = self.cur_price
                if bar is not None:
                    cur_price = bar.low

                if g.stopPrice > 0 and g.stopPrice > cur_price and g.openStatus and not g.orderStatus:
                    self.writeCtaLog(
                        u'{} onBar触发多单止损线,Bar.close:{},open:{},StopPrice:{},v：{}'.
                            format(self.curDateTime, cur_price, g.openPrice, g.stopPrice,
                                   g.volume))

                    # 创建平多事务
                    if self.tns_sell_long(sell_volume=g.volume):
                        grid_close_pos += g.volume
                        g.openStatus = False
                        g.orderStatus = False
                        has_changed = True
                        remove_gids.append(g.id)

                    else:
                        self.writeCtaLog(u'创建平多网格失败')

            for gid in remove_gids:
                self.writeCtaLog(u'移除做多网格,id={}'.format(gid))
                self.gt.removeGridById(direction=DIRECTION_LONG, id=gid)
                has_changed = True

            if has_changed:
                # 即时执行卖出网格
                self.tns_excute_short_grids()
                self.gt.save()

    # ----------------------------------------------------------------------
    def onBarB(self, bar):
        """
        大周期（4小时~日线）K线OnBar事件

        :param bar:
        :return:
        """
        self.writeCtaLog(self.lineB.displayLastBar())

        # 每个大周期的新Bar，都需要重置一次
        self.min_rt_dnline_touched = False
        self.min_rt_upline_touched = False

        if len(self.lineB.lineBar) < 2:
            return

        if self.lineB.lineBar[-2].high == self.lineB.lineBar[-2].low:
            self.writeCtaError(u'{} 最高价{}=最低价{}，不做计算'.format(self.lineB.lineBar[-2].datetime,self.lineB.lineBar[-2].high , self.lineB.lineBar[-2].low))
            return
        self.line_lower_band = self.lineB.lineBar[-1].open - self.short_mult * (self.lineB.lineBar[-2].high - self.lineB.lineBar[-2].low)

        self.line_upper_band = self.lineB.lineBar[-1].open + self.long_mult * (self.lineB.lineBar[-2].high - self.lineB.lineBar[-2].low)

        self.writeCtaLog(u'{} upperBand:{}, lowerBand:{}'.format(self.lineB.name, self.line_upper_band, self.line_lower_band))

    def tns_logic(self):
        """
        事务逻辑，
        上穿上轨，开多
        下穿下轨，平多
        :return:
        """

        # 上穿上轨，开多
        if self.cur_price > self.line_upper_band and self.position.longPos == 0:
            # 事务开多仓 self.fixedStopLose > 1 ，代表固定多少跳; 在 0~1 之间,代表百分比
            if self.fixed_stoplose > 1:
                stop_price = self.cur_price - self.minDiff * self.fixed_stoplose
            elif 1 > self.fixed_stoplose > 0:
                stop_price = self.cur_price * (1 - self.fixed_stoplose)
            else:
                stop_price = self.line_lower_band
            stop_price = min(stop_price, self.line_lower_band)

            if self.tns_add_long(stop_price=stop_price):
                self.policy.save()  # Policy中的子事务改变了状态，不保存的话会重启后会重复开仓
                self.display_tns()

        # 下穿下轨，平多
        if self.cur_price < self.line_lower_band and self.position.longPos > 0:
            remove_long_grids = []
            for g in self.gt.dnGrids:
                if g.openStatus and g.volume > 0:
                    if self.tns_sell_long(g.volume):
                        g.openStatus = False
                        remove_long_grids.append(g.id)

            for id in remove_long_grids:
                self.gt.removeGridById(direction=DIRECTION_LONG,id=id)

            if self.policy.tns_direction !=DIRECTION_SHORT:
                self.writeCtaLog(u'策略事务从：{} =》 {}'.format(self.policy.tns_direction, DIRECTION_SHORT))
                self.policy.clean()
                self.policy.tns_direction = DIRECTION_SHORT

    def tns_add_long(self, stop_price):
        """
        事务开多仓
        :param stop_price:
        :return:
        """
        assert self.cur_price > stop_price

        # 增加多头事务
        if self.entrust != 0:
            return False

        volume = self.inputSS

        # 存在多单子，不开仓
        opened_volume = 0
        for g in self.gt.dnGrids:
            if g.openStatus and g.volume > 0:
                self.writeCtaLog(u'已经持有多单:{}，不再开仓'.format(g.volume))
                return False

            if g.openStatus == False and g.orderStatus:
                if g.orderRef != EMPTY_STRING:
                    g.orderRef = EMPTY_STRING

                self.writeCtaLog(u'已经存在待开多网格')
                return False

        # 更新policy
        self.policy.tns_direction = DIRECTION_LONG
        self.policy.tns_start_date = self.curDateTime.strftime('%Y-%m-%d')
        self.policy.tns_start_price = self.cur_price

        # 创建做多网格
        grid = CtaGrid(direction=DIRECTION_LONG,
                       openprice=self.cur_price,
                       closeprice=sys.maxsize,
                       stopprice=stop_price,
                       volume=volume)
        grid.orderStatus = True
        self.writeCtaLog(u'创建事务多单,开仓价：{}，数量：{}，止损价:{}，止盈价:{}'
                         .format(grid.openPrice, grid.volume, grid.stopPrice, grid.closePrice))
        self.gt.dnGrids.append(grid)
        self.gt.save()

        return True

    def tns_sell_long(self, sell_volume):
        """
        事务平空(现货减多单）
        :param period:
        :param stop_price:
        :return:
        """
        if self.entrust !=0:
            return False

        if sell_volume <=0:
            return False

        if self.backtesting:
            if self.position.longPos < sell_volume:
                self.writeCtaError(u'当前持仓：{},小于卖出数量:{},不处理卖出信号'.format(self.position.longPos,sell_volume))
                return True
        else:
            if self.base_pos is None:
                msg = u'目前没有{}持仓信息,卖出信号不处理'.format(self.base_asset)
                self.writeCtaError(msg)

                return False

            if self.base_pos.longPosition == 0:
                self.writeCtaLog(u'当前{}持仓为0，卖出信号不处理'.format(self.base_asset))
                return True

            avaliable_volume = self.base_pos.longPosition - self.base_pos.frozen

            if avaliable_volume < sell_volume:
                self.writeCtaLog(u'当前{}持仓：{},冻结:{},剩余可卖数量:{},小于:{}'
                                 .format(self.base_asset, self.base_pos.longPosition, self.base_pos.frozen,
                                         avaliable_volume, sell_volume))

                if avaliable_volume < sell_volume* 0.5 :
                    self.writeCtaLog(u'{} 小于计划卖出{}的一半， 卖出信号不处理'.format(avaliable_volume, sell_volume))
                    return True

                self.writeCtaLog(u'计划卖出数量:{}=>{}'.format(sell_volume, avaliable_volume))
                sell_volume = avaliable_volume
                if sell_volume < self.min_trade_volume:
                    self.writeCtaLog(u'计划卖出数量{}小于最小成交数量:{},卖出信号不处理'
                                     .format(sell_volume,self.min_trade_volume))
                    return True

        # 更新Policy事务
        self.policy.tns_direction = DIRECTION_SHORT
        self.policy.tns_start_date = self.curDateTime.strftime('%Y-%m-%d')

        # 创建事务空单（卖出单）
        grid = CtaGrid(direction=DIRECTION_SHORT,
                       openprice=self.cur_price,
                       closeprice= 0,
                       stopprice=0,
                       volume= sell_volume)

        grid.orderStatus = True
        self.writeCtaLog(u'创建事务空单,卖出价：{}，数量：{}，止损价:{}'
                         .format(grid.openPrice, grid.volume, grid.stopPrice))
        self.gt.upGrids.append(grid)
        self.gt.save()
        return True

    def tns_update_fail(self):
        if self.backtesting:
            return

        cur_hour_fail = self.fail_in_hour.get(self.curDateTime.hour, 0)
        cur_hour_fail += 1
        self.fail_in_hour[self.curDateTime.hour] = cur_hour_fail

        # self.writeCtaError(u'当前小时累计失败:{}次'.format(cur_hour_fail))

    def tns_excute_short_grids(self):
        """
        事务执行减仓网格
        1、找出所有委托状态是True/OpenStatus=False得空网格。
        2、比对volume和traded volume, 如果两者得数量差，大于min_trade_volume，继续发单
        :return:
        """
        if self.entrust != 0:
            self.writeCtaLog(u'{}正在委托中，不执行减仓检查'.format(self.curDateTime))
            return

        if not self.tradingOpen:
            self.writeCtaLog(u'{}当前不是允许交易状态')
            return

        ordering_grid = None
        for grid in self.gt.upGrids:
            # 排除已经执行完毕的网格
            if grid.openStatus:
                continue
            # 排除非委托状态的网格
            if not grid.orderStatus:
                continue
            # 排除存在委托单号的网格
            if len(grid.orderRef)>0:
                continue

            if grid.volume - grid.tradedVolume <= self.min_trade_volume:
                self.tns_finish_short_grid(grid)
                return

            # 定位到首个满足条件的网格，跳出循环
            ordering_grid = grid
            break

        # 没有满足条件的网格
        if ordering_grid is None:
            return

        sell_volume = EMPTY_FLOAT

        if self.backtesting:
            cur_pos = self.ctaEngine.posBufferDict.get(self.vtSymbol,None)

            if cur_pos is None:
                self.writeCtaError(u'当前{}持仓查询不到'.format(self.vtSymbol))
                return
            if cur_pos.longPosition - cur_pos.frozen <= 0:
                self.writeCtaError(u'总量:{},冻结:{},不足卖出'
                                 .format(cur_pos.longPosition, cur_pos.frozen, ordering_grid.volume))
                return

            if cur_pos.longPosition-cur_pos.frozen >= ordering_grid.volume - ordering_grid.tradedVolume:
                sell_volume = ordering_grid.volume - ordering_grid.tradedVolume

                self.writeCtaLog(u'总量:{},冻结:{},网格减仓量:{},已成交:{},预计委托卖出:{}'
                                 .format(cur_pos.longPosition, cur_pos.frozen, ordering_grid.volume, ordering_grid.tradedVolume, sell_volume))
            else:
                volume = ordering_grid.volume
                tradedVolume = ordering_grid.tradedVolume

                sell_volume = cur_pos.longPosition-cur_pos.frozen
                if tradedVolume > 0:
                    ordering_grid.tradedVolume = ordering_grid.volume - sell_volume
                else:
                    ordering_grid.volume = sell_volume
                self.writeCtaLog(u'总量:{},冻结:{},网格减仓量:{}=>{},已成交:{}={},预计委托卖出:{}'
                                 .format(cur_pos.longPosition, cur_pos.frozen, volume, ordering_grid.volume,
                                         tradedVolume, ordering_grid.tradedVolume, sell_volume))
        else:
            if self.base_pos is None:
                self.writeCtaError(u'当前{}持仓查询不到'.format(self.base_asset))
                return

            # 根据市场计算，前5档买单数量
            market_ask_volumes = self.cur_tick.askVolume1 + self.cur_tick.askVolume2 + self.cur_tick.askVolume3 + self.cur_tick.askVolume4 + self.cur_tick.askVolume5
            market_bid_volumes = self.cur_tick.bidVolume1 + self.cur_tick.bidVolume2 + self.cur_tick.bidVolume3 + self.cur_tick.bidVolume4 + self.cur_tick.bidVolume5

            # 查询合约的最小成交数量
            contract = self.ctaEngine.mainEngine.getContract(self.vtSymbol)
            if contract and contract.volumeTick > self.min_trade_volume:
                self.min_trade_volume = contract.volumeTick

            sell_volume = ordering_grid.volume - ordering_grid.tradedVolume

            if sell_volume < self.min_trade_volume:
                self.tns_finish_short_grid(ordering_grid)
                return

            if sell_volume > self.max_trade_volume:
                self.writeCtaLog(u'卖出{}超过单次最高数量:{}'.format(sell_volume, self.max_trade_volume))
                sell_volume = self.max_trade_volume

            if sell_volume > min(market_bid_volumes / 5, market_ask_volumes / 5):
                self.writeCtaLog(u'卖出{} {}，超过叫买量/5:{} 或叫卖量/5:{},降低为:{}'
                                 .format(self.base_asset, sell_volume, market_bid_volumes / 5, market_ask_volumes / 5,
                                         min(market_bid_volumes / 5, market_ask_volumes / 5)))
                sell_volume = min(market_bid_volumes / 5, market_ask_volumes / 5)

                sell_volume = self.digits(sell_volume, self.min_trade_volume)

        if sell_volume < self.min_trade_volume:
            self.writeCtaError(u'{} 计算的减仓={}：不满足减仓数量最低要求'.format(self.curDateTime, sell_volume))
            return

        if self.backtesting:
            sell_price = self.cur_price - self.minDiff
        else:
            sell_price = self.cur_tick.askPrice1 - self.minDiff
        self.writeCtaLog(u'{} 减多仓：减仓价为:{},减仓手数:{}'.format(self.curDateTime, sell_price, sell_volume))

        ref = self.sell(price=sell_price, volume=sell_volume, orderTime=self.curDateTime, grid=ordering_grid)

        if ref is None or len(ref) == 0:
            self.writeCtaError(u'sell失败')
            return

        if not self.backtesting and self.base_pos :
            self.writeCtaLog(u'降低持仓basePos：{}=>{}'.format(self.base_pos.longPosition, self.base_pos.longPosition-sell_volume))
            self.base_pos.longPosition -= sell_volume
            self.base_pos.frozen += sell_volume

    def tns_finish_short_grid(self, grid):
        """
        做空网格（卖出多单）执行完成
        :param grid:
        :return:
        """
        self.writeCtaLog(u'卖出网格执行完毕,price:{},v:{},traded:{}'.format(grid.openPrice, grid.volume, grid.tradedVolume))
        grid.orderStatus = False
        grid.openStatus = True
        volume = grid.volume
        tradedVolume = grid.tradedVolume
        if grid.tradedVolume > 0:
            grid.volume = grid.tradedVolume
        grid.tradedVolume = 0
        self.writeCtaLog(u'设置{}网格委托状态为: {}，完成状态:{} v:{}=>{},traded:{}=>{}'
                         .format(grid.direction,  grid.orderStatus, grid.openStatus, volume, grid.volume, tradedVolume,
                                 grid.tradedVolume))
        self.position.closePos(direction=DIRECTION_SHORT,vol=grid.volume)

        dist_record = OrderedDict()
        dist_record['datetime'] = self.curDateTime
        dist_record['volume'] = grid.volume
        dist_record['price'] = self.cur_price
        dist_record['operation'] = 'sell-finished'
        self.save_dist(dist_record)

        id = grid.id
        try:
            self.gt.removeGridById(direction=DIRECTION_SHORT,id=id)
        except Exception as ex:
            self.writeCtaError(u'移除卖出网格失败,id={},ex:{}'.format(id, str(ex)))

        self.gt.save()
        self.putEvent()

    def tns_execute_long_grids(self):
        """
        事务执行买入
        1、找出所有委托状态是True/OpenStatus=False得多网格。
        2、比对volume和traded volume, 如果两者得数量差，大于min_trade_volume，继续发单
        :return:
        """
        if self.entrust != 0:
            if len(self.uncompletedOrders) == 0:
                self.writeCtaLog(u'当前不存在未完成委托单，重置委托状态')
                self.entrust = 0

            self.writeCtaLog(u'{}正在委托中，不执行买入多仓'.format(self.curDateTime))
            return

        if not self.tradingOpen:
            self.writeCtaLog(u'{}当前不是允许交易状态')
            return

        ordering_grid = None
        for grid in self.gt.dnGrids:
            # 排除已经执行完毕的网格
            if grid.openStatus:
                continue
            # 排除非委托状态的网格
            if not grid.orderStatus:
                continue
            # 排除存在委托单号的网格
            if len(grid.orderRef) > 0:
                continue

            # 满足买入数量，就完成这个买入交易
            if grid.volume - grid.tradedVolume < self.min_trade_volume and grid.tradedVolume > 0:
                self.tns_finish_long_grid(grid)
                return

            # 定位到首个满足条件的网格，跳出循环
            ordering_grid = grid
            break

        # 没有满足条件的网格
        if ordering_grid is None:
            return

        # 仍需要买入的数量
        buy_volume = ordering_grid.volume - ordering_grid.tradedVolume

        if not self.backtesting:
            if self.quote_pos is None:
                self.writeCtaError(u'现货:{}没有持仓信息'.format(self.quote_asset))
                return
            avaliable_quote = self.quote_pos.longPosition - self.quote_pos.frozen
            if avaliable_quote <= 0:
                self.writeCtaError(u'现货:{} 持仓:{},冻结：{},可用资金不足买入'.format(self.quote_asset, self.quote_pos.longPosition,
                                                                        self.quote_pos.frozen))
                return

            if avaliable_quote < self.cur_price * buy_volume:
                self.writeCtaLog(
                    u'当前可用{}:{}，不足已{}买入:{} '.format(self.quote_asset, avaliable_quote, self.cur_price, buy_volume))
                buy_volume = avaliable_quote / self.cur_price
                buy_volume = self.digits(buy_volume, self.min_trade_volume)

                if buy_volume >= self.min_trade_volume:
                    volume = ordering_grid.volume
                    ordering_grid.volume = ordering_grid.tradedVolume + buy_volume
                    self.writeCtaLog(u'调整网格多单目标:{}=>{}'.format(volume, ordering_grid.volume))
                else:
                    return

            # 根据市场计算，前5档买单数量
            market_ask_volumes = self.cur_tick.askVolume1 + self.cur_tick.askVolume2 + self.cur_tick.askVolume3 + self.cur_tick.askVolume4 + self.cur_tick.askVolume5
            market_bid_volumes = self.cur_tick.bidVolume1 + self.cur_tick.bidVolume2 + self.cur_tick.bidVolume3 + self.cur_tick.bidVolume4 + self.cur_tick.bidVolume5

            # 查询合约的最小成交数量
            contract = self.ctaEngine.mainEngine.getContract(self.vtSymbol)
            if contract and contract.volumeTick > self.min_trade_volume:
                self.min_trade_volume = contract.volumeTick

            if buy_volume > self.max_trade_volume:
                self.writeCtaLog(u'买入{}超过单次最高数量:{}'.format(buy_volume, self.max_trade_volume))
                buy_volume = self.max_trade_volume

            if buy_volume > min(market_bid_volumes / 5, market_ask_volumes / 5):
                self.writeCtaLog(u'买入{} {}，超过叫买量/5:{} 或叫卖量/5:{},降低为:{}'
                                 .format(self.base_asset, buy_volume, market_bid_volumes / 5, market_ask_volumes / 5,
                                         min(market_bid_volumes / 5, market_ask_volumes / 5)))
                buy_volume = min(market_bid_volumes / 5, market_ask_volumes / 5)

                buy_volume = self.digits(buy_volume, self.min_trade_volume)

        if buy_volume < self.min_trade_volume:
            self.writeCtaError(u'{} 计算的买入={}：不满足买入数量最低要求'.format(self.curDateTime, buy_volume))
            return

        if self.backtesting:
            buy_price = self.cur_price + self.minDiff
        else:
            buy_price = self.cur_tick.bidPrice1 + self.minDiff

        self.writeCtaLog(
            u'{} 执行开多仓：开仓价为:{},开仓手数:{}'.format(self.curDateTime, buy_price, buy_volume))

        ref = self.buy(price=buy_price, volume=buy_volume, orderTime=self.curDateTime, grid=ordering_grid)
        if ref is None or len(ref) == 0:
            self.writeCtaError(u'开多失败')
            return

        if not self.backtesting and self.quote_pos:
            self.writeCtaLog(u'降低持仓QuotePos：{}=>{}'.format(self.quote_pos.longPosition,
                                                           self.quote_pos.longPosition - buy_volume * buy_price))
            self.base_pos.longPosition -= buy_volume * buy_price
            self.base_pos.frozen += buy_volume * buy_price

    def tns_finish_long_grid(self, grid):
        """
        做多网格（买入多单）执行完成
        :param grid:
        :return:
        """
        self.writeCtaLog(u'多网格事务执行完毕,price:{},v:{},traded:{}'.format(grid.openPrice, grid.volume, grid.tradedVolume))
        grid.orderStatus = False
        grid.openStatus = True
        volume = grid.volume
        tradedVolume = grid.tradedVolume
        if grid.tradedVolume > 0:
            grid.volume = grid.tradedVolume
        grid.tradedVolume = 0
        self.writeCtaLog(u'设置{}网格:委托状态为: {}，完成状态:{} v:{}=>{},traded:{}=>{}'
                         .format(grid.direction, grid.orderStatus, grid.openStatus, volume, grid.volume,
                                 tradedVolume,
                                 grid.tradedVolume))
        self.position.openPos(direction=DIRECTION_LONG,vol=grid.volume)
        self.gt.save()

        dist_record = OrderedDict()
        dist_record['datetime'] = self.curDateTime
        dist_record['volume'] = grid.volume
        dist_record['price'] = self.cur_price
        dist_record['operation'] = 'buy-finished'
        self.save_dist(dist_record)

        self.putEvent()

    def buy(self, price, volume, stop=False, orderTime=None, grid=None):
        """
        重构模板开多处理模块
        :param price: 开仓价格
        :param volume: 开仓数量
        :param stop: 停止单（这里不用）
        :param orderTime：开仓时间
        :param grid: 网格，这里是动态创建的
        :return:
        """
        if not self.trading:
            self.writeCtaError(u'当前不允许交易')
            return ''
        if orderTime is None:
            orderTime = datetime.now()

        # 修正价格/下单数量
        price = self.ctaEngine.roundToPriceTick(price=price, priceTick=self.minDiff)
        volume = self.ctaEngine.roundToVolumeTick(volume=volume, volumeTick=self.min_trade_volume)

        # 检查是否有足够得quote货币
        if self.quote_pos is not None:
            if volume * price > self.quote_pos.longPosition - self.quote_pos.frozen:
                self.writeCtaError(u'{}开多失败,price:{},vol:{}，{}持仓:{},冻结:{}'
                                   .format(self.vtSymbol, price, volume,self.quote_asset, self.quote_pos.longPosition, self.quote_pos.frozen))
                return ''

        # 检查最小成交额度 现货币*数量
        if self.min_notional > 0 and self.min_notional > price * volume:
            self.writeCtaError(u'{}开多失败,price:{},vol:{}，未满足最小成交要求:{}'
                               .format(self.vtSymbol, price, volume,self.min_notional ))
            return ''

        # 下委托单，买入
        ref = self.ctaEngine.sendOrder(self.vtSymbol, CTAORDER_BUY, price, volume, strategy=self)
        if not ref:
            self.writeCtaError(u'{}开多失败,price:{},vol:{}'.format(self.vtSymbol, price, volume))
            return ''

        self.entrust = 1
        self.uncompletedOrders[ref] = {'SYMBOL': self.vtSymbol, 'DIRECTION': DIRECTION_LONG,
                                       'OFFSET': OFFSET_OPEN, 'Volume': volume,
                                       'Price': price, 'TradedVolume': EMPTY_INT,
                                       'OrderTime': orderTime,
                                       'Retry': 0}

        if grid is not None:
            grid.openStatus = False
            grid.orderStatus = True
            grid.orderRef = ref
            grid.openPrice = price
            if volume >= self.min_trade_volume:
                grid.volume = volume
            self.uncompletedOrders[ref]['Grid'] = grid
            self.writeCtaLog(u'多网格买入:{}=>{},v:{}'.format(grid.openPrice,grid.closePrice,grid.volume))

        return ref

    def sell(self, price, volume, stop=False, orderTime=None, grid=None):
        """
        重构模块平多逻辑
        :param price: 平仓价格
        :param volume: 平仓数量
        :param stop: 停止单，这里不使用
        :param orderTime: 下单时间
        :param grid: 网格，这里必须是上层逻辑创建好，传入的
        :return:
        """
        if not self.trading :
            self.writeCtaError(u'{}当前不允许交易'.format(self.curDateTime))
            return ''

        if orderTime is None:
            orderTime = datetime.now()

        if grid is None:
            self.writeCtaError(u'sell(),网格grid参数不能为None')
            return ''

        # 修正价格/数量
        price = self.ctaEngine.roundToPriceTick(price=price, priceTick=self.minDiff)
        sell_volume = self.ctaEngine.roundToVolumeTick(volume=volume, volumeTick=self.min_trade_volume)

        if grid is not None and self.base_pos is not None:
            if grid.volume > self.base_pos.longPosition - self.base_pos.frozen > self.min_trade_volume:
                self.writeCtaLog(
                    u'修改平仓数量:{}=>{}'.format(grid.volume, self.base_pos.longPosition - self.base_pos.frozen))
                volume = self.base_pos.longPosition - self.base_pos.frozen
                if volume > self.min_trade_volume:
                    grid.volume = volume

        ref = self.ctaEngine.sendOrder(self.vtSymbol, CTAORDER_SELL, price, sell_volume, strategy=self)
        if not ref:
            self.writeCtaError(u'{}平多失败,price:{},vol:{}'.format(self.vtSymbol, price, sell_volume))
            return ''

        self.writeCtaLog(u'sent sell, ref:{}'.format(ref))
        self.uncompletedOrders[ref] = {'SYMBOL': self.vtSymbol, 'DIRECTION': DIRECTION_SHORT,
                                       'OFFSET': OFFSET_CLOSE, 'Volume': sell_volume,
                                       'Price': price, 'TradedVolume': EMPTY_INT,
                                       'OrderTime': orderTime,
                                       'Retry': 0}

        if grid is not None:
            grid.openStatus = False
            grid.orderStatus = True
            grid.orderRef = ref
            grid.volume = volume
            self.uncompletedOrders[ref]['Grid'] = grid
            self.writeCtaLog(u'网格卖出:{}=>{},v:{}'.format(grid.openPrice, grid.closePrice, grid.volume))

        self.entrust = -1
        return ref

    def __initPosition(self):
        """
        初始化Positin
        使用网格的持久化，获取开仓状态的多空单，更新
        :return:
        """
        self.writeCtaLog(u'__initPosition(),初始化持仓')
        if len(self.gt.upGrids) <= 0:
            self.position.shortPos = 0
            # 加载已开仓的空单数据，网格JSON
            short_grids = self.gt.load(direction=DIRECTION_SHORT, openStatusFilter=[True,False])
            if len(short_grids) == 0:
                self.writeCtaLog(u'没有持久化的空单数据')
                self.gt.upGrids = []

            else:
                self.gt.upGrids = short_grids
                for sg in short_grids:
                    if len(sg.orderRef) > 0 :
                        self.writeCtaLog(u'清除委托单：{}'.format(sg.orderRef))
                        sg.orderRef = EMPTY_STRING
                    self.writeCtaLog(u'加载持仓空单,价格:{},数量:{}手,开仓状态:{},委托状态:{}'
                                     .format(sg.openPrice, sg.volume,sg.openStatus, sg.orderStatus))

        if len(self.gt.dnGrids) <= 0:
            # 加载已开仓的多数据，网格JSON
            self.position.longPos = 0
            long_grids = self.gt.load(direction=DIRECTION_LONG, openStatusFilter=[True])
            if len(long_grids) == 0:
                self.writeCtaLog(u'没有持久化的多单数据')
                self.gt.dnGrids = []
            else:
                self.gt.dnGrids = long_grids
                for lg in long_grids:
                    if len(lg.orderRef) > 0:
                        self.writeCtaLog(u'清除委托单：{}'.format(lg.orderRef))
                        lg.orderRef = EMPTY_STRING
                    if lg.openStatus and lg.volume > 0:
                        self.position.openPos(DIRECTION_LONG,lg.volume)

                    self.writeCtaLog(u'加载持仓多单,价格:{},数量:{}手,开仓状态:{},委托状态:{}'.
                                     format(lg.openPrice, lg.volume,lg.openStatus, lg.orderStatus))

        self.position.pos = self.position.longPos + self.position.shortPos

        self.writeCtaLog(
            u'{}加载持久化数据完成，多单:{}，空单:{},共:{}手'.format(self.name, self.position.longPos, abs(self.position.shortPos),
                                                    self.position.pos))
        self.gridpos = self.position.pos

    def __loadPolicy(self):
        """加载policy"""
        self.writeCtaLog(u'__initPosition(),初始化Policy')

        self.policy.load()
        self.writeCtaLog(u'Policy:{}'.format(self.policy.toJson()))

    def display_grids(self):
        """更新网格显示信息"""
        if not self.inited:
            return
        self.upGrids = self.gt.toStr(direction=DIRECTION_SHORT)
        self.writeCtaLog(self.upGrids)

        self.dnGrids = self.gt.toStr(direction=DIRECTION_LONG)
        self.writeCtaLog(self.dnGrids)

    def display_tns(self):
        self.writeCtaLog(u'{} 当前价格:{},前事务:{}'.format(self.curDateTime, self.cur_price, self.policy.toJson()))
        #                 bar 碰触上轨/实时 碰触下轨/实时, 叉位/实时

    def display_position(self):
        if not self.inited :
            return

        if self.backtesting:
            self.writeCtaLog(u'Pos:{}, GridPos:{}'.format(self.pos, self.position.longPos))
            base_pos = self.ctaEngine.posBufferDict.get('{}'.format(self.vtSymbol),None)
            if base_pos is not None:
                self.base_info = '[{}]:{}'.format(self.base_asset, base_pos.longPosition)

            c,a,p,pl = self.ctaEngine.getAccountInfo()
            self.quote_info = '[{}]:{},'.format(self.quote_asset, a)
            return


        self.base_pos = self.ctaEngine.posBufferDict.get('.'.join([self.base_asset, self.exchange]), None)
        self.quote_pos = self.ctaEngine.posBufferDict.get('.'.join([self.quote_asset, self.exchange]), None)

        if self.base_pos is not None:
            self.base_info = '[{}]:{}'.format(self.base_asset, self.base_pos.longPosition)
        if self.quote_pos is not None:
            self.quote_info = '[{}]:{},'.format(self.quote_asset, self.quote_pos.longPosition)

    # ----------------------------------------------------------------------
    def cancelAllOrders(self):
        """
        重载撤销所有正在进行得委托
        :return:
        """
        self.writeCtaLog(u'撤销所有正在进行得委托')
        self.cancelLogic(dt=datetime.now(), force=True, reopen=False)

    def cancelLogic(self, dt, force=False, reopen=True):
        """
        撤单逻辑,在本策略，只撤单，不做追单
        :param dt:  检查时间
        :param force:  强制撤单
        :param reopen: 是否追开
        :return:
        """

        if len(self.uncompletedOrders) < 1:
            return

        canceled_keys = []
        order_keys = list(self.uncompletedOrders.keys())

        for order_key in order_keys:
            order = self.uncompletedOrders[order_key]
            order_time = order['OrderTime']
            order_volume = order['Volume'] - order['TradedVolume']
            order_price = order['Price']
            order_direction = order['DIRECTION']
            order_offset = order['OFFSET']

            if ((dt - order_time).seconds > self.cancel_seconds) \
                    or force:  # 超过设置的时间还未成交
                self.writeCtaWarning(
                    u'{} {} 超时{}秒未成交，取消委托单：key:{},v:{},p:{},dir:{},offset:{},{}'.format(dt, self.vtSymbol,
                                                                                 (dt - order_time).seconds, order_key,
                                                                                 order_volume, order_price,
                                                                                 order_direction, order_offset, order_time))

                self.cancelOrder(str(order_key))
                grid = order.get('Grid',None)
                if grid is not None:
                    self.writeCtaLog('撤销{}网格{}的{}委托,{},价格:{},v:{},已成交:{}'
                                     .format(grid.direction, grid.type, order_direction,
                                             self.vtSymbol, order_price, order['Volume'], order['TradedVolume']))
                    grid.orderRef = EMPTY_STRING
                    self.gt.save()

                canceled_keys.append(order_key)

        # 删除撤单的订单
        for key in canceled_keys:
            if key in self.uncompletedOrders:
                self.writeCtaLog(u'删除orderID:{0}'.format(key))
                del self.uncompletedOrders[key]

        if len(self.uncompletedOrders) == 0:
            self.entrust = 0

    def save_dist(self, dist_data):
        """
        保存过程记录
        :param dist_data:
        :return:
        """

        if self.backtesting:
            save_path = self.ctaEngine.get_logs_path()
        else:
            save_path = self.ctaEngine.get_data_path()
        try:
            file_name = os.path.abspath(os.path.join(save_path, u'{}_dist.csv'.format(self.name)))
            self.append_data(file_name=file_name, dict_data=dist_data, field_names=self.dist_fieldnames)
        except Exception as ex:
            self.writeCtaError(u'save_dist exception:{} {}'.format(str(ex), traceback.format_exc()))

    # ----------------------------------------------------------------------
    def saveData(self):
        """保存过程数据"""
        # 保存K线
        self.writeCtaLog(u'保存过程数据')
        if not self.backtesting:
            self.writeCtaLog(u'不在回测，过滤保存过程数据')
            return



