"""手势追踪模块。

使用 OpenCV 打开摄像头，并用 MediaPipe Tasks HandLandmarker 获取食指指尖位置。
这个模块只负责“看见手”和“给出食指坐标”，不负责绘画逻辑。
"""

from pathlib import Path

import cv2

try:
    from mediapipe.tasks.python.core import base_options as base_options_module
    from mediapipe.tasks.python.vision import hand_landmarker
    from mediapipe.tasks.python.vision.core import image as image_module
    from mediapipe.tasks.python.vision.core import vision_task_running_mode as running_mode_module
except ImportError:
    base_options_module = None
    hand_landmarker = None
    image_module = None
    running_mode_module = None


class HandTracker:
    """基础手势追踪器。"""

    def __init__(self, camera_index=0, width=960, height=540):
        # 打开默认摄像头
        self.cap = cv2.VideoCapture(camera_index)
        self.width = width
        self.height = height
        self.timestamp_ms = 0

        # 尽量让摄像头画面和 Pygame 窗口比例接近
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.landmarker = None
        self.hand_tracking_ready = False
        self.status_message = "Hand tracking model not ready"

        self.model_path = Path(__file__).resolve().parent / "assets" / "hand_landmarker.task"
        self._init_hand_landmarker()

    def _init_hand_landmarker(self):
        """初始化 MediaPipe Tasks 手部关键点模型。"""
        if hand_landmarker is None:
            self.status_message = "MediaPipe Tasks import failed"
            return

        if not self.model_path.exists():
            self.status_message = "Missing assets/hand_landmarker.task"
            return

        try:
            base_options = base_options_module.BaseOptions(
                model_asset_path=str(self.model_path)
            )
            options = hand_landmarker.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=running_mode_module.VisionTaskRunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.landmarker = hand_landmarker.HandLandmarker.create_from_options(options)
            self.hand_tracking_ready = True
            self.status_message = "Hand tracking ready"
        except Exception as error:
            self.status_message = f"Hand tracking init failed: {error}"
            self.hand_tracking_ready = False

    def update(self):
        """读取一帧摄像头画面，并返回食指坐标。

        返回格式：
        {
            "frame": 摄像头画面,
            "index_pos": (x, y) 或 None,
            "is_drawing": True/False,
            "hand_tracking_ready": True/False,
            "status_message": 状态文字
        }
        """
        success, frame = self.cap.read()
        if not success:
            return self._build_result(None, None, False, "Camera not found")

        # 镜像画面，让它像照镜子一样自然
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (self.width, self.height))

        if not self.hand_tracking_ready:
            return self._build_result(frame, None, False, self.status_message)

        try:
            # OpenCV 是 BGR，MediaPipe Image 需要 RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = image_module.Image(image_format=image_module.ImageFormat.SRGB, data=rgb_frame)

            # VIDEO 模式要求时间戳递增
            self.timestamp_ms += 33
            result = self.landmarker.detect_for_video(mp_image, self.timestamp_ms)
        except Exception as error:
            return self._build_result(frame, None, False, f"Hand tracking error: {error}")

        if not result.hand_landmarks:
            return self._build_result(frame, None, False, "Show your hand to draw")

        landmarks = result.hand_landmarks[0]
        index_tip = landmarks[hand_landmarker.HandLandmark.INDEX_FINGER_TIP]

        # 把 0-1 的归一化坐标转换成窗口像素坐标
        x = int(index_tip.x * self.width)
        y = int(index_tip.y * self.height)
        index_pos = (x, y)

        # 画到摄像头预览上，方便确认程序真的识别到了食指
        cv2.circle(frame, index_pos, 10, (0, 255, 255), -1)
        cv2.putText(
            frame,
            "Index",
            (x + 12, y - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
        )

        return self._build_result(frame, index_pos, True, "Index finger detected")

    def _build_result(self, frame, index_pos, is_drawing, status_message):
        """统一整理返回数据，减少 update 里的重复代码。"""
        return {
            "frame": frame,
            "index_pos": index_pos,
            "is_drawing": is_drawing,
            "hand_tracking_ready": self.hand_tracking_ready,
            "status_message": status_message,
        }

    def release(self):
        """释放摄像头和 MediaPipe 资源。"""
        self.cap.release()
        if self.landmarker is not None:
            self.landmarker.close()
