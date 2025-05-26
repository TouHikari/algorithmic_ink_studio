# gui/control_panel.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                              QGroupBox, QSpacerItem, QSizePolicy, QPushButton,
                              QSpinBox, QComboBox, QColorDialog, QFrame, QGridLayout)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal

class ControlPanel(QWidget):
    parameters_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_params = {}
        self._parameter_widgets = {}
        self._brush_type_combo = None
        self._angle_mode_combo = None

        self._color_frame = None
        self._color_dialog = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)

        # --- Color Selection Group ---
        self.color_group = QGroupBox("颜色")
        self.color_layout = QVBoxLayout(self.color_group)

        # Current Color Display
        color_display_hbox = QHBoxLayout()
        self.current_color_label = QLabel("当前颜色:")
        self.current_color_label.setFixedWidth(120)
        self.current_color_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._color_frame = QFrame(self)
        self._color_frame.setFixedSize(80, 20)
        self._color_frame.setAutoFillBackground(True)
        self._color_frame.setStyleSheet(f"background-color: white;")

        color_display_hbox.addWidget(self.current_color_label)
        color_display_hbox.addWidget(self._color_frame)
        color_display_hbox.addStretch(1)

        self.color_layout.addLayout(color_display_hbox)

        # Color Palette/Picker Button
        self.pick_color_button = QPushButton("选择颜色...")
        self.pick_color_button.clicked.connect(self._pick_color)
        self.color_layout.addWidget(self.pick_color_button)

        # Predefined Colors
        self.predefined_colors_label = QLabel("预设颜色:")
        self.predefined_colors_label.setFixedWidth(120)
        self.predefined_colors_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.color_layout.addWidget(self.predefined_colors_label)

        self._chinese_ink_colors_bgr = {
            "墨黑": (0, 0, 0),
            "钛白": (255, 255, 255),
            "三青": (200, 120, 0),
            "三绿": (100, 200, 0),
            "花青": (150, 80, 50),
            "朱砂": (0, 0, 255),
            "朱磦": (0, 69, 255),
            "胭脂": (150, 0, 200),
            "曙红": (50, 50, 200),
            "藤黄": (0, 215, 255),
            "赭石": (50, 100, 150),
            "酞青蓝": (255, 0, 0),
        }
        self._create_predefined_color_buttons(self.color_layout)

        self.main_layout.addWidget(self.color_group)

        # --- Brush Parameters Group ---
        self.brush_group = QGroupBox("笔刷参数")
        self.brush_layout = QVBoxLayout(self.brush_group)

        self._create_parameter_control("大小", 1, 100, 40, 'size', self.brush_layout)
        self._create_parameter_control("密度", 0, 100, 60, 'density', self.brush_layout)
        self._create_parameter_control("湿润度", 0, 100, 0, 'wetness', self.brush_layout)
        self._create_parameter_control("飞白", 0, 100, 20, 'feibai', self.brush_layout)
        self._create_parameter_control("硬度", 0, 100, 50, 'hardness', self.brush_layout)
        self._create_parameter_control("流量", 0, 100, 100, 'flow', self.brush_layout)

        self.brush_type_label = QLabel("笔刷类型:")
        self.brush_type_label.setFixedWidth(120)
        self.brush_type_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._brush_type_combo = QComboBox()

        brush_type_hbox = QHBoxLayout()
        brush_type_hbox.addWidget(self.brush_type_label)
        brush_type_hbox.addWidget(self._brush_type_combo, 1)
        self.brush_layout.addLayout(brush_type_hbox)

        self.angle_mode_label = QLabel("角度模式:")
        self.angle_mode_label.setFixedWidth(120)
        self.angle_mode_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._angle_mode_combo = QComboBox()
        self._angle_mode_combo.addItems(["Direction", "Fixed", "Random", "Direction+Jitter", "Fixed+Jitter"])
        self._angle_mode_combo.setCurrentText("Direction")

        angle_mode_hbox = QHBoxLayout()
        angle_mode_hbox.addWidget(self.angle_mode_label)
        angle_mode_hbox.addWidget(self._angle_mode_combo, 1)
        self.brush_layout.addLayout(angle_mode_hbox)

        self._create_angle_control("固定角度", 0, 360, 0, 'fixed_angle', self.brush_layout)

        self._create_parameter_control("位置抖动 (%)", 0, 100, 0, 'pos_jitter', self.brush_layout)
        self._create_parameter_control("大小抖动 (%)", 0, 100, 0, 'size_jitter', self.brush_layout)
        self._create_angle_control("角度抖动 (度)", 0, 180, 0, 'angle_jitter', self.brush_layout)

        self.main_layout.addWidget(self.brush_group)

        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self._current_params['color'] = (255, 255, 255)
        self._update_color_display(QColor(255, 255, 255))

        self._connect_signals()
        
        self._read_all_parameters()
        # Initial color is set, so emit the full initial state after reading everything else
        self.parameters_changed.emit(self._current_params.copy())

    def _create_parameter_control(self, label_text: str, min_val: int, max_val: int, default_val: int, param_name: str, parent_layout: QVBoxLayout):
        """Helper method to create a parameter control (Slider + SpinBox)."""
        hbox = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFixedWidth(120)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setSingleStep(1)
        slider.setPageStep(5)

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setFixedWidth(50)

        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)

        self._parameter_widgets[param_name] = {'slider': slider, 'spinbox': spinbox, 'default': default_val}
        self._current_params[param_name] = default_val

        hbox.addWidget(label)
        hbox.addWidget(slider, 1)
        hbox.addWidget(spinbox)

        parent_layout.addLayout(hbox)

        slider.valueChanged.connect(lambda value: self._on_parameter_changed(param_name, value))

    def _create_angle_control(self, label_text: str, min_val: int, max_val: int, default_val: int, param_name: str, parent_layout: QVBoxLayout):
        """Helper method to create a parameter control (Slider + SpinBox) for angle."""
        hbox = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFixedWidth(120)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setSingleStep(1)
        slider.setPageStep(10)

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setFixedWidth(50)

        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)

        self._parameter_widgets[param_name] = {'slider': slider, 'spinbox': spinbox, 'default': default_val}
        self._current_params[param_name] = default_val

        hbox.addWidget(label)
        hbox.addWidget(slider, 1)
        hbox.addWidget(spinbox)

        parent_layout.addLayout(hbox)

        slider.valueChanged.connect(lambda value: self._on_parameter_changed(param_name, value))
        return hbox

    def _create_predefined_color_buttons(self, parent_layout: QVBoxLayout):
        """Creates buttons for predefined colors, arranged in rows using GridLayout."""
        # Use a grid layout for better arrangement of buttons
        color_grid_layout = QGridLayout()
        # Add spacing to align with labels
        color_grid_layout.setContentsMargins(120 + color_grid_layout.spacing(), 0, 0, 0) # Left margin to align under label

        buttons_per_row = 4

        for i, (name, bgr_color) in enumerate(self._chinese_ink_colors_bgr.items()):
            row = i // buttons_per_row
            col = i % buttons_per_row

            color_button = QPushButton(name)
            rgb_color = (bgr_color[2], bgr_color[1], bgr_color[0])

            color_button.setFixedSize(60, 25) # Fixed size buttons

            luminance = 0.299*rgb_color[0] + 0.587*rgb_color[1] + 0.114*rgb_color[2]
            text_color = "black" if luminance > 180 else "white"
            color_button.setStyleSheet(f"background-color: rgb({rgb_color[0]},{rgb_color[1]},{rgb_color[2]}); color: {text_color}; border: 1px solid gray;")

            color_button.clicked.connect(lambda checked, c=bgr_color: self._set_current_color(QColor(c[2], c[1], c[0])))

            color_grid_layout.addWidget(color_button, row, col)

        # Add the grid layout to the parent layout (color_layout)
        parent_layout.addLayout(color_grid_layout)

    def set_available_brush_types(self, brush_types: list[str], default_type: str = 'round'):
        """Populates the brush type combobox and sets the initial state."""
        if self._brush_type_combo is None:
            print("Error: Brush type combobox not initialized.")
            return

        self._brush_type_combo.clear()
        if not brush_types:
            self._brush_type_combo.addItem("N/A")
            self._brush_type_combo.setEnabled(False)
            self._current_params['type'] = None
            return

        self._brush_type_combo.setEnabled(True)
        self._brush_type_combo.addItems(brush_types)

        if default_type in brush_types:
            self._brush_type_combo.setCurrentText(default_type)
        else:
            self._brush_type_combo.setCurrentIndex(0)

        self._current_params['type'] = self._brush_type_combo.currentText()

        try:
             self._brush_type_combo.currentTextChanged.disconnect()
        except TypeError:
             pass
        self._brush_type_combo.currentTextChanged.connect(lambda text: self._on_parameter_changed('type', text))

        self._read_all_parameters()
        self.parameters_changed.emit(self._current_params.copy())

    def _read_all_parameters(self):
        """Reads current values of all controls EXCEPT color."""
        for param_name, widgets in self._parameter_widgets.items():
            self._current_params[param_name] = widgets['spinbox'].value()

        if self._brush_type_combo is not None:
             self._current_params['type'] = self._brush_type_combo.currentText()

        if self._angle_mode_combo is not None:
             self._current_params['angle_mode'] = self._angle_mode_combo.currentText()
        else:
             self._current_params['angle_mode'] = 'Direction'

    def _on_parameter_changed(self, param_name: str, value):
        """Internal slot: Updates param dict and emits signal."""
        # Ensure int values are int, and string values are string
        if isinstance(value, (int, float)):
             self._current_params[param_name] = int(value) # Store numeric as int
        else:
             self._current_params[param_name] = value # Store string as string

        self.parameters_changed.emit(self._current_params.copy())

    def _on_angle_mode_changed(self, text: str):
        """Internal slot: Handles angle mode combo box change."""
        self._on_parameter_changed('angle_mode', text)
        # TODO: Implement showing/hiding fixed angle/jitter specific controls based on mode

    def _pick_color(self):
        """Slot: Opens the color dialog to pick a color."""
        if self._color_dialog is None:
             self._color_dialog = QColorDialog(self)
             # Add "ShowAlphaChannel" option if you plan to support alpha later
             # self._color_dialog.setOption(QColorDialog.ShowAlphaChannel)

             # --- FIX: Attempt to set dialog window title for better clarity ---
             self._color_dialog.setWindowTitle("选择笔刷颜色")

             # Connect color dialog signals
             self._color_dialog.colorSelected.connect(self._set_current_color)
             # self._color_dialog.currentColorChanged.connect(self._update_color_display) # Optional: Real-time preview

        current_bgr = self._current_params.get('color', (255, 255, 255))
        self._color_dialog.setCurrentColor(QColor(current_bgr[2], current_bgr[1], current_bgr[0]))

        self._color_dialog.exec_()

    def _set_current_color(self, color: QColor):
        """Sets the brush color from a QColor object."""
        if color.isValid():
            bgr_color = (color.blue(), color.green(), color.red())
            self._current_params['color'] = bgr_color
            self._update_color_display(color)
            self.parameters_changed.emit(self._current_params.copy())

    def _update_color_display(self, color: QColor):
        """Updates the current color display QFrame."""
        if self._color_frame:
            self._color_frame.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")

    def _connect_signals(self):
        if self._angle_mode_combo is not None:
             try:
                  self._angle_mode_combo.currentTextChanged.disconnect()
             except TypeError:
                  pass
             self._angle_mode_combo.currentTextChanged.connect(self._on_angle_mode_changed)

    def get_current_parameters(self) -> dict:
        """Returns current brush parameter values."""
        self._read_all_parameters()
        return self._current_params.copy()