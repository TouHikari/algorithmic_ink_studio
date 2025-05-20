# gui/main_window.py (Modified - Removed Image Conversion Feature)

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSlider, QFileDialog, QMessageBox, QAction,
                              QSizePolicy, QActionGroup)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QRect, QSize, QPoint

import numpy as np
import cv2

# Import custom modules
from gui.ink_canvas_widget import InkCanvasWidget
from gui.control_panel import ControlPanel
from processing.utils import convert_cv_to_qt # Kept, might be useful, check if still needed
# Remove import of image_processing function
# from processing.image_processing import generate_ink_wash # REMOVED
from processing.lienzo import Lienzo

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("算法水墨：数字水墨画创作工具")
        canvas_initial_width, canvas_initial_height = 1000, 800 # Maybe start with a slightly larger canvas default
        self.setGeometry(100, 100, canvas_initial_width + 300, max(canvas_initial_height + 50, 850))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)

        # Create Lienzo instance
        self.lienzo = Lienzo(width=canvas_initial_width, height=canvas_initial_height, color=255)

        # Create canvas widget and pass Lienzo
        self.canvas_widget = InkCanvasWidget()
        self.canvas_widget.set_lienzo(self.lienzo)
        self.canvas_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.canvas_widget, stretch=3)

        # Create control panel
        self.control_panel = ControlPanel() # Now only contains brush controls
        self.main_layout.addWidget(self.control_panel, stretch=1)

        self.statusBar()
        self.statusBar().showMessage("准备就绪")

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._connect_signals()

        # Only one mode now - free drawing
        # self.current_mode = "free_drawing" # Not strictly needed if only one mode
        # self._update_ui_for_mode(self.current_mode) # Update UI based on the single mode

        # Remove member variable for original image data
        # self._original_image_data: np.ndarray = None # REMOVED

    def _create_actions(self):
        """Creates actions shared between menu and toolbar."""
        # File operations
        self.load_image_action = QAction("加载图片(&O)...", self)
        self.load_image_action.setShortcut("Ctrl+O")
        self.load_image_action.setStatusTip("从文件加载图片到画布") # Simplified status tip

        self.save_canvas_action = QAction("保存画布(&S)...", self)
        self.save_canvas_action.setShortcut("Ctrl+S")
        self.save_canvas_action.setStatusTip("保存当前画布内容到文件")

        self.clear_canvas_action = QAction("清空画布", self)
        self.clear_canvas_action.setStatusTip("用白色填充整个画布")

        # Remove mode switching actions
        # self.mode_image_conversion_action = QAction("图片转换模式", self) # REMOVED
        # self.mode_free_drawing_action = QAction("自由绘画模式", self) # REMOVED

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

        # Remove mode menu and action group
        # mode_menu = menu_bar.addMenu("模式(&M)") # REMOVED
        # mode_menu.addAction(self.mode_image_conversion_action) # REMOVED
        # mode_menu.addAction(self.mode_free_drawing_action) # REMOVED
        # self.mode_action_group = QActionGroup(self) # REMOVED
        # self.mode_action_group.addAction(self.mode_image_conversion_action) # REMOVED
        # self.mode_action_group.addAction(self.mode_free_drawing_action) # REMOVED
        # No mode menu, implicitly only free drawing mode is active.

    def _create_tool_bar(self):
        """Creates the toolbar."""
        tool_bar = self.addToolBar("常用工具")
        tool_bar.addAction(self.load_image_action)
        tool_bar.addAction(self.save_canvas_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.clear_canvas_action)
        # Remove mode toggle actions from toolbar
        # tool_bar.addSeparator() # REMOVED
        # tool_bar.addAction(self.mode_image_conversion_action) # REMOVED
        # tool_bar.addAction(self.mode_free_drawing_action) # REMOVED

    def _connect_signals(self):
        """Connects signals from widgets and actions to corresponding slots."""
        # File actions
        self.load_image_action.triggered.connect(self._load_image)
        self.save_canvas_action.triggered.connect(self._save_canvas)
        self.clear_canvas_action.triggered.connect(self._clear_canvas)

        # Remove mode switching signal connection
        # self.mode_action_group.triggered.connect(self._on_mode_triggered_by_action) # REMOVED

        # Connect parameter changes FROM control panel TO canvas widget (only brush params now)
        self.control_panel.parameters_changed.connect(self.canvas_widget.set_brush_params)

        # Remove connection for generate button signal
        # self.control_panel.generate_image_requested.connect(self._generate_ink_wash_image) # REMOVED

        # Canvas widget signals (if any used by MainWindow)
        # self.canvas_widget.canvas_content_changed.connect(self._on_canvas_content_changed) # Example use

    # --- Slot Functions ---

    # Remove mode switching slots - only one mode now
    # def _on_mode_triggered_by_action(self, action: QAction): pass # REMOVED
    # def _switch_mode(self, mode: str): pass # REMOVED
    # def _update_ui_for_mode(self, mode: str): pass # REMOVED - UI is static now, only brush controls visible

    def _load_image(self):
        """Slot: Handles the 'Load Image' action. Loads image directly to canvas."""
        print("Load image requested...")
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("选择要加载的图片")
        file_dialog.setNameFilter("图像文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_dialog.exec_():
            filepath = file_dialog.selectedFiles()[0]
            print(f"Selected file: {filepath}")
            self.statusBar().showMessage(f"正在加载图片: {filepath}...")
            try:
                # Use OpenCV to load the image (read as is, color or grayscale)
                cv_image = cv2.imread(filepath)

                if cv_image is not None:
                    # Directly load the image onto the canvas widget
                    # CanvasWidget.load_image_into_canvas handles resizing and grayscale conversion for display on Lienzo.
                    self.canvas_widget.load_image_into_canvas(cv_image)

                    self.statusBar().showMessage("图片加载成功，已载入到画布。")

                else:
                    QMessageBox.warning(self, "加载失败", "无法读取选定的图片文件。")
                    self.statusBar().showMessage("图片加载失败。")

            except Exception as e:
                QMessageBox.critical(self, "加载出错", f"加载图片时发生错误: {e}")
                self.statusBar().showMessage("图片加载出错。")

    def _save_canvas(self):
        # ... (Keep, saves canvas content) ...
        print("Save canvas requested...")
        canvas_data = self.canvas_widget.get_canvas_image_data()
        if canvas_data is None or canvas_data.size == 0: QMessageBox.warning(self, "保存失败", "画布为空，没有内容可以保存。"); return

        file_dialog = QFileDialog(self); file_dialog.setWindowTitle("保存当前画布为图片"); file_dialog.setAcceptMode(QFileDialog.AcceptSave); file_dialog.setNameFilter("PNG Images (*.png);;JPEG Images (*.jpg *.jpeg);;BMP Images (*.bmp)"); file_dialog.setDefaultSuffix("png"); file_dialog.selectFile("untitled_ink_wash.png")

        if file_dialog.exec_():
            filepath = file_dialog.selectedFiles()[0]
            print(f"Saving to: {filepath}"); self.statusBar().showMessage(f"正在保存画布到: {filepath}...")
            try:
                success = cv2.imwrite(filepath, canvas_data)
                if success: print("Image saved successfully."); self.statusBar().showMessage("画布保存成功。")
                else: QMessageBox.warning(self, "保存失败", "保存图片时发生错误。请检查文件路径或格式。"); self.statusBar().showMessage("画布保存失败。")
            except Exception as e: QMessageBox.critical(self, "保存出错", f"保存图片时发生错误: {e}"); self.statusBar().showMessage("画布保存出错。")

    def _clear_canvas(self):
        # ... (Keep, clears Lienzo) ...
        print("Clear canvas requested...")
        if self.lienzo: self.lienzo.fill(255); self.canvas_widget.update(); self.statusBar().showMessage("画布已清空。")

    def _on_control_panel_parameters_changed(self, params: dict):
        """Slot: Receives parameter changes from the ControlPanel (now only brush params)."""
        # print(f"Brush parameters changed received in MainWindow: {params}")
        # Always forward brush parameters to the canvas widget since there's only one mode.
        self.canvas_widget.set_brush_params(params)
        # Update status bar with brush info (optional)
        self.statusBar().showMessage(f"笔刷参数已更新: 大小={params.get('size', '?')}, 密度={params.get('density', '?')}, 湿润度={params.get('wetness', '?')}, 飞白={params.get('feibai', '?')}")

    # Remove slot for generating image
    # def _generate_ink_wash_image(self): pass # REMOVED

    # def _on_canvas_content_changed(self): pass # Keep if used by MainWindow