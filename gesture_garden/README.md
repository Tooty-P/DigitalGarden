# Blooming Spell：手势生成的二次元数字花园

这是一个 Python 作品集项目的基础骨架。

当前版本只包含一个最小的 Pygame 窗口，用来确认项目可以正常运行、打开窗口并关闭窗口。暂时不会加入摄像头、手势识别、花朵、粒子等复杂功能。

## 项目结构

```text
gesture_garden/
├── main.py
├── hand_tracker.py
├── garden_scene.py
├── objects.py
├── utils.py
├── requirements.txt
├── README.md
├── screenshots/
└── assets/
```

## 安装方法

建议先创建并激活虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 运行方法

进入项目目录后运行：

```bash
python main.py
```

程序会打开一个 960x540 的 Pygame 窗口。

## 操作方式

- 按 `Q` 退出
- 按 `ESC` 退出
- 点击窗口关闭按钮退出
