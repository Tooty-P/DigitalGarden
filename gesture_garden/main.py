"""Magic Canvas AI 主程序。

当前阶段目标：
摄像头识别食指位置 -> 在空气中绘画 -> 保存绘画草图 -> AI 理解 -> 图片生成 -> 展示结果。
真实 AI API 仍然是可替换接口，没有配置 API 时会自动使用模拟结果。
"""

import math
import threading

import cv2
import pygame

from ai.ai_client import AIClient
from drawing.canvas import Canvas
from generation.image_generator import ImageGenerator
from hand_tracker import HandTracker


# 窗口基础配置
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
WINDOW_TITLE = "Magic Canvas AI - 手势动漫 AI 绘画画布"
FPS = 60
SAVE_MESSAGE_DURATION = 120


class MagicCanvasBackground:
    """绘制简洁的二次元魔法画布背景。"""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def draw(self, screen):
        """绘制深色柔和渐变背景和少量装饰线。"""
        top_color = (21, 24, 52)
        bottom_color = (52, 72, 108)

        # 竖向渐变背景
        for y in range(self.height):
            t = y / self.height
            color = (
                int(top_color[0] * (1 - t) + bottom_color[0] * t),
                int(top_color[1] * (1 - t) + bottom_color[1] * t),
                int(top_color[2] * (1 - t) + bottom_color[2] * t),
            )
            pygame.draw.line(screen, color, (0, y), (self.width, y))

        # 画布中心的淡淡光圈，让界面有“魔法画布”的感觉
        glow = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for radius, alpha in [(260, 28), (180, 36), (100, 30)]:
            pygame.draw.circle(
                glow,
                (108, 226, 255, alpha),
                (self.width // 2, self.height // 2),
                radius,
            )
        screen.blit(glow, (0, 0))

        # 少量星点，保持画面清爽
        for i in range(28):
            x = (i * 137) % self.width
            y = 48 + (i * 71) % (self.height - 120)
            alpha = 90 + int(math.sin(pygame.time.get_ticks() * 0.001 + i) * 35)
            star = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(star, (235, 249, 255, alpha), (4, 4), 2)
            screen.blit(star, (x, y))

        # 边缘细线，像电子画布边框
        border_color = (120, 220, 255)
        pygame.draw.rect(
            screen,
            border_color,
            (18, 18, self.width - 36, self.height - 36),
            1,
            border_radius=18,
        )


def create_font(size):
    """创建支持中文的字体。"""
    font_name = pygame.font.match_font("microsoftyahei")
    if font_name is None:
        font_name = pygame.font.match_font("simhei")
    return pygame.font.Font(font_name, size) if font_name else pygame.font.Font(None, size)


def draw_camera_preview(screen, frame, font):
    """在右上角绘制摄像头预览。"""
    panel_rect = pygame.Rect(WINDOW_WIDTH - 250, 24, 220, 140)
    pygame.draw.rect(screen, (12, 18, 42), panel_rect, border_radius=12)
    pygame.draw.rect(screen, (112, 217, 255), panel_rect, 2, border_radius=12)

    if frame is None:
        text = font.render("未检测到摄像头", True, (230, 240, 255))
        screen.blit(text, text.get_rect(center=panel_rect.center))
        return

    # OpenCV 是 BGR，Pygame 需要 RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    preview_surface = pygame.image.frombuffer(
        rgb_frame.tobytes(),
        (rgb_frame.shape[1], rgb_frame.shape[0]),
        "RGB",
    )
    preview_surface = pygame.transform.smoothscale(preview_surface, (206, 116))
    screen.blit(preview_surface, (panel_rect.x + 7, panel_rect.y + 8))

    label = font.render("摄像头", True, (218, 246, 255))
    screen.blit(label, (panel_rect.x + 12, panel_rect.bottom - 23))


def draw_pointer(screen, point, color):
    """绘制当前食指或鼠标位置提示。"""
    if point is None:
        return

    x, y = point
    pointer_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(pointer_layer, (*color, 65), (x, y), 24)
    pygame.draw.circle(pointer_layer, (255, 248, 166, 125), (x, y), 10)
    pygame.draw.circle(pointer_layer, (255, 255, 255, 230), (x, y), 4)
    screen.blit(pointer_layer, (0, 0))


def draw_ui(screen, font, status_text, canvas, input_mode, save_message_timer, generation_state):
    """绘制左上角操作提示、画笔状态和保存成功提示。"""
    lines = [
        "Magic Canvas AI 魔法画布",
        status_text,
        "捏合画 / 松开移 | C清空 | S保存 | G生成 | M鼠标 | TAB/1-5换色 | [ ]笔刷 | Q/ESC退出",
    ]

    panel = pygame.Surface((860, 132), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 14, 35, 155), panel.get_rect(), border_radius=14)
    pygame.draw.rect(panel, (114, 223, 255, 90), panel.get_rect(), 2, border_radius=14)
    screen.blit(panel, (24, 24))

    for index, line in enumerate(lines):
        color = (245, 252, 255) if index == 0 else (191, 230, 245)
        text = font.render(line, True, color)
        screen.blit(text, (42, 40 + index * 25))

    # 显示当前输入模式、颜色和笔刷粗细
    mode_text = "手势" if input_mode == "Gesture" else "鼠标"
    brush_info = f"模式：{mode_text}    颜色：{canvas.color_names[canvas.color_index]}    笔刷：{canvas.brush_width}px"
    brush_text = font.render(brush_info, True, (255, 247, 168))
    screen.blit(brush_text, (42, 116))

    # 显示调色板，当前颜色用黄色外框标记
    swatch_x = 390
    swatch_y = 112
    for index, color in enumerate(canvas.palette):
        rect = pygame.Rect(swatch_x + index * 28, swatch_y, 20, 20)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        border_color = (255, 247, 168) if index == canvas.color_index else (120, 170, 200)
        border_width = 3 if index == canvas.color_index else 1
        pygame.draw.rect(screen, border_color, rect, border_width, border_radius=6)

    if save_message_timer > 0:
        alpha = min(220, save_message_timer * 4)
        message = font.render("草图已保存！", True, (255, 247, 168))
        rect = message.get_rect(center=(WINDOW_WIDTH // 2, 70))
        bubble = pygame.Surface((rect.width + 38, rect.height + 20), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (10, 18, 38, alpha), bubble.get_rect(), border_radius=16)
        pygame.draw.rect(bubble, (255, 238, 142, alpha), bubble.get_rect(), 2, border_radius=16)
        screen.blit(bubble, (rect.x - 19, rect.y - 10))
        screen.blit(message, rect)

    if generation_state["status"] == "loading":
        draw_loading(screen, font)
    elif generation_state["status"] == "error":
        draw_error_message(screen, font, generation_state["message"])


def draw_loading(screen, font):
    """绘制 AI 生成中的提示。"""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 10, 25, 95))
    screen.blit(overlay, (0, 0))

    dots = "." * ((pygame.time.get_ticks() // 350) % 4)
    text = font.render(f"AI 正在理解草图并生成图片{dots}", True, (255, 247, 168))
    rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
    panel = pygame.Surface((rect.width + 56, rect.height + 30), pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 18, 38, 220), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (120, 220, 255, 160), panel.get_rect(), 2, border_radius=18)
    screen.blit(panel, (rect.x - 28, rect.y - 15))
    screen.blit(text, rect)


def draw_error_message(screen, font, message):
    """绘制 AI 流程失败提示。"""
    text = font.render(f"生成失败：{message}", True, (255, 190, 205))
    rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 42))
    panel = pygame.Surface((min(rect.width + 44, 880), rect.height + 22), pygame.SRCALPHA)
    pygame.draw.rect(panel, (45, 12, 28, 210), panel.get_rect(), border_radius=14)
    screen.blit(panel, (max(40, rect.x - 22), rect.y - 11))
    screen.blit(text, rect)


def draw_generated_result(screen, font, generated_surface, prompt_text):
    """在右侧展示生成结果。"""
    if generated_surface is None:
        return

    panel_rect = pygame.Rect(WINDOW_WIDTH - 300, 184, 270, 330)
    panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 14, 35, 170), panel.get_rect(), border_radius=16)
    pygame.draw.rect(panel, (255, 247, 168, 150), panel.get_rect(), 2, border_radius=16)
    screen.blit(panel, panel_rect.topleft)

    title = font.render("AI 生成结果", True, (255, 247, 168))
    screen.blit(title, (panel_rect.x + 18, panel_rect.y + 14))

    preview = pygame.transform.smoothscale(generated_surface, (230, 130))
    screen.blit(preview, (panel_rect.x + 20, panel_rect.y + 48))

    prompt_label = font.render("Prompt 已生成", True, (218, 246, 255))
    screen.blit(prompt_label, (panel_rect.x + 18, panel_rect.y + 196))

    # 只显示 prompt 前几行，避免文字挤满画面
    short_prompt = prompt_text[:86] + "..." if len(prompt_text) > 86 else prompt_text
    for i, line in enumerate(wrap_text(short_prompt, 22)[:4]):
        text = font.render(line, True, (190, 220, 238))
        screen.blit(text, (panel_rect.x + 18, panel_rect.y + 226 + i * 22))


def wrap_text(text, line_length):
    """按字符数简单换行，适合短提示文本。"""
    return [text[i : i + line_length] for i in range(0, len(text), line_length)]


def translate_status(status_text):
    """把手势追踪状态转换成中文。"""
    status_map = {
        "Hand tracking ready": "手势识别已就绪",
        "Index finger detected": "已检测到食指",
        "Show your hand to draw": "请把手放到摄像头前",
        "Camera not found": "未检测到摄像头",
        "Hand tracking model not ready": "手势模型未就绪",
        "Missing assets/hand_landmarker.task": "缺少手势识别模型文件",
        "MediaPipe Tasks import failed": "MediaPipe Tasks 导入失败",
        "Show your hand to move cursor": "请把手放到摄像头前移动光标",
        "Move cursor; pinch to draw": "移动光标中：拇指和食指捏合开始绘画",
        "Pinch detected: drawing": "捏合已检测：正在绘画",
    }
    return status_map.get(status_text, status_text)


def handle_shortcuts(event, canvas):
    """处理画布相关快捷键。"""
    pressed_char = event.unicode.lower() if event.unicode else ""

    if event.key == pygame.K_c or pressed_char == "c":
        canvas.clear()
        print("画布已清空。")
    elif event.key == pygame.K_TAB:
        canvas.next_color()
    elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
        canvas.change_brush_width(-1)
    elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS):
        canvas.change_brush_width(1)
    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
        canvas.set_color_by_index(event.key - pygame.K_1)


def run_generation_flow(ai_client, image_generator, sketch_path, generation_state):
    """后台执行：草图 -> AI 理解 -> Prompt -> 图片生成。"""
    try:
        analysis_result = ai_client.analyze_sketch(sketch_path)
        prompt = analysis_result.get("prompt", "")
        generated_path = image_generator.generate(prompt)

        generation_state["status"] = "done"
        generation_state["sketch_path"] = str(sketch_path)
        generation_state["generated_path"] = str(generated_path)
        generation_state["prompt"] = prompt
        generation_state["message"] = "生成完成"
        print(f"草图已导出：{sketch_path}")
        print(f"生成 Prompt：{prompt}")
        print(f"生成图片：{generated_path}")
    except Exception as exc:
        generation_state["status"] = "error"
        generation_state["message"] = str(exc)
        print(f"AI 生成失败：{exc}")


def main():
    """程序入口：打开窗口、追踪食指、绘制并保存草图。"""
    pygame.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = create_font(21)

    background = MagicCanvasBackground(WINDOW_WIDTH, WINDOW_HEIGHT)
    canvas = Canvas(WINDOW_WIDTH, WINDOW_HEIGHT)
    hand_tracker = HandTracker(width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    ai_client = AIClient()
    image_generator = ImageGenerator()

    running = True
    was_drawing = False
    should_save_sketch = False
    save_message_timer = 0
    force_mouse_mode = False
    generation_state = {
        "status": "idle",
        "message": "",
        "sketch_path": "",
        "generated_path": "",
        "prompt": "",
    }
    generated_surface = None
    loaded_generated_path = ""

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                # 同时判断 key 和 unicode，避免中文输入法下 C/S/Q 不灵敏
                pressed_char = event.unicode.lower() if event.unicode else ""

                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q or pressed_char == "q":
                    running = False
                elif event.key == pygame.K_s or pressed_char == "s":
                    should_save_sketch = True
                elif event.key == pygame.K_g or pressed_char == "g":
                    if generation_state["status"] != "loading":
                        canvas.end_stroke()
                        was_drawing = False
                        sketch_path = canvas.save_sketch(screen)
                        generation_state.update(
                            {
                                "status": "loading",
                                "message": "AI 正在生成",
                                "sketch_path": str(sketch_path),
                                "generated_path": "",
                                "prompt": "",
                            }
                        )
                        generated_surface = None
                        loaded_generated_path = ""
                        worker = threading.Thread(
                            target=run_generation_flow,
                            args=(ai_client, image_generator, sketch_path, generation_state),
                            daemon=True,
                        )
                        worker.start()
                elif event.key == pygame.K_m or pressed_char == "m":
                    force_mouse_mode = not force_mouse_mode
                    canvas.end_stroke()
                    was_drawing = False
                else:
                    handle_shortcuts(event, canvas)

        hand_data = hand_tracker.update()
        frame = hand_data["frame"]
        hand_tracking_ready = hand_data.get("hand_tracking_ready", False)
        use_mouse = force_mouse_mode or not hand_tracking_ready

        if use_mouse:
            # 鼠标备用模式：按住左键绘画，适合摄像头失败或临时调试
            index_pos = pygame.mouse.get_pos()
            is_drawing = pygame.mouse.get_pressed()[0]
            input_mode = "Mouse"
        else:
            index_pos = hand_data["index_pos"]
            is_drawing = hand_data["is_drawing"]
            input_mode = "Gesture"

        # 食指或鼠标左键出现时开始/继续绘画；输入消失时结束这一笔
        if is_drawing and index_pos is not None:
            if not was_drawing:
                canvas.start_stroke(index_pos)
            else:
                canvas.add_point(index_pos)
            was_drawing = True
        else:
            if was_drawing:
                canvas.end_stroke()
            was_drawing = False

        # 后台生成完成后，在主线程加载图片，避免 Pygame 图像对象跨线程使用
        if generation_state["status"] == "done" and generation_state["generated_path"] != loaded_generated_path:
            try:
                generated_surface = pygame.image.load(generation_state["generated_path"]).convert()
                loaded_generated_path = generation_state["generated_path"]
                save_message_timer = SAVE_MESSAGE_DURATION
            except Exception as exc:
                generation_state["status"] = "error"
                generation_state["message"] = f"生成图加载失败：{exc}"

        background.draw(screen)
        canvas.draw(screen)
        draw_pointer(screen, index_pos, canvas.brush_color)
        draw_camera_preview(screen, frame, font)
        draw_generated_result(screen, font, generated_surface, generation_state["prompt"])

        if use_mouse:
            if force_mouse_mode:
                status = "鼠标模式：按住左键绘画"
            else:
                status = f"{translate_status(hand_data.get('status_message', '手势识别不可用'))}，已启用鼠标备用模式"
        else:
            status = translate_status(hand_data.get("status_message", "Hand tracking ready"))
        draw_ui(screen, font, status, canvas, input_mode, save_message_timer, generation_state)

        # 保存草图，供后续 AI 读取
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


