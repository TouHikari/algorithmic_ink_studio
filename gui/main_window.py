# gui/main_window.py

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSlider, QFileDialog, QMessageBox, QAction,
                              QSizePolicy, QActionGroup, QToolBar) # Import QToolBar and QActionGroup
from PyQt5.QtGui import QPixmap, QImage, QIcon # Import QIcon for toolbar buttons
from PyQt5.QtCore import Qt, QRect, QSize, QPoint

import numpy as np
import cv2
import os # Import os for icon paths

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

        self._history = [] # History states (list of numpy arrays)
        self._history_index = -1 # Index of the current state in the history

        # Save initial state
        self._save_history_state()
        # Update UI state for actions on startup
        self._update_action_states()

    def _get_icon_path(self, icon_name: str) -> str:
        """Helper to get icon path relative to the script."""
        base_path = os.path.dirname(__file__)
        icon_folder = os.path.join(base_path, '..', 'resources', 'icons')
        return os.path.join(icon_folder, f'{icon_name}.png')

    def _create_actions(self):
        """Creates actions shared between menu and toolbar."""
        self.load_image_action = QAction(QIcon(self._get_icon_path('open')), "加载图片(&O)...", self)
        self.load_image_action.setShortcut("Ctrl+O")
        self.load_image_action.setStatusTip("从文件加载图片到画布")

        self.save_canvas_action = QAction(QIcon(self._get_icon_path('save')), "保存画布(&S)...", self)
        self.save_canvas_action.setShortcut("Ctrl+S")
        self.save_canvas_action.setStatusTip("保存当前画布内容到文件")

        self.clear_canvas_action = QAction(QIcon(self._get_icon_path('new')), "清空画布", self)
        self.clear_canvas_action.setStatusTip("用白色填充整个画布")

        self.undo_action = QAction(QIcon(self._get_icon_path('undo')), "撤销(&U)", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setStatusTip("撤销上一步操作")

        self.redo_action = QAction(QIcon(self._get_icon_path('redo')), "重做(&R)", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setStatusTip("重做上一步撤销的操作")

        # Tool actions
        self.tool_brush_action = QAction(QIcon(self._get_icon_path('brush')), "画笔工具", self)
        self.tool_brush_action.setStatusTip("选择画笔工具进行绘画")
        self.tool_brush_action.setCheckable(True)

        self.tool_eraser_action = QAction(QIcon(self._get_icon_path('eraser')), "橡皮擦工具", self)
        self.tool_eraser_action.setStatusTip("选择橡皮擦工具进行擦除")
        self.tool_eraser_action.setCheckable(True)

        # Group tool actions for exclusive selection
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.addAction(self.tool_brush_action)
        self.tool_action_group.addAction(self.tool_eraser_action)

        # Set default tool
        self.tool_brush_action.setChecked(True)

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

        edit_menu = menu_bar.addMenu("编辑(&E)")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)

        tools_menu = menu_bar.addMenu("工具(&T)")
        tools_menu.addAction(self.tool_brush_action)
        tools_menu.addAction(self.tool_eraser_action)

    def _create_tool_bar(self):
        """Creates the toolbar."""
        tool_bar = self.addToolBar("常用工具")
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

    def _connect_signals(self):
        """Connects signals from widgets and actions."""
        self.load_image_action.triggered.connect(self._load_image)
        self.save_canvas_action.triggered.connect(self._save_canvas)
        self.clear_canvas_action.triggered.connect(self._clear_canvas)

        self.undo_action.triggered.connect(self._undo)
        self.redo_action.triggered.connect(self._redo)

        # Connect tool actions to a single slot
        self.tool_action_group.triggered.connect(self._on_tool_triggered)

        self.control_panel.parameters_changed.connect(self.canvas_widget.set_brush_params)

        # Connect canvas widget signal to save history
        self.canvas_widget.strokeFinished.connect(self._on_stroke_finished)

    def _save_history_state(self):
        """Saves the current lienzo state to the history."""
        if self._history_index < len(self._history) - 1:
            # Discard any states after the current index if a new action is performed
            self._history = self._history[:self._history_index + 1]

        # Get a copy of the current canvas data
        current_state = self.lienzo.get_canvas_data().copy()
        self._history.append(current_state)
        self._history_index += 1

        # Trim history if it gets too large (optional, but good for memory)
        # MAX_HISTORY_STATES = 50 # Example limit
        # while len(self._history) > MAX_HISTORY_STATES:
        #     self._history.pop(0)
        #     self._history_index -= 1

        self._update_action_states()
        # print(f"History saved. Current index: {self._history_index}/{len(self._history)-1}")

    def _load_history_state(self, index: int):
        """Loads a specific state from history and updates the canvas."""
        if 0 <= index < len(self._history):
            state_data = self._history[index]
            # Set the canvas data. Lienzo.set_canvas_data handles resizing if needed.
            try:
                 self.lienzo.set_canvas_data(state_data.copy()) # Pass a copy
                 self._history_index = index
                 self.canvas_widget.update() # Request canvas repaint
                 self._update_action_states()
                 # print(f"History state loaded. Current index: {self._history_index}/{len(self._history)-1}")

            except Exception as e:
                 print(f"Error loading history state at index {index}: {e}")
                 QMessageBox.critical(self, "历史记录错误", f"加载历史状态时发生错误: {e}")
        else:
             print(f"Warning: Attempted to load invalid history index: {index}")

    def _update_action_states(self):
        """Updates the enabled/disabled state of Undo/Redo actions."""
        self.undo_action.setEnabled(self._history_index > 0)
        self.redo_action.setEnabled(self._history_index < len(self._history) - 1)

    def _undo(self):
        """Slot: Handles the 'Undo' action."""
        if self._history_index > 0:
            self._load_history_state(self._history_index - 1)
            self.statusBar().showMessage(f"已撤销 (状态 {self._history_index + 1}/{len(self._history)})")

    def _redo(self):
        """Slot: Handles the 'Redo' action."""
        if self._history_index < len(self._history) - 1:
            self._load_history_state(self._history_index + 1)
            self.statusBar().showMessage(f"已重做 (状态 {self._history_index + 1}/{len(self._history)})")

    def _on_stroke_finished(self):
        """Slot: Called by CanvasWidget when a stroke is finished. Save state and update UI."""
        self._save_history_state()
        self.statusBar().showMessage(f"操作完成 (状态 {self._history_index + 1}/{len(self._history)})")

    def _on_tool_triggered(self, action: QAction):
        """Slot: Handles tool selection (Brush or Eraser)."""
        if action == self.tool_brush_action:
            self.canvas_widget.set_current_tool("brush")
            self.statusBar().showMessage("工具：画笔")
        elif action == self.tool_eraser_action:
            self.canvas_widget.set_current_tool("eraser")
            self.statusBar().showMessage("工具：橡皮擦")
        # If you had tool-specific control panels, you would swap them here
        # self.control_panel.show_brush_controls() # For brush
        # self.control_panel.show_eraser_controls() # For eraser (would need to implement)

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
                    # Loading a new image should clear history and save the new state
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
            # Clearing canvas is an action, save state and clear future history
            self._history = []
            self._history_index = -1
            self._save_history_state()
            self.statusBar().showMessage("画布已清空。")

    def _on_control_panel_parameters_changed(self, params: dict):
        """Slot: Receives brush parameter changes."""
        self.canvas_widget.set_brush_params(params)
        # Update status bar message to reflect current tool as well
        tool_name_zh = "画笔" if self._current_tool == "brush" else "橡皮擦"
        self.statusBar().showMessage(f"工具：{tool_name_zh}, 参数已更新: 类型={params.get('type', '?')}, 大小={params.get('size', '?')}, 密度={params.get('density', '?')}, 湿润度={params.get('wetness', '?')}, 飞白={params.get('feibai', '?')}")