# -*- coding: utf-8 -*-
"""
多周期显示K线，
时间点同步

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

        self.periods = ['M5', 'M15', 'H1', 'D']
        self.kline_dict = {}

        self.initUI()

    def initUI(self):
        gridLayout = QtWidgets.QGridLayout()

        for period_name in self.periods:
            canvas = KLineWidget(display_vol=False, display_sub=True)
            canvas.show()
            canvas.KLtitle.setText('eth_usdt({})'.format(period_name), size='18pt')
            canvas.title = 'eth_usdt({})'.format(period_name)
            canvas.add_indicator(indicator='upper', is_main=True)
            canvas.add_indicator(indicator='middle', is_main=True)
            canvas.add_indicator(indicator='lower', is_main=True)
            canvas.add_indicator(indicator='sk', is_main=False)
            canvas.add_indicator(indicator='sd', is_main=False)
            self.kline_dict[period_name] = canvas
            # 注册重定向事件
            canvas.relocate_notify_func = self.onRelocate

        gridLayout.addWidget(self.kline_dict[self.periods[0]], 0, 1)
        gridLayout.addWidget(self.kline_dict[self.periods[1]], 0, 2)

        gridLayout.addWidget(self.kline_dict[self.periods[2]], 1, 1)
        gridLayout.addWidget(self.kline_dict[self.periods[3]], 1, 2)

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
                    df = pd.read_csv('data/eth_usdt_{}.csv'.format(period_name))
                    df = df.set_index(pd.DatetimeIndex(df['datetime']))
                    canvas.loadData(df, main_indicators=['upper', 'middle', 'lower'], sub_indicators=['sk', 'sd'])

            """
            trade_list_file = 'logs/S01_Btc_0913_1445_TradeList_20180913_1518.csv'
            if os.path.exists(trade_list_file):
                df_trade = pd.read_csv(trade_list_file)
                self.kline_dict['h1'].add_signals(df_trade)

            tns_file = 'logs/S41_Btc_DayTrend_DTOSC_tns_20180626_2352.csv'
            if os.path.exists(tns_file):
                df_tns = pd.read_csv(tns_file)
                self.kline_dict['h6'].add_trans_df(df_tns)
                self.kline_dict['h12'].add_trans_df(df_tns)
                self.kline_dict['d'].add_trans_df(df_tns)

            markup_file = 'logs/S41_Btc_DayTrend_DTOSC_dist_20180626_2352.csv'
            if os.path.exists(markup_file):
                df_markup = pd.read_csv(markup_file)
                df_markup = df_markup[['datetime', 'price', 'operation']]
                df_markup.rename(columns={'operation': 'markup'}, inplace=True)
                self.kline_dict['h2'].add_markups(df_markup=df_markup, include_list=['h246_goldencross','h246_deadcross'],
                                                   exclude_list=['buy', 'short', 'sell', 'cover'])
            """
        except Exception as ex:
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, 'Exception', u'Load data Exception:{}'.format(str(ex)),
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

    # K线界面
    try:

        display_multi_grid()

    except Exception as ex:
        print(u'exception:{},trace:{}'.format(str(ex), traceback.format_exc()))
