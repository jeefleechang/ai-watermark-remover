# AI Watermark Remover / AI 图片去水印小工具

一个基于 OpenCV 的轻量桌面工具，用于去除 AI 生成图片角落的水印 logo / 文字（如即梦、豆包、Midjourney 等右下角水印）。无需联网，图片不上传，本地处理，保护隐私。

A lightweight local desktop tool (OpenCV + Tkinter) to remove corner watermarks from AI-generated images. Works fully offline.

![修复前后对比](docs/compare.png)

## 功能 / Features

- 🖱️ **框选去水印**：鼠标拖拽框选水印区域，可框选多处，支持撤销 / 清空
- 🧠 **两种修复算法**：
  - **TELEA**：适合小 logo、文字水印（默认）
  - **NS（Navier-Stokes）**：适合面积稍大的区域
- 🔧 修复半径可调，实时预览效果
- 💾 单张另存（原图不动，自动加 `_nowm` 后缀）
- 📦 **批量处理**：框好一张样例后，对整个文件夹按同一位置批量去水印；不同尺寸的图片自动按比例换算选区
- 🈲 完整兼容中文路径和文件名

## 效果与边界 / Limitations

- ✅ 角落小 logo、小号文字水印：效果好
- ⚠️ 半透明居中大水印 / 大面积平铺水印：会留下修复痕迹，这类场景建议使用深度学习修复模型（如 LaMa）

## 环境要求 / Requirements

- Windows / macOS / Linux（Windows 下提供一键启动脚本）
- Python 3.9+

依赖：

```
opencv-python-headless
pillow
numpy
```

> macOS/Linux 如需使用系统 Python，请先创建虚拟环境。`opencv-python-headless` 为无 GUI 的精简版 OpenCV（本程序界面由 Tkinter 提供）。

## 快速开始 / Quick Start

```bash
# 1. 克隆
git clone https://github.com/jeefleechang/ai-watermark-remover.git
cd ai-watermark-remover

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt

# 3. 运行
python app.py
```

**Windows 用户**：完成上述安装后，可直接双击 `run.bat` 启动（无控制台黑窗）。

## 使用说明 / Usage

1. 点击「打开图片」选择一张图片
2. 鼠标拖拽框选水印区域（黄框），可多次框选多处水印
3. 点击「预览修复」查看效果；不满意可「撤销选区」后重新框选
4. 满意后点击「另存为」保存
5. 如需批量：先在一张样例图上框好位置 → 点击「批量处理文件夹」→ 选择文件夹，结果输出到该文件夹下的 `nowm_output/` 子目录

## 自测 / Self-test

```bash
python tests/selftest.py
```

自动生成一张带水印的测试图，跑通「框选 → 修复」管线并校验水印已被去除。

## 技术实现 / How it works

1. 将用户框选区域写入二值 mask，并向外膨胀若干像素以覆盖水印边缘
2. 使用 OpenCV `cv2.inpaint()`（TELEA / NS）基于周围像素对 mask 区域进行纹理修复
3. 批量模式下，选区按图片宽高比例映射到不同分辨率的图片

## License

MIT
