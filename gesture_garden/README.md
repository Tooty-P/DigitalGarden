# Magic Canvas AI

手势动漫 AI 绘画画布。

Magic Canvas AI 是一个 Python + Pygame 原型项目。用户可以通过摄像头识别手部动作，在画布中进行手势绘画；也可以切换到鼠标备用模式。绘制完成后，程序会保存草图，根据当前主题和用户输入的关键词生成英文 Prompt，并调用 SiliconFlow 的图片生成接口生成二次元萌系图片，最后在窗口中展示结果。

## 效果截图

### 绘画与主题选择

![绘画界面](docs/images/sketch.png)

### 生成中

![生成中](docs/images/loading.png)

### 生成结果

![生成结果](docs/images/result.png)

### 生成失败提示

![生成失败提示](docs/images/error.png)

## 当前功能

- 使用 OpenCV 打开摄像头。
- 使用 MediaPipe HandLandmarker 获取食指位置。
- 支持手势绘画、橡皮擦、鼠标备用绘画模式。
- 支持画笔颜色、画笔粗细、橡皮大小和画布缩放。
- 支持按 `S` 保存当前草图。
- 支持按 `G` 自动保存草图、生成 Prompt、调用 SiliconFlow 生成图片。
- 支持 `drawing`、`generating`、`result`、`error` 四种界面状态。
- 生成中显示 Loading，失败时显示友好错误提示。
- 支持主题切换：`garden`、`pet`、`room`、`sky_island`、`character`。
- 支持关键词输入框，让用户补充生成内容，例如 `dog and cat`。
- 右侧面板显示摄像头、工具状态、主题快捷键、关键词、颜色和生成结果预览。

## 生成流程

```text
用户绘画
↓
按 G
↓
导出当前草图到 data/sketches/
↓
读取当前主题和关键词
↓
Prompt Builder 生成英文 Prompt
↓
SiliconFlowImageGenerator 调用图片生成 API
↓
下载生成图片到 outputs/generated/
↓
Pygame 窗口展示生成结果
```

当前版本暂时没有让 AI 自动理解草图内容。为了提升生成结果和用户输入的相关性，程序会使用：

```text
主题描述 + 用户关键词 + 固定二次元萌系风格
```

默认 Prompt 是场景优先。只有选择 `character` 主题时，才会明显偏向人物生成。

## 项目结构

```text
gesture_garden/
├── main.py                         # 主程序入口：窗口、绘画、生成状态、结果展示
├── hand_tracker.py                 # 摄像头与 MediaPipe 手势追踪
├── utils.py                        # 通用保存工具
├── requirements.txt                # Python 依赖
├── run.ps1                         # PowerShell 运行脚本
├── .env                            # 本地 API 配置，不提交到 Git
├── assets/
│   └── hand_landmarker.task         # MediaPipe 手部关键点模型
├── ai/
│   ├── config.py                    # 从 .env 读取 SiliconFlow 配置
│   ├── ai_client.py                 # 预留 AIClient 接口
│   └── prompt_builder.py            # 根据主题和关键词构建 Prompt
├── drawing/
│   ├── canvas.py                    # Canvas 画布对象
│   ├── stroke.py                    # Stroke 连续笔画对象
│   └── sketch_exporter.py           # 草图导出到 data/sketches/
├── generation/
│   ├── image_generator.py           # 旧版可替换图片生成接口
│   ├── siliconflow_generator.py     # SiliconFlow API 调用与图片下载
│   └── test_zimage.py               # Z-Image-Turbo 独立测试
├── data/
│   └── sketches/                    # 导出的草图 PNG，运行时生成
├── docs/
│   └── images/                      # README 截图
├── outputs/
│   └── generated/                   # AI 生成图片，运行时生成
├── test_env.py                      # .env 读取诊断
└── test_siliconflow_auth.py         # SiliconFlow API 认证诊断
```

## 安装依赖

推荐使用项目内的虚拟环境。

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果没有创建虚拟环境，可以先执行：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## SiliconFlow 配置

在项目根目录 `gesture_garden/.env` 中配置以下变量：

```env
SILICONFLOW_API_KEY=你的_API_Key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_IMAGE_MODEL=Tongyi-MAI/Z-Image-Turbo
```

注意：

- 不要把 API Key 写死进代码。
- 不要把 `.env` 提交到 GitHub。
- 如果 API Key 缺失或错误，主程序不会直接崩溃，会进入 error 状态并显示错误提示。

## 运行程序

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe main.py
```

运行后会打开 Pygame 窗口。摄像头画面显示在右侧，画布显示在左侧。把手放到摄像头前，移动食指可以控制光标；如果手势不可用，可以使用鼠标备用模式。

## 操作指南

| 按键 / 操作 | 功能 |
| --- | --- |
| `G` | 自动保存草图并生成 AI 图片 |
| `R` | 从结果页或错误页返回绘画模式 |
| `C` | 清空画布 |
| `S` | 保存当前草图 |
| `M` | 切换手势 / 鼠标输入模式 |
| `1` | 切换主题为 `garden` |
| `2` | 切换主题为 `pet` |
| `3` | 切换主题为 `room` |
| `4` | 切换主题为 `sky_island` |
| `5` | 切换主题为 `character` |
| 输入英文关键词 | 编辑补充关键词 |
| `Enter` | 确认关键词；再次按下可继续编辑 |
| `Backspace` | 删除关键词 |
| `TAB` | 切换下一个画笔颜色 |
| `[` / `-` | 减小画笔粗细 |
| `]` / `=` | 增大画笔粗细 |
| `Q` / `ESC` | 退出程序 |

推荐使用方式：

```text
1. 画草图
2. 按 1-5 选择主题
3. 输入英文关键词
4. 按 Enter 确认
5. 按 G 生成图片
6. 按 R 返回绘画
```

关键词示例：

```text
flowers tree small house
dog and cat
bed window moon plant
pink hair magical staff
```

## 主题说明

| 主题 | 适合生成 |
| --- | --- |
| `garden` | 花园、植物、小屋、梦幻场景 |
| `pet` | 可爱宠物、幻想小生物 |
| `room` | 魔法房间、室内场景 |
| `sky_island` | 天空岛、云层、小房子、幻想天空 |
| `character` | 二次元角色、全身人物、魔法服装 |

## API 诊断

检查 `.env` 是否读取成功：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe test_env.py
```

独立测试 SiliconFlow 图片生成接口：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe test_siliconflow_auth.py
```

独立测试 Z-Image-Turbo 生成器：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe -m generation.test_zimage
```

常见判断：

| 现象 | 可能原因 |
| --- | --- |
| `ModuleNotFoundError: No module named 'dotenv'` | 没安装 `python-dotenv` |
| `key exists: False` | `.env` 没读到，或变量名不是 `SILICONFLOW_API_KEY` |
| `401` | API Key 无效或格式错误 |
| `403` | 权限、额度或模型可用性问题 |
| `404` | base_url 或接口地址错误 |
| `429` | 请求过快，被限流 |
| `503` | 服务繁忙或暂时不可用 |

## 输出文件

按 `S` 或 `G` 后，草图会保存到：

```text
gesture_garden/data/sketches/
```

按 `G` 并生成成功后，AI 图片会保存到：

```text
gesture_garden/outputs/generated/
```

这些文件属于运行产物，默认不提交到 Git。

## 开发测试

语法检查：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe -m py_compile main.py ai\prompt_builder.py generation\siliconflow_generator.py
```

测试 Prompt Builder：

```powershell
cd D:\Tooty\Documents\CodeX\DigitalGarden\gesture_garden
.\.venv\Scripts\python.exe ai\prompt_builder.py
```

## 当前状态

当前项目已经完成最小可演示闭环：

```text
手势 / 鼠标绘画 → 保存草图 → 主题和关键词生成 Prompt → SiliconFlow 生成图片 → 展示结果
```

后续可以继续提升：

- 接入草图识别，让生成内容真正参考用户画的形状。
- 增加图片比例、负面 Prompt、风格强度等生成参数。
- 优化生成结果页，支持重新生成、保存记录和查看历史图片。
- 增加更稳定的网络重试和错误分类。
