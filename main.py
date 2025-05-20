import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

if __name__ == "__main__":
    # 创建Qt应用程序实例
    app = QApplication(sys.argv)

    # 创建主窗口实例
    main_window = MainWindow()
    main_window.show() # 显示窗口

    # 启动应用程序的事件循环
    # 事件循环会等待用户操作（如点击、输入）或系统事件（如窗口重绘）
    # 当事件发生时，Qt会将事件发送给对应的窗口或控件进行处理（信号与槽机制）
    sys.exit(app.exec_())