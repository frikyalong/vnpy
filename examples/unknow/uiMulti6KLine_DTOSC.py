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

class SingleKline(QtWidgets.QWidget):

    def __init__(self, parent=None, period_name=None):
        self.parent = parent
        super(SingleKline, self).__init__(parent)
        self.period_name = period_name
        self.canvas = None

        self.initUI()

        #self.loadData()

    def initUI(self):

        vbox = QtWidgets.QVBoxLayout()

        self.canvas = KLineWidget(display_vol=False, display_sub=True)
        self.canvas.show()
        self.canvas.KLtitle.setText('btc_usd({})'.format(self.period_name), size='18pt')
        self.canvas.add_indicator(indicator='ma5', is_main=True)
        self.canvas.add_indicator(indicator='ma10', is_main=True)
        self.canvas.add_indicator(indicator='ma18', is_main=True)
        self.canvas.add_indicator(indicator='sk', is_main=False)
        self.canvas.add_indicator(indicator='sd', is_main=False)
        #canvas.loadData(pd.DataFrame.from_csv('data/btc_{}.csv'.format(p)),
        #                main_indicators=['ma5', 'ma10', 'ma18'],
        #                sub_indicators=['sk', 'sd'])

        vbox.addWidget(self.canvas)
        self.setLayout(vbox)

    def loadData(self):
        if self.canvas:
            df = pd.read_csv('data/btc_usd{}.csv'.format(self.period_name))
            df = df.set_index(pd.DatetimeIndex(df['datetime']))

            self.canvas.loadData(df, main_indicators=['ma5', 'ma10', 'ma18'], sub_indicators=['sk', 'sd'])

########################################################################
class MultiKlineWindow(QtWidgets.QMainWindow):
    """多窗口显示K线
    包括：

    """

    # ----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(MultiKlineWindow, self).__init__(parent)

        self.periods = ['m30', 'h1', 'h2', 'h4', 'h6', 'd']
        self.kline_dict = {}
        self.initUi()

        self.load_multi_kline()
    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'多周期')
        self.maximumSize()
        self.mdi = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi)

        # 创建菜单
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Cascade")
        file_menu.addAction("Tiled")
        file_menu.triggered[QtWidgets.QAction].connect(self.windowaction)

    def windowaction(self,q):
        if q.text() == "cascade":
            self.mdi.cascadeSubWindows()

        if q.text() == "Cascade":
            self.mdi.tileSubWindows()
    # ----------------------------------------------------------------------
    def load_multi_kline(self):
        """加载多周期窗口"""

        try:
           for period in self.periods:

                sub_window = QtWidgets.QMdiSubWindow()
                sub_window.setWindowTitle(period)
                single_kline = SingleKline(parent=self, period_name=period)
                sub_window.setWidget(single_kline)
                self.mdi.addSubWindow(single_kline)
                single_kline.loadData()
                single_kline.show()

           self.mdi.tileSubWindows()

        except Exception as ex:
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, 'Exception', u'Load vt_Setting.json Exception', QtWidgets.QMessageBox.Cancel,
                                          QtWidgets.QMessageBox.NoButton)

            return


    def closeEvent(self, event):
        """关闭窗口时的事件"""
        sys.exit(0)


class GridKline(QtWidgets.QWidget):

    def __init__(self, parent=None):
        self.parent = parent
        super(GridKline, self).__init__(parent)

        self.periods = ['h1', 'h2', 'h4', 'h6', 'h12', 'd']
        self.kline_dict = {}

        self.initUI()

    def initUI(self):
        gridLayout = QtWidgets.QGridLayout()

        for period_name in self.periods:
            canvas = KLineWidget(display_vol=False, display_sub=True)
            canvas.show()
            canvas.KLtitle.setText('btc({})'.format(period_name), size='18pt')
            canvas.title = 'btc({})'.format(period_name)
            canvas.add_indicator(indicator='ma5', is_main=True)
            canvas.add_indicator(indicator='ma10', is_main=True)
            canvas.add_indicator(indicator='ma18', is_main=True)
            canvas.add_indicator(indicator='sk', is_main=False)
            canvas.add_indicator(indicator='sd', is_main=False)
            self.kline_dict[period_name] = canvas
            # 注册重定向事件
            canvas.relocate_notify_func = self.onRelocate

        gridLayout.addWidget(self.kline_dict['h1'], 0, 1)
        gridLayout.addWidget(self.kline_dict['h2'], 0, 2)
        gridLayout.addWidget(self.kline_dict['h4'], 0, 3)
        gridLayout.addWidget(self.kline_dict['h6'], 1, 1)
        gridLayout.addWidget(self.kline_dict['h12'], 1, 2)
        gridLayout.addWidget(self.kline_dict['d'], 1, 3)

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
                    df = pd.read_csv('data/btc_usd_{}.csv'.format(period_name))
                    df = df.set_index(pd.DatetimeIndex(df['datetime']))
                    canvas.loadData(df, main_indicators=['ma5', 'ma10', 'ma18'], sub_indicators=['sk', 'sd'])

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

def display_multi_window():
    qApp = createQApp()

    qApp.setWindowIcon(QtGui.QIcon(loadIconPath('dashboard.ico')))
    w = MultiKlineWindow()
    w.showMaximized()
    sys.exit(qApp.exec_())

def  display_multi_grid():

    qApp = createQApp()
    qApp.setWindowIcon(QtGui.QIcon(loadIconPath('dashboard.ico')))
    w = GridKline()
    w.showMaximized()
    sys.exit(qApp.exec_())

if __name__ == '__main__':

#
    ## 界面设置
    #cfgfile = QtCore.QFile('css.qss')
    #cfgfile.open(QtCore.QFile.ReadOnly)
    #styleSheet = cfgfile.readAll()
    #styleSheet = str(styleSheet)
    #qApp.setStyleSheet(styleSheet)
#
    # K线界面
    try:
        #ui = KLineWidget(display_vol=False,display_sub=True)
        #ui.show()
        #ui.KLtitle.setText('btc(H2)',size='20pt')
        #ui.add_indicator(indicator='ma5', is_main=True)
        #ui.add_indicator(indicator='ma10', is_main=True)
        #ui.add_indicator(indicator='ma18', is_main=True)
        #ui.add_indicator(indicator='sk',is_main=False)
        #ui.add_indicator(indicator='sd', is_main=False)
        #ui.loadData(pd.DataFrame.from_csv('data/btc_h2.csv'), main_indicators=['ma5','ma10','ma18'], sub_indicators=['sk','sd'])

        #ui = MultiKline(parent=app)
        #ui.show()

        #app.exec_()
    #

        display_multi_grid()

    except Exception as ex:
        print(u'exception:{},trace:{}'.format(str(ex), traceback.format_exc()))
