# gui/control_panel.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                              QGroupBox, QSpacerItem, QSizePolicy,
                              QSpinBox, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal

class ControlPanel(QWidget):
    parameters_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_params = {}
        self._parameter_widgets = {}
        self._brush_type_combo = None # Existing brush type combo box
        self._angle_mode_combo = None # New angle mode combo box
        self._fixed_angle_widgets = {} # Widgets for fixed angle
        self._jitter_widgets = {} # Widgets for jitter parameters

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)

        self.brush_group = QGroupBox("笔刷参数")
        self.brush_layout = QVBoxLayout(self.brush_group)

        # Existing parameters
        self._create_parameter_control("大小", 1, 100, 40, 'size', self.brush_layout)
        self._create_parameter_control("密度", 0, 100, 60, 'density', self.brush_layout)
        self._create_parameter_control("湿润度", 0, 100, 0, 'wetness', self.brush_layout)
        self._create_parameter_control("飞白", 0, 100, 20, 'feibai', self.brush_layout)

        # New Parameters
        self._create_parameter_control("硬度", 0, 100, 50, 'hardness', self.brush_layout)
        self._create_parameter_control("流量", 0, 100, 100, 'flow', self.brush_layout) # Flow default 100%

        # Brush Type Selection
        self.brush_type_label = QLabel("笔刷类型:")
        self.brush_type_label.setFixedWidth(60)
        self._brush_type_combo = QComboBox()

        brush_type_hbox = QHBoxLayout()
        brush_type_hbox.addWidget(self.brush_type_label)
        brush_type_hbox.addWidget(self._brush_type_combo)
        self.brush_layout.addLayout(brush_type_hbox)

        # Angle Control
        self.angle_mode_label = QLabel("角度模式:")
        self.angle_mode_label.setFixedWidth(60)
        self._angle_mode_combo = QComboBox()
        # Populate angle modes
        self._angle_mode_combo.addItems(["Direction", "Fixed", "Random", "Direction+Jitter", "Fixed+Jitter"])
        self._angle_mode_combo.setCurrentText("Direction") # Default mode

        angle_mode_hbox = QHBoxLayout()
        angle_mode_hbox.addWidget(self.angle_mode_label)
        angle_mode_hbox.addWidget(self._angle_mode_combo)
        self.brush_layout.addLayout(angle_mode_hbox)

        # Fixed Angle Control (Slider + SpinBox)
        # Use a separate helper for angle control as range is different (0-360)
        self._create_angle_control("固定角度", 0, 360, 0, 'fixed_angle', self.brush_layout)

        # Jitter Controls
        self._create_parameter_control("位置抖动 (%)", 0, 100, 0, 'pos_jitter', self.brush_layout)
        self._create_parameter_control("大小抖动 (%)", 0, 100, 0, 'size_jitter', self.brush_layout)
        # Angle Jitter Control (0-180 degrees)
        self._create_angle_control("角度抖动 (度)", 0, 180, 0, 'angle_jitter', self.brush_layout)

        self.main_layout.addWidget(self.brush_group)

        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self._connect_signals() # Connect signals for new controls

    def _create_parameter_control(self, label_text: str, min_val: int, max_val: int, default_val: int, param_name: str, parent_layout: QVBoxLayout):
        """Helper method to create a parameter control (Slider + SpinBox) for 0-100 range unless specified."""
        hbox = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFixedWidth(90) # Adjust width for longer labels

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
        self._current_params[param_name] = default_val # Initialize current params with default value

        hbox.addWidget(label)
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)

        parent_layout.addLayout(hbox)

        slider.valueChanged.connect(lambda value: self._on_parameter_changed(param_name, value))

    def _create_angle_control(self, label_text: str, min_val: int, max_val: int, default_val: int, param_name: str, parent_layout: QVBoxLayout):
        """Helper method to create a parameter control (Slider + SpinBox) for angle (0-360 or 0-180)."""
        hbox = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFixedWidth(90) # Adjust width

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setSingleStep(1)
        slider.setPageStep(10) # Larger page step for angle

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setFixedWidth(50)

        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)

        # Store angle widgets separately or include in _parameter_widgets but distinguish
        # Let's keep them in _parameter_widgets for simplicity, they are numeric
        self._parameter_widgets[param_name] = {'slider': slider, 'spinbox': spinbox, 'default': default_val}
        self._current_params[param_name] = default_val # Initialize current params with default value

        hbox.addWidget(label)
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)

        parent_layout.addLayout(hbox)

        slider.valueChanged.connect(lambda value: self._on_parameter_changed(param_name, value))
        return hbox # Return hbox so it can be potentially shown/hidden

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

        # Initialize the brush type param *after* setting items
        self._current_params['type'] = self._brush_type_combo.currentText()

        # Connect the signal AFTER populating and setting initial text/index
        try:
             self._brush_type_combo.currentTextChanged.disconnect()
        except TypeError:
             pass
        self._brush_type_combo.currentTextChanged.connect(lambda text: self._on_parameter_changed('type', text))

        # Read all parameters (including initial type and angle mode) and emit the first signal
        self._read_all_parameters()
        self.parameters_changed.emit(self._current_params.copy())

    def _read_all_parameters(self):
        """Reads current values of all controls."""
        # Numeric parameters
        for param_name, widgets in self._parameter_widgets.items():
            self._current_params[param_name] = widgets['spinbox'].value()

        # Brush type parameter
        if self._brush_type_combo is not None:
             self._current_params['type'] = self._brush_type_combo.currentText()

        # Angle mode parameter
        if self._angle_mode_combo is not None:
             self._current_params['angle_mode'] = self._angle_mode_combo.currentText()
        else:
             # Ensure angle_mode is initialized even if combo fails
             self._current_params['angle_mode'] = 'Direction'

    def _on_parameter_changed(self, param_name: str, value):
        """Internal slot: Updates param dict and emits signal."""
        self._current_params[param_name] = value
        self.parameters_changed.emit(self._current_params.copy())

    def _on_angle_mode_changed(self, text: str):
        """Internal slot: Handles angle mode combo box change."""
        self._on_parameter_changed('angle_mode', text)
        # TODO: Implement showing/hiding fixed angle/jitter specific controls based on mode

    def _connect_signals(self):
        # Parameter change signals for sliders/spinboxes are connected in _create_parameter_control and _create_angle_control.
        # Brush type combo signal is connected in set_available_brush_types.
        # Connect angle mode combo box signal
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