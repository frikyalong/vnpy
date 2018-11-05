# encoding: UTF-8
# 多RPC监控界面组件
# author: 李来佳
# 当前目录需要有VT_setting.json

import sys, os
global vnpy_root
vnpy_root = os.path.abspath(os.path.join(os.getcwd()))
sys.path.append(vnpy_root)

from vnpy.trader.uiMultiRpcMonitor import *
if __name__ == '__main__':
    from vnpy.trader.uiQt import createQApp

    qApp = createQApp()

    qApp.setWindowIcon(QtGui.QIcon(loadIconPath('dashboard.ico')))
    w = MultiRpcServerManager()
    w.showMaximized()
    sys.exit(qApp.exec_())
