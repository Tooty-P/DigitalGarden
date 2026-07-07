import pygame


# 窗口基础配置
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
WINDOW_TITLE = "Blooming Spell: Gesture Garden"
FPS = 60


def main():
    """程序入口：创建一个最小 Pygame 窗口。"""
    # 初始化 Pygame
    pygame.init()

    # 创建窗口和时钟
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    running = True

    while running:
        # 处理窗口事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # 按 Q 或 ESC 退出程序
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    running = False

        # 使用柔和的深色背景，暂时不绘制复杂内容
        screen.fill((18, 20, 32))

        # 刷新窗口画面
        pygame.display.flip()

        # 控制帧率
        clock.tick(FPS)

    # 退出 Pygame
    pygame.quit()


if __name__ == "__main__":
    main()
