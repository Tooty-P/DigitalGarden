# Magic Canvas AI

Gesture-Controlled Anime AI Art Generator

Magic Canvas AI 是一个基于 Python 的手势绘画与 AI 图像生成原型项目。用户可以通过摄像头识别食指位置，在 Pygame 窗口中进行空气绘画；系统会导出草图，交给可替换的 AI 接口生成图片描述 Prompt，再通过图片生成接口展示生成结果。

当前项目默认使用模拟 AI 分析和模拟图片生成，不会调用真实 API。代码已经预留 DeepSeek、豆包、GPT、OpenAI Image API、Stable Diffusion 等后续替换入口。

## Core Flow

```text
手势绘画
↓
保存 / 导出草图
↓
AIClient 理解草图
↓
Prompt Builder 生成二次元图片描述
↓
ImageGenerator 生成图片路径
↓
Pygame 窗口展示生成结果
```

## Features

- 使用 OpenCV 打开摄像头。
- 使用 MediaPipe HandLandmarker 获取食指指尖位置。
- 拇指和食指捏合时绘制发光魔法线条；松开捏合时只移动光标。
- 支持画笔平滑，减少手势抖动。
- 支持多种画笔颜色和画笔粗细。
- 摄像头或手势识别不可用时，可切换鼠标备用绘画模式。
- 支持导出 AI 可读取的草图 PNG。
- 支持模拟 AI 草图理解，生成二次元风格 Prompt。
- 支持模拟图片生成，并在窗口右侧展示结果。
- API 设计可替换，不绑定具体 AI 服务。

## Controls

| Key | 功能 |
| --- | --- |
| `C` | 清空画布 |
| `S` | 保存当前草图 |
| `G` | 执行 AI 流程：导出草图、生成 Prompt、生成并展示图片 |
| `M` | 切换鼠标备用绘画模式 |
| 拇指 + 食指捏合 | 开始绘画 |
| 松开捏合 | 停止绘画，只移动光标 |
| `TAB` | 切换下一个画笔颜色 |
| `1` - `5` | 选择指定画笔颜色 |
| `[` / `-` | 减小画笔粗细 |
| `]` / `=` | 增大画笔粗细 |
| `Q` / `ESC` | 退出程序 |

## Project Structure

```text
gesture_garden/
├── main.py                         # 主程序入口：窗口、绘画、AI 流程、结果展示
├── hand_tracker.py                 # 摄像头与 MediaPipe 手势追踪
├── utils.py                        # 通用保存工具
├── requirements.txt                # 项目依赖
├── run.ps1                         # PowerShell 运行脚本
├── assets/
│   └── hand_landmarker.task         # MediaPipe 手部关键点模型
├── drawing/
│   ├── canvas.py                    # Canvas 画布对象
│   ├── stroke.py                    # Stroke 连续笔画对象
│   └── sketch_exporter.py           # 草图导出到 data/sketches
├── ai/
│   ├── config.py                    # AI Provider / API Key / 模型配置
│   ├── ai_client.py                 # 可替换 AIClient 与 Provider 接口
│   └── prompt_builder.py            # 根据分析结果构建二次元 Prompt
├── generation/
│   └── image_generator.py           # 可替换图片生成接口，当前为模拟生成
├── data/
│   ├── sketches/                    # 导出的草图 PNG，运行时生成
│   └── generated/                   # 模拟生成图片，运行时生成
├── test_ai_client.py                # AIClient 模拟分析测试
├── test_image_generator.py          # 图片生成接口测试
└── test_prompt_builder.py           # Prompt Builder 测试
```

## Installation

推荐使用 Python 3.12。

```powershell
py -3.12 -m pip install pygame opencv-python mediapipe numpy
```

如果你使用项目虚拟环境，也可以先激活 `.venv` 后安装依赖。

## Run

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
py -3.12 main.py
```

运行后会打开 960x540 的 Pygame 窗口。把手放到摄像头前，移动食指可以移动光标；拇指和食指捏合时会绘制发光线条。按 `G` 会启动模拟 AI 生成流程，窗口会显示 Loading，完成后右侧会展示生成结果。

## Output Files

按 `S` 或 `G` 后，草图会导出到：

```text
gesture_garden/data/sketches/
```

按 `G` 后，模拟生成图片会保存到：

```text
gesture_garden/data/generated/
```

这些输出文件属于运行产物，默认不提交到 Git。

## AI Configuration

当前默认配置位于：

```text
gesture_garden/ai/config.py
```

默认值：

```python
AI_PROVIDER = "none"
API_KEY = ""
API_MODEL = ""
```

无 API Key 时，项目会自动返回模拟分析结果，保证主程序正常运行。未来可以把 `AI_PROVIDER` 切换为 `deepseek`、`doubao` 或 `gpt`，并填写对应 API Key、模型名和服务地址。

## Tests

语法检查：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
py -3.12 -m py_compile main.py hand_tracker.py drawing/canvas.py drawing/stroke.py drawing/sketch_exporter.py ai/ai_client.py ai/prompt_builder.py generation/image_generator.py
```

测试 Prompt 构建：

```powershell
py -3.12 test_prompt_builder.py
```

测试 AIClient 模拟分析：

```powershell
py -3.12 test_ai_client.py
```

测试图片生成接口：

```powershell
py -3.12 test_image_generator.py
```

## Current Status

当前项目已经完成可演示原型：

```text
手势绘画 → 草图导出 → AI 理解 → Prompt → 图片生成接口 → 展示结果
```

后续可继续优化：

- 捏合手势控制开始 / 停止绘画。
- 更完整的生成结果面板。
- 接入真实多模态文本 AI 分析草图。
- 接入真实图片生成 API。
- 制作作品集截图、演示视频和最终项目展示页。

