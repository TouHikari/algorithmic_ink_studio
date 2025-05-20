# gui/control_panel.py (Modified - Removed Image Conversion Controls)

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                              QGroupBox, QSpacerItem, QSizePolicy, QPushButton,
                              QSpinBox, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal # Ensure pyqtSignal is imported

class ControlPanel(QWidget):
    # Define a signal that emits a dictionary of brush parameters when they change
    # Only brush parameters are relevant now
    parameters_changed = pyqtSignal(dict)
    # Remove generate_image_requested signal
    # generate_image_requested = pyqtSignal() # REMOVED

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_params = {}
        self._parameter_widgets = {}

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)

        # --- Brush Parameters Group ---
        self.brush_group = QGroupBox("笔刷参数")
        self.brush_layout = QVBoxLayout(self.brush_group)

        self._create_parameter_control("大小", 1, 100, 40, 'size', self.brush_layout)
        self._create_parameter_control("密度", 0, 100, 60, 'density', self.brush_layout)
        self._create_parameter_control("湿润度", 0, 100, 0, 'wetness', self.brush_layout)
        self._create_parameter_control("飞白", 0, 100, 20, 'feibai', self.brush_layout)

        # TODO: Brush Type Selection remains a potential feature
        # self.brush_type_label = QLabel("笔刷类型:")
        # self.brush_type_combo = QComboBox()
        # self.brush_type_combo.addItems(["Round"])
        # self.brush_layout.addWidget(self.brush_type_label)
        # self.brush_layout.addWidget(self.brush_type_combo)
        # self.brush_type_combo.currentTextChanged.connect(lambda text: self._on_parameter_changed('type', text))
        # self._current_params['type'] = self.brush_type_combo.currentText()

        self.main_layout.addWidget(self.brush_group)

        # --- Image Conversion Parameters Group ---
        # REMOVE this group completely
        # self.image_conversion_group = QGroupBox("图片转换参数") # REMOVED
        # ... (remove creation of its layout and widgets) ...
        # self.generate_button = QPushButton("生成水墨画") # REMOVED

        # --- Add a spacer to push controls to the top ---
        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self._read_all_parameters() # Ensure self._current_params is populated

        self._connect_signals()

        # No need to hide/show groups based on mode anymore, only brush group exists.

    def _create_parameter_control(self, label_text: str, min_val: int, max_val: int, default_val: int, param_name: str, parent_layout: QVBoxLayout):
        """Helper method to create a parameter control."""
        hbox = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFixedWidth(60)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setSingleStep(1)
        slider.setPageStep(5)
        # slider.setTickInterval(...) # Optional
        # slider.setTickPosition(...) # Optional

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setFixedWidth(50)

        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)

        self._parameter_widgets[param_name] = {'slider': slider, 'spinbox': spinbox, 'default': default_val}

        hbox.addWidget(label)
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)

        parent_layout.addLayout(hbox)

        # Connect the slider's valueChanged signal to our internal handler
        slider.valueChanged.connect(lambda value: self._on_parameter_changed(param_name, value))

    def _read_all_parameters(self):
        """Reads current values."""
        for param_name, widgets in self._parameter_widgets.items():
            self._current_params[param_name] = widgets['slider'].value()

    def _on_parameter_changed(self, param_name: str, value: int):
        """Internal slot: Updates param dict and emits signal."""
        # print(f"Parameter '{param_name}' changed to {value}")
        self._current_params[param_name] = value
        # Emit brush parameters only (image conversion params are removed)
        self.parameters_changed.emit(self._current_params.copy())

    def _connect_signals(self):
        """Connects signals."""
        # No generate button signal anymore # REMOVED
        # self.generate_button.clicked.connect(self.generate_image_requested.emit) # REMOVED

        # Parameter change signals connected in _create_parameter_control

    def get_current_parameters(self) -> dict:
        """Returns current brush parameter values."""
        return self._current_params.copy()

    # Remove methods related to showing different control groups
    # def show_brush_controls(self): # REMOVED - Only brush controls exist
    #     self.brush_group.show()
    #     self.image_conversion_group.hide() # REMOVED

    # def show_image_conversion_controls(self): # REMOVED
    #     self.brush_group.hide()
    #     self.image_conversion_group.show() # REMOVED