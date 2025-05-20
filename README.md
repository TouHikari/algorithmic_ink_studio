# 算法水墨：数字水墨画创作工具

**Algorithm Ink Wash Studio**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

这是一个用于模拟中国水墨画创作过程的数字绘画工具。本项目旨在运用编程技术，探索水墨画独特的笔触、墨韵和留白等艺术表现形式，让用户可以在数字画布上体验水墨画的创作乐趣。

This is a digital painting tool designed to simulate the process of creating Chinese ink wash paintings. This project aims to explore the unique artistic expressions of ink wash painting, such as brush strokes, ink rendering (墨韵), and negative space (留白), by using programming techniques. It allows users to experience the joy of ink wash creation on a digital canvas.

## 功能特性 (Features)

本项目目前专注于提供自由绘画功能，模拟水墨笔触的效果：

The project currently focuses on providing freehand drawing capabilities, simulating the effects of ink wash brushwork:

*   **数字画布 (Digital Canvas):** 一个可供用户进行绘画的数字画布。
*   **模拟水墨笔刷 (Simulated Ink Brush):** 提供一个模拟毛笔属性的笔刷。
*   **参数调整 (Parameter Control):** 用户可以通过参数控制（如大小、密度、湿润度、飞白）来调节笔刷的艺术效果。
    *   **大小 (Size):** 控制笔画的粗细。
    *   **密度 (Density):** 控制墨色的浓淡。
    *   **湿润度 (Wetness):** 控制墨迹的晕染扩散程度（墨韵）。高湿润度会产生明显的墨迹边缘柔化和向留白区域的渗透效果。
    *   **飞白 (Feibai):** 模拟干笔触中因墨量不足或运笔过快产生的笔画断续和纹理，露出纸色。
*   **延迟晕染效果 (Delayed Diffusion Effect):** 湿润度带来的晕染效果会在用户释放鼠标（完成一次笔画）后进行计算并显现。
*   **载入与保存 (Load & Save):** 可以载入图片到画布上进行创作，也可以保存当前的画布内容为图片文件。

## 技术栈 (Technical Stack)

本项目使用以下技术和库：

The project is built using the following technologies and libraries:

*   **Python:** 主要编程语言。
*   **PyQt5 (或 PySide2):** 用于构建图形用户界面 (GUI)。
*   **OpenCV:** 用于图像处理，包括图像读写、缩放、颜色空间转换、滤波器应用（如双边滤波）等。
*   **NumPy:** 用于高效处理图像数据（作为多维数组）。

## 算法原理简述 (Brief Explanation of Algorithms)

本项目中的水墨效果主要通过以下算法步骤模拟：

The ink wash effects in this project are primarily simulated through the following algorithmic steps:

1.  **笔触墨量计算 (Brush Ink Application):**
    *   使用加载的**笔刷形状图片 (Brush Shape Mask)** 作为基础笔头形态。
    *   根据用户的**笔刷大小 (Size)** 对笔刷形状进行缩放。
    *   根据笔画**方向 (Stroke Direction)** 计算角度，对笔刷形状进行旋转。
    *   结合笔刷的**密度 (Density)** 和**飞白 (Feibai)** 参数以及随机噪点，计算笔刷在画布上每个像素点应该应用的墨量（或者说，将像素变暗的程度）。高密度和笔刷形状不透明区域应用更多墨量，高飞白区域随机减少墨量应用。
    *   将计算出的墨量叠加到画布的像素上，使对应区域变暗。

2.  **延迟局部晕染 (Delayed Localized Diffusion):**
    *   在用户完成一个笔画（释放鼠标）后，程序会识别出本次笔画直接影响的区域。
    *   计算一个稍大于这个核心区域的**处理区域 (Processing Area)**，大小取决于笔刷大小和**湿润度 (Wetness)** 参数。
    *   对这个处理区域应用**双边滤波 (Bilateral Filter)**。这是一种图像平滑滤波器，它在平坦区域进行模糊，同时倾向于保留边缘，有助于模拟墨迹边缘的过渡。
    *   将模糊后的结果与原始（未模糊）的处理区域像素进行**智能混合**（例如，使用 `np.minimum` 操作）。这种混合方式旨在只采纳模糊结果中使像素变暗的部分，模拟墨水向纸张渗透导致变深的效果，同时避免提亮已有深色区域或产生方形边界。

## 项目结构 (Project Structure)

项目的核心文件结构如下：

The core structure of the project is organized as follows:

```
algorithmic_ink_studio/
├── main.py             # 程序入口点 (Main entry point)
├── gui/
│   ├── __init__.py
│   ├── main_window.py  # 主窗口UI和事件处理 (Main window UI and event handling)
│   ├── ink_canvas_widget.py # 画布显示和鼠标交互 (Canvas display and mouse interaction)
│   └── control_panel.py   # 参数控制面板UI (Parameter control panel UI)
├── processing/
│   ├── __init__.py
│   ├── brush_engine.py    # 笔刷算法核心，墨迹应用和晕染 (Core brush algorithms, ink application, diffusion)
│   ├── lienzo.py          # 画布底层数据管理 (Underlying canvas data management)
│   └── utils.py           # 辅助函数 (Utility functions)
└── resources/          # 存放资源文件，如笔刷形状图片 (Resource files, e.g., brush shape images)
    └── brush_round.png # 默认圆形笔刷形状图片 (Default round brush shape image)
    └── ... (other brush shape images)
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
    pip install opencv-python numpy PyQt5 # 或者 PySide2
    ```

### 准备笔刷形状 (Prepare Brush Shapes)

*   项目已经内置有默认的笔刷形状。
*   如果想使用自己的笔刷，请按以下步骤操作：
    *   在项目根目录下创建 `resources` 文件夹，如果在源代码中没有包含的话。
    *   在 `resources` 文件夹中放入至少一个名为 `brush_round.png` 的**灰度 PNG 图片**。这张图片应该代表你想要的圆形毛笔笔头形状，其中**黑色代表不透明墨迹，白色代表完全透明（纸张）**。中间的灰度值表示半透明。你可以从在线资源获取这类图片，或者自己手绘/用软件制作。

### 运行程序 (Running the Program)

1.  确保你的虚拟环境已激活。
2.  在终端中，导航到项目的根目录 `algorithmic_ink_studio`。
3.  运行 `main.py` 文件：
    ```bash
    python main.py
    ```

## 使用说明 (Usage)

1.  程序启动后会显示主窗口，左侧是画布区域，右侧是笔刷参数控制面板。
2.  使用右侧的滑块和SpinBox调整笔刷的**大小、密度、湿润度、飞白**等参数。
3.  在画布区域按住**鼠标左键并拖动**进行绘画。你会看到笔画立即显现（不包含最终晕染），释放鼠标后，湿润度带来的晕染效果会随之出现。
4.  使用顶部菜单或工具栏的“文件”->“加载图片”载入一张图片到画布上，可以在图片基础上绘画。
5.  使用“文件”->“清空画布”来清除画布内容。
6.  使用“文件”->“保存画布”来保存你的作品为图片文件。

## 未来改进方向 (Future Work)

本项目可以进一步扩展，例如：

*   **更多笔刷类型 (More Brush Types):** 支持加载和使用不同形状（如平头、尖头、散开等）的笔刷图片。
*   **压感支持 (Pressure Sensitivity):** 如果使用数位板，读取压感信息来动态调整笔刷的大小和密度。
*   **更高级的墨韵模拟 (More Advanced Diffusion):** 探索更复杂的物理扩散模型（如 Reaction-Diffusion、各向异性扩散）或基于纸张纹理的扩散。
*   **纸张纹理叠加 (Paper Texture Overlay):** 将纸张纹理叠加到绘制结果上，增强真实感。
*   **撤销/重做 (Undo/Redo):** 实现操作历史记录功能。
*   **画布缩放与平移 (Zoom & Pan):** 支持在大画布上进行局部操作。
*   **更灵活的笔刷混合模式 (More Flexible Blending):** 模拟不同的墨色叠加效果。
*   **颜色调味 (Color Tinting):** 在灰度水墨基础上，添加淡淡的颜色。

## 贡献 (Contributing)

如果你对本项目感兴趣并希望做出贡献，欢迎提交 Pull Request（如果放在代码托管平台）。

## 致谢 (Credits)

本项目使用了以下开源库：

*   PyQt (或 PySide)
*   OpenCV
*   NumPy

## 许可证 (License)

本项目根据 [MIT 许可证](LICENSE) 许可。

This project is licensed under the [MIT License](LICENSE).
