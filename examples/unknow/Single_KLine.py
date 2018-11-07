# -*- coding: utf-8 -*-
"""
多周期显示K线，
时间点同步
华富资产/李来佳
"""

import sys
import os
import ctypes
import platform
system = platform.system()

# 将repostory的目录，作为根目录，添加到系统环境中。
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..' , '..'))
sys.path.append(ROOT_PATH)


from vnpy.trader.uiKLine.uiCrosshair import Crosshair
from vnpy.trader.uiKLine.uiKLine import  *


class GridKline(QtWidgets.QWidget):

    def __init__(self, parent=None):
        self.parent = parent
        super(GridKline, self).__init__(parent)

        self.periods = ['M5','M30','H4']
        self.main_indicator_dict = {}
        self.main_indicator_dict['M5'] = ['upper', 'middle', 'lower','MA169']
        self.main_indicator_dict['M30'] = ['upper', 'middle', 'lower','MA169']
        self.main_indicator_dict['H4'] = ['upper', 'middle', 'lower']

        self.kline_dict = {}

        self.initUI()

    def initUI(self):
        gridLayout = QtWidgets.QGridLayout()

        for period_name in self.periods:
            canvas = KLineWidget(display_vol=False, display_sub=True)
            canvas.show()
            canvas.KLtitle.setText('{}'.format(period_name), size='18pt')
            canvas.title = '{}'.format(period_name)
            main_indicators = self.main_indicator_dict.get(period_name,[])
            for indicator in main_indicators:
                canvas.add_indicator(indicator=indicator, is_main=True)
                canvas.add_indicator(indicator=indicator, is_main=True)
                canvas.add_indicator(indicator=indicator, is_main=True)
            #canvas.add_indicator(indicator='sk', is_main=False)
            #canvas.add_indicator(indicator='sd', is_main=False)

            self.kline_dict[period_name] = canvas
            # 注册重定向事件
            canvas.relocate_notify_func = self.onRelocate
        gridLayout.addWidget(self.kline_dict['M5'], 0, 1)
        gridLayout.addWidget(self.kline_dict['M30'], 0, 2)
        gridLayout.addWidget(self.kline_dict['H4'], 0, 3)

        self.setLayout(gridLayout)

        self.show()

        self.load_multi_kline()

    # ----------------------------------------------------------------------
    def load_multi_kline(self):
        """加载多周期窗口"""

        try:
            for period_name in self.periods:
                canvas = self.kline_dict.get(period_name,None)
                if canvas is not None:
                    df = pd.read_csv('logs/S48_J99_{}.csv'.format(period_name))
                    if 'openInterest' not in df.columns:
                        df['openInterest'] = 0
                    df = df.set_index(pd.DatetimeIndex(df['datetime']))
                    canvas.loadData(df, main_indicators=self.main_indicator_dict.get(period_name,[]))

            trade_list_file = 'logs/S103_M5_0929_1707_TradeList_20180929_1709.csv'
            if os.path.exists(trade_list_file):
                df_trade = pd.read_csv(trade_list_file)
                self.kline_dict['M5'].add_signals(df_trade)
                self.kline_dict['M30'].add_signals(df_trade)
                self.kline_dict['H4'].add_signals(df_trade)
            """
            tns_file = 'logs/S43_I_Resonance_tns_20180620_1504.csv'
            if os.path.exists(tns_file):
                df_tns = pd.read_csv(tns_file)
                self.kline_dict['h2'].add_trans_df(df_tns)
                self.kline_dict['d'].add_trans_df(df_tns)

            markup_file = 'logs/S43_I_Resonance_dist_20180620_1702.csv'
            if os.path.exists(markup_file):
                df_markup = pd.read_csv(markup_file)
                df_markup = df_markup[['datetime', 'price', 'operation']]
                df_markup.rename(columns={'operation': 'markup'}, inplace=True)
                self.kline_dict['m30'].add_markups(df_markup=df_markup, include_list=['M30_H1'], exclude_list=['buy', 'short', 'sell', 'cover'])
                self.kline_dict['h1'].add_markups(df_markup=df_markup,
                                                   include_list=['H1_H2'],
                                                   exclude_list=['buy', 'short', 'sell', 'cover'])
                self.kline_dict['h2'].add_markups(df_markup=df_markup,
                                                   include_list=['H2_H4'],
                                                   exclude_list=['buy', 'short', 'sell', 'cover'])
            """
        except Exception as ex:
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, 'Exception', u'Load data Exception',
                                          QtWidgets.QMessageBox.Cancel,
                                          QtWidgets.QMessageBox.NoButton)

            return

    def onRelocate(self,window_id, t_value, count_k):
        """
        重定位所有周期的时间
        :param window_id:
        :param t_value:
        :return:
        """
        for period_name in self.periods:
            try:
                canvas = self.kline_dict.get(period_name, None)
                if canvas is not None:
                    canvas.relocate(window_id,t_value, count_k)
            except Exception as ex:
                traceback.print_exc()
########################################################################
# 功能测试
########################################################################

from vnpy.trader.uiQt import createQApp
from vnpy.trader.vtFunction import loadIconPath


def  display_multi_grid():

    qApp = createQApp()
    qApp.setWindowIcon(QtGui.QIcon(loadIconPath('dashboard.ico')))
    w = GridKline()
    w.showMaximized()
    sys.exit(qApp.exec_())

if __name__ == '__main__':

#
    ## 界面设置
    qApp = createQApp()
    qApp.setWindowIcon(QtGui.QIcon(loadIconPath('dashboard.ico')))
    #
    # K线界面
    try:
        ui = KLineWidget(display_vol=False,display_sub=True)
        ui.show()
        ui.KLtitle.setText('btc()',size='20pt')
        ui.add_indicator(indicator='ema34', is_main=True)
        ui.add_indicator(indicator='ema55', is_main=True)
        ui.add_indicator(indicator='ema120', is_main=True)
        ui.add_indicator(indicator='sk',is_main=False)
        ui.add_indicator(indicator='sd', is_main=False)

        # 这里加载基础K线
        df = pd.read_csv('logs/SDemo_btc_usdt_M5.csv')
        if 'openInterest' not in df.columns:
            df['openInterest'] = 0
        df = df.set_index(pd.DatetimeIndex(df['datetime']))

        ui.loadData(df, main_indicators=['ema34','ema55','ema120'], sub_indicators=['sk','sd'])

        # 这里加载每次回测后的成交记录
        trade_list_file = 'logs/S_M5_0929_1644_TradeList_20180929_1647.csv'
        if os.path.exists(trade_list_file):
            df_trade = pd.read_csv(trade_list_file)
            ui.add_signals(df_trade)

        ui.showMaximized()

        sys.exit(qApp.exec_())

        #display_multi_grid()

    except Exception as ex:
        print(u'exception:{},trace:{}'.format(str(ex), traceback.format_exc()))
