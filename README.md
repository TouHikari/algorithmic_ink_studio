# 算法水墨：数字水墨画创作工具

**Algorithm Ink Wash Studio**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

这是一个用于模拟中国水墨画创作过程的数字绘画工具。本项目旨在运用编程技术，探索水墨画独特的笔触、墨韵和留白等艺术表现形式，让用户可以在数字画布上体验水墨画的创作乐趣。

This is a digital painting tool designed to simulate the process of creating Chinese ink wash paintings. This project aims to explore the unique artistic expressions of ink wash painting, such as brush strokes, ink rendering (墨韵), and negative space (留白), by using programming techniques. It allows users to experience the joy of ink wash creation on a digital canvas.

## 功能特性 (Features)

本项目目前专注于提供自由绘画功能，模拟水墨笔触的效果：

The project currently focuses on providing freehand drawing capabilities, simulating the effects of ink wash brushwork:

*   **数字画布 (Digital Canvas):** 一个可供用户进行绘画的数字画布，底层使用 NumPy 数组存储图像数据。
    *   支持画布的缩放与平移操作。
*   **模拟水墨笔刷 (Simulated Ink Brush):** 提供一个模拟毛笔属性的笔刷。
    *   支持加载自定义的笔刷形状图片 (`.png`)。
    *   支持笔刷参数调整，包括大小、密度、湿润度、飞白、硬度、流量。
    *   支持不同的笔刷角度模式（跟随方向、固定角度、随机角度、带抖动）。
    *   支持笔触的位置、大小、角度抖动模拟。
*   **颜色选择 (Color Selection):** 支持使用拾色器选择颜色，也提供多种预设的国画颜色。
*   **延迟晕染效果 (Delayed Diffusion Effect):** 湿润度带来的墨迹晕染效果会在用户释放鼠标（完成一次笔画）后，通过图像处理算法（局部双边滤波和智能混合）计算并显现。
*   **橡皮擦工具 (Eraser Tool):** 提供擦除画布内容的工具。
*   **载入与保存 (Load & Save):** 可以从文件载入图片 (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`) 到画布上进行创作，也可以保存当前的画布内容为图片文件 (`.png`, `.jpg`, `.bmp`)。
*   **新建画布 (New Canvas):** 支持创建指定尺寸的空白画布。
*   **清空画布 (Clear Canvas):** 快速填充画布为白色。
*   **撤销/重做 (Undo/Redo):** 支持有限次数的操作历史记录。

## 技术栈 (Technical Stack)

本项目使用以下技术和库：

The project is built using the following technologies and libraries:

*   **Python:** 主要编程语言。
*   **PyQt5:** 用于构建图形用户界面 (GUI)。支持对系统语言环境进行本地化（UI元素会自动翻译，如果存在对应的 Qt 翻译文件）。
*   **OpenCV (通过 `opencv-python`)**: 用于图像处理后端，包括图像读写、颜色空间转换、缩放、旋转、滤波（双边滤波）、像素操作等。
*   **NumPy:** 用于高效处理图像数据（作为多维数组）。

## 算法原理简述 (Brief Explanation of Algorithms)

本项目中的水墨效果主要通过以下算法步骤模拟：

The ink wash effects in this project are primarily simulated through the following algorithmic steps:

1.  **笔触像素应用 (Brush Pixel Application):**
    *   程序预加载不同的**笔刷形状掩膜 (Brush Shape Mask)**，这些掩膜是表示笔头不透明度的浮点数数组。
    *   根据当前的**笔刷大小 (Size)** 和**笔刷类型 (Type)**，获取对应的缩放后的笔刷掩膜。
    *   根据**角度模式 (Angle Mode)** 和笔画段的**移动方向**或**固定/随机**值，计算笔刷旋转角度，并对笔刷掩膜进行旋转。
    *   结合笔刷的**硬度 (Hardness)** 参数调整掩膜的透明度（使其更集中或更分散）。
    *   考虑**密度 (Density)** 和**流量 (Flow)** 计算基础不透明度。
    *   通过**飞白 (Feibai)** 参数和局部的随机噪点，进一步调整笔刷在画布上每个像素点的最终叠加不透明度。高飞白区域会随机产生低不透明度点，露出纸色。
    *   将计算出的不透明度应用于画布的对应像素区域。对于画笔工具，墨色叠加方式为取画布原有颜色和笔刷颜色中较暗的那个（模拟墨水下渗变深）。对于橡皮擦工具，则根据不透明度混合纸白色，模拟擦除效果。
    *   为确保笔画连续，在鼠标移动过程中，会在两个采样点之间进行插值，并在插值点应用单个笔刷印迹（"Stamp"）。插值步长与笔刷大小和位置抖动相关。

2.  **延迟局部晕染 (Delayed Localized Diffusion):**
    *   当鼠标左键释放，表示一次完整的笔画或擦除操作结束。
    *   如果当前工具是橡皮擦，则不做晕染处理。
    *   如果当前工具是画笔，并且**湿润度 (Wetness)** 参数大于 0，程序会识别出本次笔画段影响的**总区域 (Inked Region)**。
    *   计算一个稍大于这个总区域的**处理区域 (Processing Area)**，其扩展范围由**湿润度**和**笔刷大小**决定。
    *   获取该处理区域的原始图像数据。
    *   对这个处理区域应用 **OpenCV 的双边滤波 (Bilateral Filter)**。双边滤波是一种非线性平滑滤波器，它根据像素值的相似性和空间距离进行加权平均，能够在模糊平坦区域（模拟墨水晕开）的同时保留锐利的边缘（避免破坏笔画主要轮廓），这非常适合模拟水墨的自然扩散效果。滤波的强度和范围由**湿润度**参数控制。
    *   将滤波后的结果与原始处理区域的图像数据进行**智能混合**。混合方法通常为沿着像素的各个通道取最小值 (`np.minimum`)。这种混合方式的目的是只采纳模糊结果中那些比原始像素更“暗”的部分，从而模拟墨水吸收后颜色变深、向湿润区域渗透的现象，同时避免墨迹提亮或产生边界效应。
    *   将混合后的结果（即应用了晕染效果的部分区域）粘贴回主画布中。

## 项目结构 (Project Structure)

项目的核心文件结构如下：

The core structure of the project is organized as follows:

```
algorithmic_ink_studio/
├── .gitignore        # Git忽略文件，指定哪些文件不应被版本控制 (Git ignore file, specifies which files should not be version controlled)
├── LICENSE           # 项目许可证信息 (Project license information)
├── main.py           # 程序主入口，启动应用和主窗口UI (Main entry point, launches the application and main window UI)
├── README.md         # 项目说明文件 (Project README file)
├── gui/              # 图形用户界面 (GUI) 相关文件 (Graphical User Interface related files)
│   ├── __init__.py   # 标记此目录为一个Python包 (Marks this directory as a Python package)
│   ├── control_panel.py   # 右侧参数控制面板的UI和逻辑 (UI and logic for the right-side parameter control panel)
│   ├── ink_canvas_widget.py # Canvas画布的显示、鼠标交互（绘画、平移、缩放）逻辑 (Canvas widget display and mouse interaction (drawing, panning, zooming) logic)
│   └── main_window.py  # 主窗口的UI布局、菜单、工具栏、信号连接及应用核心逻辑（如历史记录）(Main window UI layout, menus, toolbar, signal connections, and core application logic (e.g., history))
├── processing/       # 图像处理和笔刷算法的核心文件 (Core files for image processing and brush algorithms)
│   ├── __init__.py   # 标记此目录为一个Python包 (Marks this directory as a Python package)
│   ├── brush_engine.py    # 笔刷形状处理、笔触应用和墨迹扩散（晕染）算法实现 (Brush shape handling, brush stroke application, and ink diffusion (blur) algorithm implementation)
│   ├── lienzo.py          # 画布的底层数据（基于NumPy数组）管理类 (Underlying canvas data (NumPy array) management class)
│   └── utils.py           # 包含图像数据格式转换等通用辅助函数 (Contains general utility functions like image data format conversion)
└── resources/          # 存储资源文件（如笔刷形状、图标等）(Stores resource files (e.g., brush shapes, icons, etc.))
    ├── brush_dry.png   # "Dry"类型笔刷的形状图片 ("Dry" brush shape image)
    ├── brush_flat.png  # "Flat"类型笔刷的形状图片 ("Flat" brush shape image)
    ├── brush_round.png # "Round"类型笔刷的形状图片 ("Round" brush shape image)
    ├── brush_tapered.png # "Tapered"类型笔刷的形状图片 ("Tapered" brush shape image)
    └── icons/          # 应用程序工具栏和菜单项使用的图标文件 (Icon files used by the application toolbar and menu items)
        ├── brush.png
        ├── clear.png
        ├── eraser.png
        ├── new.png
        ├── open.png
        ├── redo.png
        ├── save.png
        ├── undo.png
        ├── zoom_actual.png
        ├── zoom_fit.png
        ├── zoom_in.png
        ├── zoom_out.png
        ├── brush.png
        └── eraser.png
```

## 快速开始 (Getting Started)

### 前置条件 (Prerequisites)

*   Python 3.6 或更高版本。

### 安装 (Installation)

1.  **克隆或下载源代码**到你的本地计算机。
2.  **创建并激活虚拟环境**（推荐）：
    ```bash
    python -m venv ink_env
    # Windows
    .\ink_env\Scripts\activate
    # macOS/Linux
    source ink_env/bin/activate
    ```
3.  **安装所需库**：
    ```bash
    pip install opencv-python numpy PyQt5
    ```

### 准备笔刷形状 (Prepare Brush Shapes)

*   项目已包含几个基础的笔刷形状图片在 `resources/` 目录下。
*   这些图片应该是**灰度 PNG 图片**，或者带有透明通道的 PNG。程序会读取其不透明度信息（例如，对于灰度图，黑色代表完全不透明，白色代表完全透明；对于带 Alpha 通道的图，Alpha 通道值决定不透明度）。
*   笔刷图片建议是正方形。

### 运行程序 (Running the Program)

1.  确保你的虚拟环境已激活。
2.  在终端中，导航到项目的根目录 `algorithmic_ink_studio`。
3.  运行 `main.py` 文件：
    ```bash
    python main.py
    ```
    *(注: main.py 尝试加载 Qt 的本地化翻译，如果你的系统语言有对应的 Qt 翻译文件，部分标准 UI 元素可能会显示为本地语言)*

## 使用说明 (Usage)

1.  程序启动后会显示主窗口，左侧是画布区域，右侧是笔刷参数控制面板。
2.  左键拖动画布进行绘画，中键或右键拖动可平移画布视图。
3.  滚轮可缩放画布视图，缩放中心为鼠标滚轮位置。
4.  使用顶部工具栏或“工具”菜单切换“画笔工具”和“橡皮擦工具”。
5.  在右侧的控制面板，使用滑块、SpinBox、下拉菜单调整笔刷的**大小、密度、湿润度、飞白、硬度、流量**、**笔刷类型**、**角度模式**以及各种**抖动**参数。
6.  在右侧控制面板点击“选择颜色...”按钮打开颜色拾色器，或者点击预设的国画颜色按钮快速切换颜色。
7.  使用顶部菜单或工具栏的“文件”->“新建画布”创建一个新的空白画布，可以选择尺寸。
8.  使用“文件”->“加载图片”载入一张图片到画布上。这将替换当前画布内容。
9.  使用“文件”->“清空画布”用白色填充整个画布。
10. 使用“文件”->“保存画布”保存你的作品为图片文件。
11. 使用“编辑”菜单或工具栏的“撤销”和“重做”按钮回溯或前进操作历史（最多保存100步）。
12. 使用“视图”菜单或工具栏的缩放相关操作调整画布的显示比例和位置。

## 未来改进方向 (Future Work)

本项目可以进一步扩展，例如：

*   **更多笔刷高级参数 (More Advanced Brush Parameters):** 探索更多模拟画笔特性的参数，如笔锋、笔触分离等。
*   **压感支持 (Pressure Sensitivity):** 如果使用数位板，读取压感信息来动态调整笔刷的大小、密度或流量。
*   **更高级的墨韵模拟 (More Advanced Diffusion):** 探索更复杂的物理扩散模型（如 Reaction-Diffusion、各向异性扩散）或基于颜色深度的扩散，以实现更丰富自然的晕染效果。
*   **纸张纹理叠加 (Paper Texture Overlay):** 将纸张纹理叠加到绘制结果上，增强真实感。
*   **图层系统 (Layer System):** 允许多个图层进行绘画和编辑。
*   **自定义笔刷包 (Custom Brush Packs):** 支持载入、管理和保存一组笔刷设置和形状。
*   **性能优化 (Performance Optimization):** 提高处理大型画布或复杂笔画时的响应速度。

## 贡献 (Contributing)

如果你对本项目感兴趣并希望做出贡献，欢迎提交 Pull Request。

## 致谢 (Credits)

本项目使用了以下开源库：

*   PyQt5: GUI Framework
*   OpenCV: Image processing
*   NumPy: Numerical operations, especially for image data

## 许可证 (License)

本项目根据 [MIT 许可证](LICENSE) 许可。

This project is licensed under the [MIT License](LICENSE).