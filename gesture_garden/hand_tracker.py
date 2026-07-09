"""手势追踪模块。

使用 OpenCV 打开摄像头，并用 MediaPipe Tasks HandLandmarker 获取食指指尖位置。
绘画触发规则：拇指和食指捏合时触发当前工具；不捏合时只移动光标。
"""

from pathlib import Path
import math

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

        # 捏合阈值：使用 MediaPipe 的 0-1 归一化坐标计算。
        # 开始阈值比旧值稍大，让捏合更容易触发；结束阈值更大，避免临界抖动频繁断线。
        self.pinch_start_threshold = 0.065
        self.pinch_end_threshold = 0.085

        # 连续帧确认：避免一帧误判就立刻开始或结束操作。
        self.pinch_start_frames = 2
        self.pinch_end_frames = 4
        self.pinch_hold_frames = 6
        self.pinch_candidate_count = 0
        self.release_candidate_count = 0
        self.hold_count = 0
        self.stable_is_pinching = False
        self.last_index_pos = None
        self.last_thumb_pos = None
        self.last_pinch_distance = None

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
        """读取一帧摄像头画面，并返回光标坐标和捏合状态。"""
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
            # 手部短暂丢失时，如果刚才还在捏合，先保持几帧，避免操作被摄像头抖动切断。
            if self.stable_is_pinching and self.hold_count < self.pinch_hold_frames:
                self.hold_count += 1
                status_message = "Pinch held: active"
                if self.last_index_pos is not None and self.last_thumb_pos is not None:
                    self._draw_hand_debug(
                        frame,
                        self.last_index_pos,
                        self.last_thumb_pos,
                        True,
                        self.last_pinch_distance,
                    )
                return self._build_result(
                    frame,
                    self.last_index_pos,
                    True,
                    status_message,
                    is_pinching=True,
                    thumb_pos=self.last_thumb_pos,
                    pinch_distance=self.last_pinch_distance,
                )

            self._reset_pinch_state()
            return self._build_result(frame, None, False, "Show your hand to move cursor")

        landmarks = result.hand_landmarks[0]
        index_tip = landmarks[hand_landmarker.HandLandmark.INDEX_FINGER_TIP]
        thumb_tip = landmarks[hand_landmarker.HandLandmark.THUMB_TIP]

        # 把 0-1 的归一化坐标转换成窗口像素坐标
        index_pos = self._to_pixel(index_tip)
        thumb_pos = self._to_pixel(thumb_tip)

        pinch_distance = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
        is_pinching = self._update_pinch_state(pinch_distance)
        status_message = "Pinch detected: active" if is_pinching else "Move cursor; pinch to use tool"

        self.last_index_pos = index_pos
        self.last_thumb_pos = thumb_pos
        self.last_pinch_distance = pinch_distance

        # 画到摄像头预览上，方便确认程序识别到了食指、拇指、捏合状态和距离数值。
        self._draw_hand_debug(frame, index_pos, thumb_pos, is_pinching, pinch_distance)

        return self._build_result(
            frame,
            index_pos,
            is_pinching,
            status_message,
            is_pinching=is_pinching,
            thumb_pos=thumb_pos,
            pinch_distance=pinch_distance,
        )

    def _to_pixel(self, landmark):
        """把 MediaPipe 的归一化坐标转换为窗口像素坐标。"""
        x = int(landmark.x * self.width)
        y = int(landmark.y * self.height)
        return (x, y)

    def _update_pinch_state(self, pinch_distance):
        """用迟滞阈值和连续帧确认，得到更稳定的捏合状态。"""
        self.hold_count = 0

        if self.stable_is_pinching:
            # 已经在操作时，只有明显松开并持续几帧，才真正退出。
            if pinch_distance >= self.pinch_end_threshold:
                self.release_candidate_count += 1
            else:
                self.release_candidate_count = 0

            if self.release_candidate_count >= self.pinch_end_frames:
                self.stable_is_pinching = False
                self.release_candidate_count = 0
                self.pinch_candidate_count = 0
        else:
            # 未操作时，连续几帧满足开始阈值，才进入操作。
            if pinch_distance <= self.pinch_start_threshold:
                self.pinch_candidate_count += 1
            else:
                self.pinch_candidate_count = 0

            if self.pinch_candidate_count >= self.pinch_start_frames:
                self.stable_is_pinching = True
                self.pinch_candidate_count = 0
                self.release_candidate_count = 0

        return self.stable_is_pinching

    def _reset_pinch_state(self):
        """手部持续丢失后，重置捏合状态。"""
        self.stable_is_pinching = False
        self.pinch_candidate_count = 0
        self.release_candidate_count = 0
        self.hold_count = 0
        self.last_index_pos = None
        self.last_thumb_pos = None
        self.last_pinch_distance = None

    def _draw_hand_debug(self, frame, index_pos, thumb_pos, is_pinching, pinch_distance=None):
        """在摄像头预览上绘制调试标记。"""
        if index_pos is None or thumb_pos is None:
            return

        color = (0, 255, 0) if is_pinching else (0, 255, 255)
        label = "Pinch" if is_pinching else "Cursor"
        if pinch_distance is not None:
            label = f"{label} {pinch_distance:.3f}"

        cv2.circle(frame, index_pos, 10, color, -1)
        cv2.circle(frame, thumb_pos, 8, (255, 180, 0), -1)
        cv2.line(frame, index_pos, thumb_pos, color, 2)
        cv2.putText(
            frame,
            label,
            (index_pos[0] + 12, index_pos[1] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )

    def _build_result(
        self,
        frame,
        index_pos,
        is_drawing,
        status_message,
        is_pinching=False,
        thumb_pos=None,
        pinch_distance=None,
    ):
        """统一整理返回数据，减少 update 里的重复代码。"""
        return {
            "frame": frame,
            "index_pos": index_pos,
            "thumb_pos": thumb_pos,
            "is_drawing": is_drawing,
            "is_pinching": is_pinching,
            "pinch_distance": pinch_distance,
            "hand_tracking_ready": self.hand_tracking_ready,
            "status_message": status_message,
        }

    def release(self):
        """释放摄像头和 MediaPipe 资源。"""
        self.cap.release()
        if self.landmarker is not None:
            self.landmarker.close()
