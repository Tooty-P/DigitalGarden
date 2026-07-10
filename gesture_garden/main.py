"""Magic Canvas AI 主程序。

当前阶段目标：
摄像头识别食指位置 -> 在空气中绘画/擦除 -> 保存绘画草图 -> AI 理解 -> 图片生成 -> 展示结果。
真实 AI API 仍然是可替换接口，没有配置 API 时会自动使用模拟结果。
"""

import threading

import cv2
import pygame

from ai.prompt_builder import build_prompt
from drawing.canvas import Canvas
from generation.siliconflow_generator import SiliconFlowImageGenerator
from hand_tracker import HandTracker


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Magic Canvas AI - 手势动漫 AI 绘画画布"
FPS = 60
SAVE_MESSAGE_DURATION = 120
DEFAULT_GENERATION_THEME = "garden"
THEME_KEYS = {
    pygame.K_1: "garden",
    pygame.K_2: "pet",
    pygame.K_3: "room",
    pygame.K_4: "sky_island",
    pygame.K_5: "character",
}
THEME_LABELS = [
    ("1", "garden"),
    ("2", "pet"),
    ("3", "room"),
    ("4", "sky_island"),
    ("5", "character"),
]

DEFAULT_ERASER_RADIUS = 18
MIN_ERASER_RADIUS = 6
MAX_ERASER_RADIUS = 60
MIN_ZOOM = 0.5
MAX_ZOOM = 2.0
ZOOM_STEP = 0.1

CANVAS_RECT = pygame.Rect(32, 104, 880, 584)
SIDE_PANEL_RECT = pygame.Rect(936, 24, 312, 664)
TOP_BAR_RECT = pygame.Rect(32, 24, 880, 58)


class MagicCanvasBackground:
    """绘制专业绘画软件风格的低干扰工作台。"""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def draw(self, screen):
        """绘制深灰蓝工作区、画布面板和辅助网格。"""
        top_color = (28, 34, 45)
        bottom_color = (18, 22, 31)
        for y in range(self.height):
            t = y / self.height
            color = (
                int(top_color[0] * (1 - t) + bottom_color[0] * t),
                int(top_color[1] * (1 - t) + bottom_color[1] * t),
                int(top_color[2] * (1 - t) + bottom_color[2] * t),
            )
            pygame.draw.line(screen, color, (0, y), (self.width, y))

        self._draw_panel(screen, TOP_BAR_RECT, (35, 42, 55), (69, 82, 103))
        self._draw_canvas_panel(screen)
        self._draw_panel(screen, SIDE_PANEL_RECT, (31, 38, 51), (69, 82, 103))

    def _draw_panel(self, screen, rect, fill, border):
        """绘制统一风格的界面面板。"""
        shadow = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 70), shadow.get_rect(), border_radius=12)
        screen.blit(shadow, (rect.x + 4, rect.y + 5))
        pygame.draw.rect(screen, fill, rect, border_radius=12)
        pygame.draw.rect(screen, border, rect, 1, border_radius=12)

    def _draw_canvas_panel(self, screen):
        """绘制中央绘画区域底板。"""
        shadow_rect = CANVAS_RECT.move(5, 7)
        shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 95), shadow.get_rect(), border_radius=10)
        screen.blit(shadow, shadow_rect.topleft)

        pygame.draw.rect(screen, (16, 20, 29), CANVAS_RECT, border_radius=10)
        pygame.draw.rect(screen, (55, 68, 88), CANVAS_RECT, 1, border_radius=10)

        grid = pygame.Surface((CANVAS_RECT.width, CANVAS_RECT.height), pygame.SRCALPHA)
        for x in range(0, CANVAS_RECT.width, 32):
            pygame.draw.line(grid, (255, 255, 255, 10), (x, 0), (x, CANVAS_RECT.height))
        for y in range(0, CANVAS_RECT.height, 32):
            pygame.draw.line(grid, (255, 255, 255, 10), (0, y), (CANVAS_RECT.width, y))
        screen.blit(grid, CANVAS_RECT.topleft)


def create_font(size):
    """创建支持中文的字体。"""
    font_name = pygame.font.match_font("microsoftyahei")
    if font_name is None:
        font_name = pygame.font.match_font("simhei")
    return pygame.font.Font(font_name, size) if font_name else pygame.font.Font(None, size)


def get_canvas_view(canvas, zoom):
    """计算逻辑画布缩放后在屏幕上的显示区域和比例。"""
    base_scale = min(CANVAS_RECT.width / canvas.width, CANVAS_RECT.height / canvas.height)
    scale = base_scale * zoom
    view_width = int(canvas.width * scale)
    view_height = int(canvas.height * scale)
    x = CANVAS_RECT.centerx - view_width // 2
    y = CANVAS_RECT.centery - view_height // 2
    return pygame.Rect(x, y, view_width, view_height), scale


def screen_to_canvas(point, canvas, zoom):
    """把屏幕坐标转换成逻辑画布坐标。"""
    view_rect, scale = get_canvas_view(canvas, zoom)
    if point is None or not view_rect.collidepoint(point):
        return None

    x = int((point[0] - view_rect.x) / scale)
    y = int((point[1] - view_rect.y) / scale)
    return (max(0, min(canvas.width - 1, x)), max(0, min(canvas.height - 1, y)))


def canvas_to_screen(point, canvas, zoom):
    """把逻辑画布坐标转换成屏幕坐标。"""
    if point is None:
        return None
    view_rect, scale = get_canvas_view(canvas, zoom)
    return (int(view_rect.x + point[0] * scale), int(view_rect.y + point[1] * scale))


def draw_canvas_view(screen, canvas, zoom):
    """把逻辑画布绘制到缩放后的屏幕区域。"""
    view_rect, _ = get_canvas_view(canvas, zoom)
    canvas_surface = pygame.Surface((canvas.width, canvas.height), pygame.SRCALPHA)
    canvas.draw(canvas_surface)
    scaled_surface = pygame.transform.smoothscale(canvas_surface, view_rect.size)

    # 限制绘制区域，避免放大后内容覆盖工具面板。
    old_clip = screen.get_clip()
    screen.set_clip(CANVAS_RECT)
    screen.blit(scaled_surface, view_rect.topleft)
    screen.set_clip(old_clip)

    pygame.draw.rect(screen, (92, 108, 132), view_rect, 1, border_radius=6)
    label_font = pygame.font.Font(None, 18)
    label = label_font.render(f"Canvas {int(zoom * 100)}%", True, (136, 154, 178))
    screen.blit(label, (CANVAS_RECT.x + 14, CANVAS_RECT.y + 10))


def draw_camera_preview(screen, frame, font):
    """在右侧面板绘制摄像头预览。"""
    title = font.render("摄像头", True, (225, 235, 247))
    screen.blit(title, (SIDE_PANEL_RECT.x + 16, SIDE_PANEL_RECT.y + 14))

    preview_rect = pygame.Rect(SIDE_PANEL_RECT.x + 18, SIDE_PANEL_RECT.y + 52, 276, 164)
    pygame.draw.rect(screen, (13, 17, 25), preview_rect, border_radius=8)
    pygame.draw.rect(screen, (76, 91, 116), preview_rect, 1, border_radius=8)

    if frame is None:
        text = font.render("未检测到摄像头", True, (190, 203, 219))
        screen.blit(text, text.get_rect(center=preview_rect.center))
        return

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    preview_surface = pygame.image.frombuffer(
        rgb_frame.tobytes(),
        (rgb_frame.shape[1], rgb_frame.shape[0]),
        "RGB",
    )
    preview_surface = pygame.transform.smoothscale(preview_surface, (264, 148))
    screen.blit(preview_surface, (preview_rect.x + 6, preview_rect.y + 8))


def draw_pointer(screen, point, color, tool_mode, eraser_radius, scale):
    """按当前工具绘制光标提示。"""
    if point is None:
        return

    x, y = point
    pointer_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

    if tool_mode == "erase":
        screen_radius = max(4, int(eraser_radius * scale))
        pygame.draw.circle(pointer_layer, (255, 114, 142, 35), (x, y), screen_radius + 8)
        pygame.draw.circle(pointer_layer, (255, 160, 180, 210), (x, y), screen_radius, 2)
        pygame.draw.circle(pointer_layer, (255, 255, 255, 230), (x, y), 3)
    elif tool_mode == "draw":
        pygame.draw.circle(pointer_layer, color, (x, y), 6)
        pygame.draw.circle(pointer_layer, (245, 252, 255, 180), (x, y), 2)
    else:
        pygame.draw.circle(pointer_layer, (255, 238, 150, 190), (x, y), 4)

    screen.blit(pointer_layer, (0, 0))


def get_color_swatch_rects(canvas):
    """返回右侧颜色面板中每个色块的位置。"""
    rects = []
    start_x = SIDE_PANEL_RECT.x + 20
    start_y = SIDE_PANEL_RECT.y + 512
    size = 28
    gap = 10
    columns = 6
    for index in range(len(canvas.palette)):
        col = index % columns
        row = index // columns
        rects.append(pygame.Rect(start_x + col * (size + gap), start_y + row * (size + gap), size, size))
    return rects


def draw_ui(
    screen,
    font,
    small_font,
    status_text,
    canvas,
    input_mode,
    tool_mode,
    eraser_radius,
    zoom,
    save_message_timer,
    generation_state,
    current_theme,
    extra_keywords_text,
    keyword_editing,
):
    """绘制工具栏、状态栏和保存提示。"""
    tool_name = {"draw": "画笔", "erase": "橡皮擦", "cursor": "光标"}.get(tool_mode, "光标")
    mode_text = "手势" if input_mode == "Gesture" else "鼠标"

    title = font.render("Magic Canvas AI", True, (235, 242, 250))
    screen.blit(title, (TOP_BAR_RECT.x + 18, TOP_BAR_RECT.y + 16))

    status = small_font.render(f"{mode_text} | {tool_name} | {status_text}", True, (182, 198, 219))
    screen.blit(status, (TOP_BAR_RECT.x + 220, TOP_BAR_RECT.y + 10))

    shortcuts = small_font.render("1-5主题 | Enter确认/编辑关键词 | G生成 | C清空 | S保存 | R返回 | Q退出", True, (151, 169, 190))
    screen.blit(shortcuts, (TOP_BAR_RECT.x + 220, TOP_BAR_RECT.y + 34))

    y = SIDE_PANEL_RECT.y + 240
    draw_section_title(screen, font, "工具", SIDE_PANEL_RECT.x + 16, y)
    y += 34
    draw_key_value(screen, small_font, "输入", mode_text, SIDE_PANEL_RECT.x + 16, y)
    y += 25
    draw_key_value(screen, small_font, "当前", tool_name, SIDE_PANEL_RECT.x + 16, y)
    y += 25
    draw_key_value(screen, small_font, "笔刷", f"{canvas.brush_width}px", SIDE_PANEL_RECT.x + 16, y)
    y += 25
    draw_key_value(screen, small_font, "橡皮", f"{eraser_radius}px", SIDE_PANEL_RECT.x + 16, y)
    y += 25
    draw_key_value(screen, small_font, "缩放", f"{int(zoom * 100)}%", SIDE_PANEL_RECT.x + 16, y)
    y += 25
    draw_key_value(screen, small_font, "颜色", canvas.color_names[canvas.color_index], SIDE_PANEL_RECT.x + 16, y)

    draw_theme_selector(screen, small_font, current_theme)

    keyword_y = SIDE_PANEL_RECT.y + 414
    draw_section_title(screen, font, "关键词", SIDE_PANEL_RECT.x + 16, keyword_y)
    keyword_label = extra_keywords_text if extra_keywords_text else "(empty)"
    if keyword_editing:
        keyword_label = f"{keyword_label}|"
    draw_wrapped_value(screen, small_font, "Keywords", keyword_label, SIDE_PANEL_RECT.x + 16, keyword_y + 30, 270)

    draw_section_title(screen, font, "颜色", SIDE_PANEL_RECT.x + 18, SIDE_PANEL_RECT.y + 482)
    for index, rect in enumerate(get_color_swatch_rects(canvas)):
        pygame.draw.rect(screen, canvas.palette[index], rect, border_radius=6)
        border_color = (255, 232, 143) if index == canvas.color_index else (88, 103, 128)
        border_width = 3 if index == canvas.color_index else 1
        pygame.draw.rect(screen, border_color, rect, border_width, border_radius=6)

    if save_message_timer > 0:
        alpha = min(230, save_message_timer * 4)
        message = font.render("草图已保存", True, (255, 232, 143))
        rect = message.get_rect(center=(CANVAS_RECT.centerx, 65))
        bubble = pygame.Surface((rect.width + 40, rect.height + 20), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (20, 26, 36, alpha), bubble.get_rect(), border_radius=14)
        pygame.draw.rect(bubble, (255, 232, 143, alpha), bubble.get_rect(), 1, border_radius=14)
        screen.blit(bubble, (rect.x - 20, rect.y - 10))
        screen.blit(message, rect)

    if generation_state["status"] == "generating":
        draw_loading(screen, font)
    elif generation_state["status"] == "error":
        draw_error_message(screen, font, generation_state["message"])


def draw_section_title(screen, font, text, x, y):
    """绘制侧边栏小标题。"""
    label = font.render(text, True, (230, 238, 248))
    screen.blit(label, (x, y))


def draw_key_value(screen, font, key, value, x, y):
    """绘制侧边栏键值信息。"""
    key_text = font.render(key, True, (143, 160, 181))
    value_text = font.render(value, True, (224, 234, 247))
    screen.blit(key_text, (x, y))
    screen.blit(value_text, (x + 62, y))


def draw_theme_selector(screen, font, current_theme):
    """在右侧空白区域显示 1-5 主题快捷键提示。"""
    panel_rect = pygame.Rect(SIDE_PANEL_RECT.x + 150, SIDE_PANEL_RECT.y + 314, 142, 158)
    pygame.draw.rect(screen, (24, 30, 42), panel_rect, border_radius=8)
    pygame.draw.rect(screen, (76, 91, 116), panel_rect, 1, border_radius=8)

    title = font.render("主题 1-5", True, (230, 238, 248))
    screen.blit(title, (panel_rect.x + 10, panel_rect.y + 8))

    row_y = panel_rect.y + 34
    for key, theme in THEME_LABELS:
        active = theme == current_theme
        row_rect = pygame.Rect(panel_rect.x + 8, row_y, panel_rect.width - 16, 20)

        if active:
            pygame.draw.rect(screen, (255, 232, 143), row_rect, border_radius=5)
            text_color = (25, 30, 40)
        else:
            text_color = (190, 206, 226)

        label = font.render(f"{key}  {theme}", True, text_color)
        screen.blit(label, (row_rect.x + 8, row_rect.y + 2))
        row_y += 23


def draw_wrapped_value(screen, font, key, value, x, y, max_width):
    """绘制可能较长的键值信息，关键词过长时截断显示。"""
    key_text = font.render(key, True, (143, 160, 181))
    display_value = str(value)
    while font.size(display_value)[0] > max_width and len(display_value) > 3:
        display_value = display_value[:-4] + "..."
    value_text = font.render(display_value, True, (224, 234, 247))
    screen.blit(key_text, (x, y))
    screen.blit(value_text, (x, y + 20))


def draw_keyword_editor_dialog(screen, font, small_font, extra_keywords_text):
    """绘制关键词编辑对话框，让用户能实时看到正在输入的内容。"""
    dialog_rect = pygame.Rect(CANVAS_RECT.x + 54, CANVAS_RECT.bottom - 126, CANVAS_RECT.width - 108, 96)
    shadow_rect = dialog_rect.move(4, 5)

    shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 95), shadow.get_rect(), border_radius=12)
    screen.blit(shadow, shadow_rect.topleft)

    pygame.draw.rect(screen, (28, 35, 48), dialog_rect, border_radius=12)
    pygame.draw.rect(screen, (255, 232, 143), dialog_rect, 2, border_radius=12)

    title = font.render("关键词编辑", True, (255, 232, 143))
    screen.blit(title, (dialog_rect.x + 18, dialog_rect.y + 12))

    hint = small_font.render("输入英文关键词，Backspace 删除，Enter 确认", True, (170, 188, 210))
    screen.blit(hint, (dialog_rect.x + 124, dialog_rect.y + 16))

    input_rect = pygame.Rect(dialog_rect.x + 18, dialog_rect.y + 48, dialog_rect.width - 36, 30)
    pygame.draw.rect(screen, (13, 17, 25), input_rect, border_radius=7)
    pygame.draw.rect(screen, (84, 101, 128), input_rect, 1, border_radius=7)

    display_text = extra_keywords_text if extra_keywords_text else "flowers tree small house"
    text_color = (235, 242, 250) if extra_keywords_text else (112, 130, 154)
    caret = "|" if (pygame.time.get_ticks() // 450) % 2 == 0 else ""
    display_text = fit_text_to_width(f"{display_text}{caret}", small_font, input_rect.width - 20)
    text = small_font.render(display_text, True, text_color)
    screen.blit(text, (input_rect.x + 10, input_rect.y + 7))


def fit_text_to_width(text, font, max_width):
    """从左侧截断过长文本，确保输入框里始终能看到最新输入。"""
    display_text = str(text)
    while font.size(display_text)[0] > max_width and len(display_text) > 4:
        display_text = "..." + display_text[4:]
    return display_text


def draw_loading(screen, font):
    """绘制 AI 生成中的提示。"""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 10, 18, 120))
    screen.blit(overlay, (0, 0))

    dots = "." * ((pygame.time.get_ticks() // 350) % 4)
    text = font.render(f"Generating... 正在保存草图、思考并生成图片{dots}", True, (255, 232, 143))
    rect = text.get_rect(center=(CANVAS_RECT.centerx, CANVAS_RECT.centery))
    panel = pygame.Surface((rect.width + 56, rect.height + 30), pygame.SRCALPHA)
    pygame.draw.rect(panel, (25, 31, 42, 235), panel.get_rect(), border_radius=14)
    pygame.draw.rect(panel, (95, 111, 137, 180), panel.get_rect(), 1, border_radius=14)
    screen.blit(panel, (rect.x - 28, rect.y - 15))
    screen.blit(text, rect)


def draw_error_message(screen, font, message):
    """绘制 AI 流程失败提示。"""
    text = font.render(f"生成失败：{message}", True, (255, 180, 196))
    rect = text.get_rect(center=(CANVAS_RECT.centerx, WINDOW_HEIGHT - 36))
    panel = pygame.Surface((min(rect.width + 44, 650), rect.height + 22), pygame.SRCALPHA)
    pygame.draw.rect(panel, (58, 24, 35, 225), panel.get_rect(), border_radius=12)
    screen.blit(panel, (max(CANVAS_RECT.x, rect.x - 22), rect.y - 11))
    screen.blit(text, rect)


def draw_generated_result(screen, font, small_font, generated_surface, prompt_text):
    """在右侧展示生成结果。"""
    y = SIDE_PANEL_RECT.y + 612
    title = font.render("AI 结果", True, (230, 238, 248))
    screen.blit(title, (SIDE_PANEL_RECT.x + 16, y))

    result_rect = pygame.Rect(SIDE_PANEL_RECT.x + 18, y + 28, 276, 50)
    pygame.draw.rect(screen, (13, 17, 25), result_rect, border_radius=8)
    pygame.draw.rect(screen, (76, 91, 116), result_rect, 1, border_radius=8)

    if generated_surface is None:
        hint = small_font.render("按 G", True, (143, 160, 181))
        screen.blit(hint, hint.get_rect(center=result_rect.center))
        return

    # 按原比例缩放右下角预览，避免生成图被拉伸变形。
    preview_rect = result_rect.inflate(-12, -10)
    image_rect = generated_surface.get_rect()
    scale = min(preview_rect.width / image_rect.width, preview_rect.height / image_rect.height)
    preview_size = (max(1, int(image_rect.width * scale)), max(1, int(image_rect.height * scale)))
    preview = pygame.transform.smoothscale(generated_surface, preview_size)
    screen.blit(preview, preview.get_rect(center=preview_rect.center))


def draw_result_screen(screen, font, small_font, generated_surface, generation_state):
    """绘制结果展示模式，把生成图缩放后居中显示。"""
    screen.fill((16, 20, 29))

    title = font.render("AI 生成结果", True, (235, 242, 250))
    screen.blit(title, (36, 28))

    hint = small_font.render("R 返回绘画 | Q / ESC 退出", True, (170, 188, 210))
    screen.blit(hint, (36, 58))

    theme_text = small_font.render(f"Theme: {generation_state.get('theme', '')}", True, (190, 206, 226))
    screen.blit(theme_text, (360, 30))
    keywords_text = small_font.render(f"Keywords: {generation_state.get('keywords', '') or '(empty)'}", True, (190, 206, 226))
    screen.blit(keywords_text, (360, 56))

    image_area = pygame.Rect(48, 96, WINDOW_WIDTH - 96, WINDOW_HEIGHT - 160)
    pygame.draw.rect(screen, (25, 31, 42), image_area, border_radius=12)
    pygame.draw.rect(screen, (76, 91, 116), image_area, 1, border_radius=12)

    if generated_surface is None:
        text = font.render("还没有可显示的生成图片", True, (210, 222, 238))
        screen.blit(text, text.get_rect(center=image_area.center))
        return

    source_rect = generated_surface.get_rect()
    scale = min(image_area.width / source_rect.width, image_area.height / source_rect.height)
    display_size = (
        max(1, int(source_rect.width * scale)),
        max(1, int(source_rect.height * scale)),
    )
    preview = pygame.transform.smoothscale(generated_surface, display_size)
    preview_rect = preview.get_rect(center=image_area.center)
    screen.blit(preview, preview_rect)

    path_text = small_font.render(generation_state.get("generated_path", ""), True, (136, 154, 178))
    screen.blit(path_text, (48, WINDOW_HEIGHT - 42))


def draw_generating_screen(screen, font, small_font, generation_state):
    """绘制生成中模式，提示用户程序正在保存草图、思考并请求图片。"""
    screen.fill((16, 20, 29))

    dots = "." * ((pygame.time.get_ticks() // 350) % 4)
    title = font.render(f"Generating{dots}", True, (255, 232, 143))
    screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30)))

    message = generation_state.get("message") or "保存草图，正在思考并生成图片"
    detail = small_font.render(message, True, (190, 206, 226))
    screen.blit(detail, detail.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 8)))

    hint = small_font.render("请稍等，生成完成后会自动显示结果 | Q / ESC 退出", True, (136, 154, 178))
    screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 42)))


def draw_error_screen(screen, font, small_font, generation_state):
    """绘制错误模式，显示失败原因并允许返回绘画。"""
    screen.fill((29, 18, 24))

    title = font.render("生成失败", True, (255, 180, 196))
    screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 56)))

    message = generation_state.get("message") or "未知错误"
    lines = wrap_text(message, small_font, 820)
    y = WINDOW_HEIGHT // 2 - 16
    for line in lines[:5]:
        text = small_font.render(line, True, (238, 206, 216))
        screen.blit(text, text.get_rect(center=(WINDOW_WIDTH // 2, y)))
        y += 24

    hint = small_font.render("按 R 返回绘画模式 | Q / ESC 退出", True, (210, 172, 186))
    screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, y + 30)))


def wrap_text(text, font, max_width):
    """按宽度简单折行，避免错误信息超出窗口。"""
    raw_text = str(text)
    if " " not in raw_text:
        lines = []
        current = ""
        for char in raw_text:
            candidate = current + char
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or [""]

    words = raw_text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def translate_status(status_text):
    """把手势追踪状态转换成中文。"""
    status_map = {
        "Hand tracking ready": "手势识别已就绪",
        "Camera not found": "未检测到摄像头",
        "Hand tracking model not ready": "手势模型未就绪",
        "Missing assets/hand_landmarker.task": "缺少手势识别模型文件",
        "MediaPipe Tasks import failed": "MediaPipe Tasks 导入失败",
        "Show your hand to move cursor": "请把手放到摄像头前移动光标",
        "Move cursor; pinch to use tool": "移动光标中：捏合执行当前工具",
        "Pinch detected: active": "捏合已检测：正在执行当前工具",
        "Pinch held: active": "短暂保持当前工具",
    }
    return status_map.get(status_text, status_text)


def clamp(value, minimum, maximum):
    """把数值限制在指定范围内。"""
    return max(minimum, min(maximum, value))


def handle_shortcuts(event, canvas, active_tool, eraser_radius, zoom):
    """处理画布相关快捷键，并返回更新后的橡皮和缩放值。"""
    pressed_char = event.unicode.lower() if event.unicode else ""
    mods = pygame.key.get_mods()
    ctrl_pressed = bool(mods & pygame.KMOD_CTRL)

    if ctrl_pressed and event.key == pygame.K_z:
        if canvas.undo():
            print("已撤销上一步。")
        return eraser_radius, zoom

    if ctrl_pressed and event.key in (pygame.K_EQUALS, pygame.K_PLUS):
        zoom = round(clamp(zoom + ZOOM_STEP, MIN_ZOOM, MAX_ZOOM), 2)
        return eraser_radius, zoom

    if ctrl_pressed and event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
        zoom = round(clamp(zoom - ZOOM_STEP, MIN_ZOOM, MAX_ZOOM), 2)
        return eraser_radius, zoom

    if ctrl_pressed and event.key == pygame.K_0:
        zoom = 1.0
        return eraser_radius, zoom

    if event.key == pygame.K_c or pressed_char == "c":
        canvas.clear()
        print("画布已清空。")
    elif event.key == pygame.K_TAB:
        canvas.next_color()
    elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
        if active_tool == "erase":
            eraser_radius = int(clamp(eraser_radius - 2, MIN_ERASER_RADIUS, MAX_ERASER_RADIUS))
        else:
            canvas.change_brush_width(-1)
    elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS):
        if active_tool == "erase":
            eraser_radius = int(clamp(eraser_radius + 2, MIN_ERASER_RADIUS, MAX_ERASER_RADIUS))
        else:
            canvas.change_brush_width(1)
    return eraser_radius, zoom


def run_generation_flow(image_generator, sketch_path, generation_state, theme, extra_keywords_text):
    """后台执行：草图导出记录 -> 主题和关键词 Prompt -> SiliconFlow 图片生成。"""
    try:
        # 当前先不做复杂草图识别，用主题和用户关键词提高相关性。
        prompt = build_prompt(theme=theme, extra_keywords=extra_keywords_text)
        print(f"当前主题：{theme}")
        print(f"用户关键词：{extra_keywords_text or '(empty)'}")
        print(f"最终 Prompt：{prompt}")
        generated_path = image_generator.generate(prompt)
        if generated_path is None:
            error_message = image_generator.last_error or "返回图片路径为空，请检查 SiliconFlow 返回内容。"
            raise RuntimeError(error_message)

        generation_state["status"] = "done"
        generation_state["sketch_path"] = str(sketch_path)
        generation_state["generated_path"] = str(generated_path)
        generation_state["prompt"] = prompt
        generation_state["theme"] = theme
        generation_state["keywords"] = extra_keywords_text
        generation_state["message"] = "生成完成"
        print(f"草图已导出：{sketch_path}")
        print(f"生成图片：{generated_path}")
    except Exception as exc:
        generation_state["status"] = "error"
        generation_state["message"] = str(exc)
        print(f"AI 生成失败：{exc}")


def main():
    """程序入口：打开窗口、追踪食指、绘制、擦除并保存草图。"""
    pygame.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = create_font(19)
    small_font = create_font(15)

    background = MagicCanvasBackground(WINDOW_WIDTH, WINDOW_HEIGHT)
    canvas = Canvas(WINDOW_WIDTH, WINDOW_HEIGHT)
    hand_tracker = HandTracker(width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    image_generator = SiliconFlowImageGenerator()

    running = True
    app_mode = "drawing"
    was_drawing = False
    was_erasing = False
    should_save_sketch = False
    save_message_timer = 0
    force_mouse_mode = False
    active_tool = "draw"
    eraser_radius = DEFAULT_ERASER_RADIUS
    zoom = 1.0
    current_theme = DEFAULT_GENERATION_THEME
    extra_keywords_text = ""
    keyword_editing = True
    generation_state = {
        "status": "idle",
        "message": "",
        "sketch_path": "",
        "generated_path": "",
        "prompt": "",
        "theme": current_theme,
        "keywords": extra_keywords_text,
    }
    generated_surface = None
    loaded_generated_path = ""

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if app_mode == "drawing" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(get_color_swatch_rects(canvas)):
                    if rect.collidepoint(event.pos):
                        canvas.set_color_by_index(index)
                        break

            if event.type == pygame.KEYDOWN:
                pressed_char = event.unicode.lower() if event.unicode else ""

                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q or pressed_char == "q":
                    running = False
                elif app_mode in ("result", "error") and (event.key == pygame.K_r or pressed_char == "r"):
                    app_mode = "drawing"
                    if generation_state["status"] == "error":
                        generation_state["status"] = "idle"
                elif app_mode == "drawing" and event.key in THEME_KEYS:
                    current_theme = THEME_KEYS[event.key]
                    generation_state["theme"] = current_theme
                    print(f"当前主题已切换为：{current_theme}")
                elif app_mode == "drawing" and event.key == pygame.K_RETURN:
                    keyword_editing = not keyword_editing
                    state_text = "编辑中" if keyword_editing else "已确认"
                    print(f"关键词{state_text}：{extra_keywords_text or '(empty)'}")
                elif app_mode == "drawing" and keyword_editing and event.key == pygame.K_BACKSPACE:
                    extra_keywords_text = extra_keywords_text[:-1]
                    generation_state["keywords"] = extra_keywords_text
                elif app_mode == "drawing" and keyword_editing and event.unicode and event.unicode.isprintable():
                    # 简单文本输入：启动后默认输入关键词，按 Enter 确认后快捷键生效。
                    if len(extra_keywords_text) < 80:
                        extra_keywords_text += event.unicode
                        generation_state["keywords"] = extra_keywords_text
                elif app_mode == "drawing" and (event.key == pygame.K_s or pressed_char == "s"):
                    should_save_sketch = True
                elif event.key == pygame.K_g or pressed_char == "g":
                    if app_mode == "drawing" and generation_state["status"] != "generating":
                        canvas.end_stroke()
                        was_drawing = False
                        was_erasing = False
                        sketch_path = canvas.save_sketch(screen)
                        app_mode = "generating"
                        generation_state.update(
                            {
                                "status": "generating",
                                "message": "草图已保存，正在思考并生成图片",
                                "sketch_path": str(sketch_path),
                                "generated_path": "",
                                "prompt": "",
                                "theme": current_theme,
                                "keywords": extra_keywords_text,
                            }
                        )
                        generated_surface = None
                        loaded_generated_path = ""
                        worker = threading.Thread(
                            target=run_generation_flow,
                            args=(image_generator, sketch_path, generation_state, current_theme, extra_keywords_text),
                            daemon=True,
                        )
                        worker.start()
                elif app_mode == "drawing" and (event.key == pygame.K_m or pressed_char == "m"):
                    force_mouse_mode = not force_mouse_mode
                    canvas.end_stroke()
                    was_drawing = False
                    was_erasing = False
                elif app_mode == "drawing" and (event.key == pygame.K_e or pressed_char == "e"):
                    active_tool = "erase" if active_tool == "draw" else "draw"
                    canvas.end_stroke()
                    was_drawing = False
                    was_erasing = False
                elif app_mode == "drawing":
                    eraser_radius, zoom = handle_shortcuts(event, canvas, active_tool, eraser_radius, zoom)

        if generation_state["status"] == "done" and generation_state["generated_path"] != loaded_generated_path:
            try:
                generated_surface = pygame.image.load(generation_state["generated_path"]).convert()
                loaded_generated_path = generation_state["generated_path"]
                app_mode = "result"
                save_message_timer = SAVE_MESSAGE_DURATION
            except Exception as exc:
                generation_state["status"] = "error"
                generation_state["message"] = f"生成图加载失败：{exc}"
                app_mode = "error"

        if generation_state["status"] == "error":
            app_mode = "error"

        if app_mode == "generating":
            draw_generating_screen(screen, font, small_font, generation_state)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        if app_mode == "result":
            draw_result_screen(screen, font, small_font, generated_surface, generation_state)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        if app_mode == "error":
            draw_error_screen(screen, font, small_font, generation_state)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        hand_data = hand_tracker.update()
        frame = hand_data["frame"]
        hand_tracking_ready = hand_data.get("hand_tracking_ready", False)
        use_mouse = force_mouse_mode or not hand_tracking_ready

        if use_mouse:
            screen_pos = pygame.mouse.get_pos()
            canvas_pos = screen_to_canvas(screen_pos, canvas, zoom)
            mouse_buttons = pygame.mouse.get_pressed()
            left_pressed = mouse_buttons[0]
            right_pressed = mouse_buttons[2]
            is_drawing = canvas_pos is not None and left_pressed and active_tool == "draw"
            is_erasing = canvas_pos is not None and (right_pressed or (left_pressed and active_tool == "erase"))
            tool_mode = "erase" if is_erasing else active_tool
            input_mode = "Mouse"
        else:
            screen_pos = hand_data["index_pos"]
            canvas_pos = screen_to_canvas(screen_pos, canvas, zoom)
            tool_active = hand_data["is_drawing"] and canvas_pos is not None
            is_drawing = tool_active and active_tool == "draw"
            is_erasing = tool_active and active_tool == "erase"
            tool_mode = active_tool
            input_mode = "Gesture"

        # 当前工具优先级：擦除 > 绘画 > 移动光标。
        if is_erasing and canvas_pos is not None:
            if was_drawing:
                canvas.end_stroke()
                was_drawing = False
            if not was_erasing:
                canvas.begin_erase_action()
            canvas.erase_at(canvas_pos, eraser_radius)
            was_erasing = True
        elif is_drawing and canvas_pos is not None:
            if was_erasing:
                was_erasing = False
            if not was_drawing:
                canvas.start_stroke(canvas_pos)
            else:
                canvas.add_point(canvas_pos)
            was_drawing = True
        else:
            if was_drawing:
                canvas.end_stroke()
            was_drawing = False
            was_erasing = False

        background.draw(screen)
        draw_canvas_view(screen, canvas, zoom)
        pointer_pos = canvas_to_screen(canvas_pos, canvas, zoom) if canvas_pos is not None else screen_pos
        _, view_scale = get_canvas_view(canvas, zoom)
        draw_pointer(screen, pointer_pos, canvas.brush_color, tool_mode, eraser_radius, view_scale)
        draw_camera_preview(screen, frame, font)
        draw_generated_result(screen, font, small_font, generated_surface, generation_state["prompt"])

        if use_mouse:
            if force_mouse_mode:
                status = "鼠标模式：左键执行当前工具，右键临时擦除"
            else:
                status = f"{translate_status(hand_data.get('status_message', '手势识别不可用'))}，已启用鼠标备用模式"
        else:
            status = translate_status(hand_data.get("status_message", "Hand tracking ready"))
        status = f"drawing | {status}"
        draw_ui(
            screen,
            font,
            small_font,
            status,
            canvas,
            input_mode,
            tool_mode,
            eraser_radius,
            zoom,
            save_message_timer,
            generation_state,
            current_theme,
            extra_keywords_text,
            keyword_editing,
        )
        if keyword_editing:
            draw_keyword_editor_dialog(screen, font, small_font, extra_keywords_text)

        if should_save_sketch:
            saved_path = canvas.save_sketch(screen)
            print(f"草图已保存：{saved_path}")
            save_message_timer = SAVE_MESSAGE_DURATION
            should_save_sketch = False

        if save_message_timer > 0:
            save_message_timer -= 1

        pygame.display.flip()
        clock.tick(FPS)

    hand_tracker.release()
    pygame.quit()


if __name__ == "__main__":
    main()

