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
        self._brush_type_combo = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)

        self.brush_group = QGroupBox("笔刷参数")
        self.brush_layout = QVBoxLayout(self.brush_group)

        self._create_parameter_control("大小", 1, 100, 40, 'size', self.brush_layout)
        self._create_parameter_control("密度", 0, 100, 60, 'density', self.brush_layout)
        self._create_parameter_control("湿润度", 0, 100, 0, 'wetness', self.brush_layout)
        self._create_parameter_control("飞白", 0, 100, 20, 'feibai', self.brush_layout)

        self.brush_type_label = QLabel("笔刷类型:")
        self.brush_type_label.setFixedWidth(60)
        self._brush_type_combo = QComboBox()

        brush_type_hbox = QHBoxLayout()
        brush_type_hbox.addWidget(self.brush_type_label)
        brush_type_hbox.addWidget(self._brush_type_combo)
        self.brush_layout.addLayout(brush_type_hbox)

        self.main_layout.addWidget(self.brush_group)

        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Initial params read and signals connected handled by set_available_brush_types in MainWindow

    def _create_parameter_control(self, label_text: str, min_val: int, max_val: int, default_val: int, param_name: str, parent_layout: QVBoxLayout):
        """Helper method to create a parameter control (Slider + SpinBox)."""
        hbox = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFixedWidth(60)

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
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)

        parent_layout.addLayout(hbox)

        slider.valueChanged.connect(lambda value: self._on_parameter_changed(param_name, value))

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
            print("Warning: No available brush types provided.")
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

        # Read all parameters (including initial type) and emit the first signal
        self._read_all_parameters()
        self.parameters_changed.emit(self._current_params.copy())

    def _read_all_parameters(self):
        """Reads current values of all controls."""
        for param_name, widgets in self._parameter_widgets.items():
            self._current_params[param_name] = widgets['spinbox'].value()

        if self._brush_type_combo is not None:
             self._current_params['type'] = self._brush_type_combo.currentText()

    def _on_parameter_changed(self, param_name: str, value):
        """Internal slot: Updates param dict and emits signal."""
        self._current_params[param_name] = value
        self.parameters_changed.emit(self._current_params.copy())

    def _connect_signals(self):
        # Parameter change signals connected in _create_parameter_control and set_available_brush_types
        pass

    def get_current_parameters(self) -> dict:
        """Returns current brush parameter values."""
        self._read_all_parameters()
        return self._current_params.copy()