# gui/main_window.py

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSlider, QFileDialog, QMessageBox, QAction,
                              QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QRect, QSize, QPoint

import numpy as np
import cv2

from gui.ink_canvas_widget import InkCanvasWidget
from gui.control_panel import ControlPanel
from processing.utils import convert_cv_to_qt
from processing.lienzo import Lienzo
import processing.brush_engine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("算法水墨：数字水墨画创作工具")
        canvas_initial_width, canvas_initial_height = 1000, 800
        self.setGeometry(100, 100, canvas_initial_width + 300, max(canvas_initial_height + 50, 850))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)

        self.lienzo = Lienzo(width=canvas_initial_width, height=canvas_initial_height, color=255)

        self.canvas_widget = InkCanvasWidget()
        self.canvas_widget.set_lienzo(self.lienzo)
        self.canvas_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.canvas_widget, stretch=3)

        processing.brush_engine.load_brush_shapes()
        available_brush_types = processing.brush_engine.get_available_brush_types()

        self.control_panel = ControlPanel()
        self.control_panel.set_available_brush_types(available_brush_types, default_type='round')

        self.main_layout.addWidget(self.control_panel, stretch=1)

        self.statusBar()
        self.statusBar().showMessage("准备就绪")

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._connect_signals()

    def _create_actions(self):
        """Creates actions shared between menu and toolbar."""
        self.load_image_action = QAction("加载图片(&O)...", self)
        self.load_image_action.setShortcut("Ctrl+O")
        self.load_image_action.setStatusTip("从文件加载图片到画布")

        self.save_canvas_action = QAction("保存画布(&S)...", self)
        self.save_canvas_action.setShortcut("Ctrl+S")
        self.save_canvas_action.setStatusTip("保存当前画布内容到文件")

        self.clear_canvas_action = QAction("清空画布", self)
        self.clear_canvas_action.setStatusTip("用白色填充整个画布")

    def _create_menu_bar(self):
        """Creates the menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件(&F)")
        file_menu.addAction(self.load_image_action)
        file_menu.addAction(self.save_canvas_action)
        file_menu.addSeparator()
        file_menu.addAction(self.clear_canvas_action)
        file_menu.addSeparator()
        file_menu.addAction(QAction("退出", self, triggered=self.close))

    def _create_tool_bar(self):
        """Creates the toolbar."""
        tool_bar = self.addToolBar("常用工具")
        tool_bar.addAction(self.load_image_action)
        tool_bar.addAction(self.save_canvas_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.clear_canvas_action)

    def _connect_signals(self):
        """Connects signals from widgets and actions."""
        self.load_image_action.triggered.connect(self._load_image)
        self.save_canvas_action.triggered.connect(self._save_canvas)
        self.clear_canvas_action.triggered.connect(self._clear_canvas)

        self.control_panel.parameters_changed.connect(self.canvas_widget.set_brush_params)

    def _load_image(self):
        """Slot: Handles the 'Load Image' action."""
        print("Load image requested...")
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("选择要加载的图片")
        file_dialog.setNameFilter("图像文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_dialog.exec_():
            filepath = file_dialog.selectedFiles()[0]
            print(f"Selected file: {filepath}")
            self.statusBar().showMessage(f"正在加载图片: {filepath}...")
            try:
                cv_image = cv2.imread(filepath)
                if cv_image is not None:
                    self.canvas_widget.load_image_into_canvas(cv_image)
                    self.statusBar().showMessage("图片加载成功，已载入到画布。")
                else:
                    QMessageBox.warning(self, "加载失败", "无法读取选定的图片文件。")
                    self.statusBar().showMessage("图片加载失败。")
            except Exception as e:
                QMessageBox.critical(self, "加载出错", f"加载图片时发生错误: {e}")
                self.statusBar().showMessage("图片加载出错。")

    def _save_canvas(self):
         print("Save canvas requested...")
         canvas_data = self.canvas_widget.get_canvas_image_data()
         if canvas_data is None or canvas_data.size == 0: QMessageBox.warning(self, "保存失败", "画布为空，没有内容可以保存。"); return

         file_dialog = QFileDialog(self)
         file_dialog.setWindowTitle("保存当前画布为图片")
         file_dialog.setAcceptMode(QFileDialog.AcceptSave)
         file_dialog.setNameFilter("PNG Images (*.png);;JPEG Images (*.jpg *.jpeg);;BMP Images (*.bmp)")
         file_dialog.setDefaultSuffix("png")
         file_dialog.selectFile("untitled_ink_wash.png")

         if file_dialog.exec_():
             filepath = file_dialog.selectedFiles()[0]
             print(f"Saving to: {filepath}"); self.statusBar().showMessage(f"正在保存画布到: {filepath}...")
             try:
                 if canvas_data.dtype != np.uint8:
                     print(f"Warning: Canvas data dtype is {canvas_data.dtype}, converting to uint8 for saving.")
                     canvas_data = canvas_data.astype(np.uint8)
                 if len(canvas_data.shape) == 3:
                     print(f"Warning: Canvas data shape is {canvas_data.shape}, converting to grayscale for saving.")
                     if canvas_data.shape[2] == 3:
                          canvas_data = cv2.cvtColor(canvas_data, cv2.COLOR_BGR2GRAY)
                     elif canvas_data.shape[2] == 4:
                          canvas_data = cv2.cvtColor(canvas_data, cv2.COLOR_BGRA2GRAY)
                     else:
                           print(f"Warning: Cannot convert canvas data with {canvas_data.shape[2]} channels to gray for saving. Attempting save as is.")
                 success = cv2.imwrite(filepath, canvas_data)
                 if success: print("Image saved successfully."); self.statusBar().showMessage("画布保存成功。")
                 else: QMessageBox.warning(self, "保存失败", "保存图片时发生错误。请检查文件路径或格式。"); self.statusBar().showMessage("画布保存失败。")
             except Exception as e: QMessageBox.critical(self, "保存出错", f"保存图片时发生错误: {e}"); self.statusBar().showMessage("画布保存出错。")

    def _clear_canvas(self):
        print("Clear canvas requested...")
        if self.lienzo:
            self.lienzo.fill(255)
            self.canvas_widget.update()
            self.statusBar().showMessage("画布已清空。")

    def _on_control_panel_parameters_changed(self, params: dict):
        """Slot: Receives brush parameter changes."""
        self.canvas_widget.set_brush_params(params)
        self.statusBar().showMessage(f"笔刷参数已更新: 类型={params.get('type', '?')}, 大小={params.get('size', '?')}, 密度={params.get('density', '?')}, 湿润度={params.get('wetness', '?')}, 飞白={params.get('feibai', '?')}")