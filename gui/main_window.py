# gui/main_window.py

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSlider, QFileDialog, QMessageBox, QAction,
                              QSizePolicy, QActionGroup, QInputDialog)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, QCoreApplication

import numpy as np
import cv2
import os

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

        self._history = []
        self._history_index = -1

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._connect_signals()

        self._save_history_state()
        self._update_action_states()
        self._update_status_bar()

    def _get_icon_path(self, icon_name: str) -> str:
        """Helper to get icon path relative to the script."""
        base_path = os.path.dirname(__file__)
        icon_folder = os.path.join(base_path, '..', 'resources', 'icons')
        return os.path.join(icon_folder, f'{icon_name}.png')

    def _create_actions(self):
        """Creates actions shared between menu and toolbar."""
        self.new_canvas_action = QAction(QIcon(self._get_icon_path('new')), "新建画布(&N)...", self)
        self.new_canvas_action.setShortcut("Ctrl+N")
        self.new_canvas_action.setStatusTip("创建新的空白画布")

        self.load_image_action = QAction(QIcon(self._get_icon_path('open')), "加载图片(&O)...", self)
        self.load_image_action.setShortcut("Ctrl+O")
        self.load_image_action.setStatusTip("从文件加载图片到画布")

        self.save_canvas_action = QAction(QIcon(self._get_icon_path('save')), "保存画布(&S)...", self)
        self.save_canvas_action.setShortcut("Ctrl+S")
        self.save_canvas_action.setStatusTip("保存当前画布内容到文件")

        self.clear_canvas_action = QAction(QIcon(self._get_icon_path('clear')), "清空画布", self)
        self.clear_canvas_action.setStatusTip("用白色填充整个画布")

        self.undo_action = QAction(QIcon(self._get_icon_path('undo')), "撤销(&U)", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setStatusTip("撤销上一步操作")

        self.redo_action = QAction(QIcon(self._get_icon_path('redo')), "重做(&R)", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setStatusTip("重做上一步撤销的操作")

        self.tool_brush_action = QAction(QIcon(self._get_icon_path('brush')), "画笔工具", self)
        self.tool_brush_action.setStatusTip("选择画笔工具进行绘画")
        self.tool_brush_action.setCheckable(True)

        self.tool_eraser_action = QAction(QIcon(self._get_icon_path('eraser')), "橡皮擦工具", self)
        self.tool_eraser_action.setStatusTip("选择橡皮擦工具进行擦除")
        self.tool_eraser_action.setCheckable(True)

        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.addAction(self.tool_brush_action)
        self.tool_action_group.addAction(self.tool_eraser_action)
        self.tool_brush_action.setChecked(True)

        self.zoom_in_action = QAction(QIcon(self._get_icon_path('zoom_in')), "放大", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.setStatusTip("放大画布视图")

        self.zoom_out_action = QAction(QIcon(self._get_icon_path('zoom_out')), "缩小", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.setStatusTip("缩小画布视图")

        self.zoom_actual_action = QAction(QIcon(self._get_icon_path('zoom_actual')), "实际像素 (100%)", self)
        self.zoom_actual_action.setShortcut("Ctrl+0")
        self.zoom_actual_action.setStatusTip("以实际像素比例显示画布 (1:1)")

        self.zoom_fit_action = QAction(QIcon(self._get_icon_path('zoom_fit')), "适合窗口", self)
        self.zoom_fit_action.setShortcut("Ctrl+W")
        self.zoom_fit_action.setStatusTip("调整画布视图以适合窗口大小")

    def _create_menu_bar(self):
        """Creates the menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件(&F)")
        file_menu.addAction(self.new_canvas_action)
        file_menu.addAction(self.load_image_action)
        file_menu.addAction(self.save_canvas_action)
        file_menu.addSeparator()
        file_menu.addAction(self.clear_canvas_action)
        file_menu.addSeparator()
        file_menu.addAction(QAction("退出", self, triggered=self.close))

        edit_menu = menu_bar.addMenu("编辑(&E)")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)

        tools_menu = menu_bar.addMenu("工具(&T)")
        tools_menu.addAction(self.tool_brush_action)
        tools_menu.addAction(self.tool_eraser_action)

        view_menu = menu_bar.addMenu("视图(&V)")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.zoom_actual_action)
        view_menu.addAction(self.zoom_fit_action)

    def _create_tool_bar(self):
        """Creates the toolbar."""
        tool_bar = self.addToolBar("常用工具")
        tool_bar.addAction(self.new_canvas_action)
        tool_bar.addAction(self.load_image_action)
        tool_bar.addAction(self.save_canvas_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.clear_canvas_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.undo_action)
        tool_bar.addAction(self.redo_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.tool_brush_action)
        tool_bar.addAction(self.tool_eraser_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.zoom_in_action)
        tool_bar.addAction(self.zoom_out_action)
        tool_bar.addAction(self.zoom_actual_action)
        tool_bar.addAction(self.zoom_fit_action)

    def _connect_signals(self):
        """Connects signals from widgets and actions."""
        self.new_canvas_action.triggered.connect(self._new_canvas)
        self.load_image_action.triggered.connect(self._load_image)
        self.save_canvas_action.triggered.connect(self._save_canvas)
        self.clear_canvas_action.triggered.connect(self._clear_canvas)

        self.undo_action.triggered.connect(self._undo)
        self.redo_action.triggered.connect(self._redo)

        self.tool_action_group.triggered.connect(self._on_tool_triggered)

        self.zoom_in_action.triggered.connect(self._zoom_in)
        self.zoom_out_action.triggered.connect(self._zoom_out)
        self.zoom_actual_action.triggered.connect(self._zoom_actual)
        self.zoom_fit_action.triggered.connect(self._zoom_fit)

        self.control_panel.parameters_changed.connect(self.canvas_widget.set_brush_params)

        self.canvas_widget.strokeFinished.connect(self._on_stroke_finished)
        self.canvas_widget.canvas_content_changed.connect(self._update_status_bar)
        self.canvas_widget.zoomLevelChanged.connect(self._update_status_bar)

    def _save_history_state(self):
        """Saves the current lienzo state to the history."""
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]

        current_state = self.lienzo.get_canvas_data().copy()
        self._history.append(current_state)
        self._history_index += 1

        MAX_HISTORY_STATES = 100
        while len(self._history) > MAX_HISTORY_STATES:
            self._history.pop(0)
            self._history_index -= 1

        self._update_action_states()

    def _load_history_state(self, index: int):
        """Loads a specific state from history and updates the canvas."""
        if 0 <= index < len(self._history):
            state_data = self._history[index]
            try:
                 self.lienzo.set_canvas_data(state_data.copy())
                 self._history_index = index
                 self.canvas_widget.update()
                 self._update_action_states()
                 self._update_status_bar()

            except Exception as e:
                 print(f"Error loading history state at index {index}: {e}")
                 QMessageBox.critical(self, "历史记录错误", f"加载历史状态时发生错误: {e}")
        else:
             print(f"Warning: Attempted to load invalid history index: {index}")

    def _update_action_states(self):
        """Updates the enabled/disabled state of Undo/Redo actions."""
        self.undo_action.setEnabled(self._history_index > 0)
        self.redo_action.setEnabled(self._history_index < len(self._history) - 1)

    def _update_status_bar(self):
        """Updates the status bar with canvas size, zoom level, and brush info."""
        if self.lienzo:
            width, height = self.lienzo.get_size()
            zoom = self.canvas_widget.get_zoom_factor()
            tool_name_zh = "画笔" if self.canvas_widget._current_tool == "brush" else "橡皮擦"
            brush_params = self.canvas_widget._current_brush_params # Access current params from canvas_widget

            status_text = (
                f"工具：{tool_name_zh}"
                f" | 画布：{width}x{height} 像素"
                f" | 缩放：{zoom:.0%}"
                f" | 状态：{self._history_index + 1}/{len(self._history)}"
                f" | 参数：大小={brush_params.get('size', '-')}, 密度={brush_params.get('density', '-')}, 湿润度={brush_params.get('wetness', '-')}, 飞白={brush_params.get('feibai', '-')}, 硬度={brush_params.get('hardness', '-')}, 流量={brush_params.get('flow', '-')}"
                f" 类型={brush_params.get('type', '-')}"
                f" 角度模式={brush_params.get('angle_mode', '-')}"
            )
            self.statusBar().showMessage(status_text)

        else:
             self.statusBar().showMessage("没有加载画布")

    def _undo(self):
        """Slot: Handles the 'Undo' action."""
        if self._history_index > 0:
            self._load_history_state(self._history_index - 1)

    def _redo(self):
        """Slot: Handles the 'Redo' action."""
        if self._history_index < len(self._history) - 1:
            self._load_history_state(self._history_index + 1)

    def _on_stroke_finished(self):
        """Slot: Called by CanvasWidget when a stroke is finished. Save state and update UI."""
        self._save_history_state()

    def _on_tool_triggered(self, action: QAction):
        """Slot: Handles tool selection."""
        if action == self.tool_brush_action:
            self.canvas_widget.set_current_tool("brush")
        elif action == self.tool_eraser_action:
            self.canvas_widget.set_current_tool("eraser")
        self._update_status_bar()

    def _new_canvas(self):
        """Slot: Creates a new canvas with user-defined size."""
        print("New canvas requested...")
        current_width, current_height = (self.lienzo.get_size() if self.lienzo else (1000, 800))

        width, ok_w = QInputDialog.getInt(self, "新建画布", "宽度 (像素):", current_width, 1, 4000, 1)
        if not ok_w: return

        height, ok_h = QInputDialog.getInt(self, "新建画布", "高度 (像素):", current_height, 1, 4000, 1)
        if not ok_h: return

        if width <= 0 or height <= 0:
             QMessageBox.warning(self, "新建失败", "画布尺寸无效。")
             return

        try:
             self.lienzo = Lienzo(width=width, height=height, color=255)
             self.canvas_widget.set_lienzo(self.lienzo)

             self._history = []
             self._history_index = -1
             self._save_history_state()

             self.statusBar().showMessage(f"新建画布成功: {width}x{height} 像素")
             self._update_status_bar()

        except Exception as e:
            QMessageBox.critical(self, "新建出错", f"创建新画布时发生错误: {e}")
            self.statusBar().showMessage("新建画布出错。")

    def _zoom_in(self):
        """Slot: Zooms in."""
        if self.lienzo is None: return
        current_zoom = self.canvas_widget.get_zoom_factor()
        zoom_levels = [0.01, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 8.0, 10.0, 16.0, 32.0, 64.0, 100.0]
        new_zoom = current_zoom
        for level in zoom_levels:
            if level > current_zoom + 0.001:
                new_zoom = level
                break
        else:
             new_zoom = zoom_levels[-1]

        if new_zoom != current_zoom:
            # Keep current pan, set_zoom_pan will handle re-centering based on mouse pos in wheelEvent, but not here.
            # For menu/toolbar zoom, just keep the current pan offset.
            current_pan_offset = self.canvas_widget.get_pan_offset()
            self.canvas_widget.set_zoom_pan(new_zoom, current_pan_offset)

    def _zoom_out(self):
        """Slot: Zooms out."""
        if self.lienzo is None: return
        current_zoom = self.canvas_widget.get_zoom_factor()
        zoom_levels = [0.01, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 8.0, 10.0, 16.0, 32.0, 64.0, 100.0]
        new_zoom = current_zoom
        for level in reversed(zoom_levels):
            if level < current_zoom - 0.001:
                new_zoom = level
                break
        else:
             new_zoom = zoom_levels[0]

        if new_zoom != current_zoom:
            current_pan_offset = self.canvas_widget.get_pan_offset()
            self.canvas_widget.set_zoom_pan(new_zoom, current_pan_offset)

    def _zoom_actual(self):
        """Slot: Sets zoom to 100% (actual pixels)."""
        if self.lienzo is None: return
        self.canvas_widget.set_zoom_pan(1.0, QPoint(0,0))

    def _zoom_fit(self):
        """Slot: Adjusts zoom and pan to fit canvas in window."""
        if self.lienzo is None or self.canvas_widget is None: return

        canvas_width, canvas_height = self.lienzo.get_size()
        widget_width, widget_height = self.canvas_widget.width(), self.canvas_widget.height()

        if canvas_width <= 0 or canvas_height <= 0 or widget_width <= 0 or widget_height <= 0:
             return

        scale_w = widget_width / canvas_width if canvas_width > 0 else 0
        scale_h = widget_height / canvas_height if canvas_height > 0 else 0

        fit_zoom_factor = min(scale_w, scale_h)

        fit_zoom_factor *= 0.95

        fit_zoom_factor = max(0.01, fit_zoom_factor)

        self.canvas_widget.set_zoom_pan(fit_zoom_factor, QPoint(0,0))

        scaled_canvas_width = canvas_width * fit_zoom_factor
        scaled_canvas_height = canvas_height * fit_zoom_factor

        pan_x = 0
        pan_y = 0

        if scaled_canvas_width < widget_width:
            pan_x = (widget_width - scaled_canvas_width) / 2
        if scaled_canvas_height < widget_height:
            pan_y = (widget_height - scaled_canvas_height) / 2

        self.canvas_widget.set_zoom_pan(fit_zoom_factor, QPoint(int(pan_x), int(pan_y)))

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
                    self._history = []
                    self._history_index = -1
                    self._save_history_state()
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
            self._history = []
            self._history_index = -1
            self._save_history_state()
            self.statusBar().showMessage("画布已清空。")

    def _on_control_panel_parameters_changed(self, params: dict):
        """Slot: Receives brush parameter changes."""
        self.canvas_widget.set_brush_params(params)
        self._update_status_bar()