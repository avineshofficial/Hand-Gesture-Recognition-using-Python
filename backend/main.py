import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import threading
from enum import Enum

# --- CONFIGURATION CONSTANTS ---
# Feel & Usability
SMOOTHING_FACTOR = 0.15         # Lower value = smoother but more latency. 0.15 is a good balance.
CURSOR_MAPPING_BORDER = 0.1     # Dead zone at camera edges (0.1 = 10% border).
# Gestures
PINCH_DISTANCE_THRESHOLD = 0.045 # Slightly increased for easier pinching.
ACTION_COOLDOWN = 0.5           # Seconds between distinct actions.
# STABILITY
POSE_CONFIRMATION_THRESHOLD = 5 # Number of consecutive frames to confirm a new pose.

# --- SETUP ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

class Pose(Enum):
    """Defines the recognized hand poses."""
    IDLE = 0; FIST = 1; OPEN_PALM = 2; POINTER = 3
    PEACE_SIGN = 4; THUMBS_UP = 5; CALL_ME = 6

class HandTracker(threading.Thread):
    """A dedicated thread for handling camera input and MediaPipe processing."""
    def __init__(self):
        super().__init__(daemon=True)
        self.lock = threading.Lock()
        self.landmarks = None
        self.image_frame = None
        self.running = False

    def run(self):
        self.running = True
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.75, min_tracking_confidence=0.75, max_num_hands=1)
        mp_draw = mp.solutions.drawing_utils
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while self.running:
            success, image = cap.read()
            if not success:
                time.sleep(0.1)
                continue

            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            with self.lock:
                if results.multi_hand_landmarks:
                    self.landmarks = results.multi_hand_landmarks[0]
                    mp_draw.draw_landmarks(image, self.landmarks, mp_hands.HAND_CONNECTIONS)
                else:
                    self.landmarks = None
                self.image_frame = image
        cap.release()

    def get_data(self):
        with self.lock:
            return self.landmarks, self.image_frame

    def stop(self):
        self.running = False

class GestureController:
    """Manages the application state and maps finger poses to cursor functions."""
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.current_pose = Pose.IDLE
        self.last_action_time = 0
        self.is_dragging = False
        self.smooth_x, self.smooth_y = self.screen_width / 2, self.screen_height / 2
        self.scroll_origin_y = None
        self.tracker = HandTracker()
        
        # Stability variables
        self.pose_candidate = None
        self.pose_confirmation_frames = 0

    def _get_hand_pose(self, landmarks):
        """
        Determines the current hand pose using a robust vector-based method.
        This is resilient to hand rotation.
        """
        if not landmarks: return Pose.IDLE
        
        landmark_list = landmarks.landmark

        # --- Vector-based Finger State Detection ---
        # 1. Define the 'up' direction of the palm
        wrist = np.array([landmark_list[0].x, landmark_list[0].y, landmark_list[0].z])
        middle_mcp = np.array([landmark_list[9].x, landmark_list[9].y, landmark_list[9].z])
        palm_up_vector = middle_mcp - wrist
        palm_up_vector = palm_up_vector / np.linalg.norm(palm_up_vector)

        # 2. Check each finger's direction relative to the palm's up direction
        finger_states = []
        # Index, Middle, Ring, Pinky
        for tip_idx, mcp_idx in [(8, 5), (12, 9), (16, 13), (20, 17)]:
            tip = np.array([landmark_list[tip_idx].x, landmark_list[tip_idx].y, landmark_list[tip_idx].z])
            mcp = np.array([landmark_list[mcp_idx].x, landmark_list[mcp_idx].y, landmark_list[mcp_idx].z])
            finger_vector = tip - mcp
            finger_vector = finger_vector / np.linalg.norm(finger_vector)
            
            # Dot product determines alignment. > 0.6 means finger is mostly pointing "up".
            if np.dot(finger_vector, palm_up_vector) > 0.6:
                finger_states.append(True)
            else:
                finger_states.append(False)
        
        is_index_up, is_middle_up, is_ring_up, is_pinky_up = finger_states

        # 3. Check Thumb separately (it moves differently)
        thumb_tip = landmark_list[4]
        thumb_ip = landmark_list[3]
        is_thumb_up = thumb_tip.y < thumb_ip.y # The simpler y-check is often fine for the thumb

        # --- Pose Matching Logic ---
        if is_thumb_up and is_pinky_up and not is_index_up and not is_middle_up and not is_ring_up:
            return Pose.CALL_ME
        if is_thumb_up and not any(finger_states):
            return Pose.THUMBS_UP
        if all(finger_states):
            return Pose.OPEN_PALM
        if not any(finger_states) and not is_thumb_up: # More strict fist
            return Pose.FIST
        if finger_states == [True, False, False, False]:
            return Pose.POINTER
        if finger_states == [True, True, False, False]:
            return Pose.PEACE_SIGN

        return Pose.IDLE

    def _get_distance(self, landmark_list, p1_idx, p2_idx):
        p1 = landmark_list[p1_idx]
        p2 = landmark_list[p2_idx]
        return np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p2.x, p2.y]))

    def _update_cursor(self, landmark_list, tracking_point_idx=8):
        tracking_point = landmark_list[tracking_point_idx]
        
        raw_x = np.interp(tracking_point.x, [CURSOR_MAPPING_BORDER, 1 - CURSOR_MAPPING_BORDER], [0, self.screen_width])
        raw_y = np.interp(tracking_point.y, [CURSOR_MAPPING_BORDER, 1 - CURSOR_MAPPING_BORDER], [0, self.screen_height])
        
        self.smooth_x = SMOOTHING_FACTOR * raw_x + (1 - SMOOTHING_FACTOR) * self.smooth_x
        self.smooth_y = SMOOTHING_FACTOR * raw_y + (1 - SMOOTHING_FACTOR) * self.smooth_y
        
        pyautogui.moveTo(self.smooth_x, self.smooth_y)

    def _handle_pointer_pose(self, landmark_list):
        self._update_cursor(landmark_list)
        can_act = (time.time() - self.last_action_time) > ACTION_COOLDOWN

        if can_act:
            if self._get_distance(landmark_list, 4, 8) < PINCH_DISTANCE_THRESHOLD:
                pyautogui.click()
                print("Action: Left Click")
                self.last_action_time = time.time()
            elif self._get_distance(landmark_list, 4, 12) < PINCH_DISTANCE_THRESHOLD:
                pyautogui.rightClick()
                print("Action: Right Click")
                self.last_action_time = time.time()
            elif self._get_distance(landmark_list, 4, 16) < PINCH_DISTANCE_THRESHOLD:
                pyautogui.doubleClick()
                print("Action: Double Click")
                self.last_action_time = time.time()

    def _handle_thumbs_up_pose(self, landmark_list):
        self._update_cursor(landmark_list, tracking_point_idx=4)
        distance = self._get_distance(landmark_list, 4, 8)
        
        if distance < PINCH_DISTANCE_THRESHOLD and not self.is_dragging:
            pyautogui.mouseDown()
            self.is_dragging = True
            print("Action: Drag Start")
        elif distance > (PINCH_DISTANCE_THRESHOLD + 0.015) and self.is_dragging:
            pyautogui.mouseUp()
            self.is_dragging = False
            print("Action: Drag End")

    def _handle_peace_sign_pose(self, landmark_list):
        if self.scroll_origin_y is None:
            self.scroll_origin_y = landmark_list[8].y
        
        current_y = landmark_list[8].y
        delta_y = self.scroll_origin_y - current_y
        scroll_amount = int(delta_y * 400)
        if abs(scroll_amount) > 3:
            pyautogui.scroll(scroll_amount)
        self.scroll_origin_y = current_y

    def _update_debug_window(self, frame):
        if frame is not None:
            cv2.putText(frame, f"POSE: {self.current_pose.name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Gesture Controller - Debug", frame)
            return cv2.waitKey(1) & 0xFF

    def run(self):
        self.tracker.start()
        print("--- Pro Gesture Controller (Rock-Solid Version) ---")
        print("Show an open palm to get started.")
        print("Press 'ESC' in the camera window to exit.")

        try:
            while True:
                landmarks, frame = self.tracker.get_data()
                
                raw_pose = self._get_hand_pose(landmarks)

                if raw_pose == self.current_pose:
                    self.pose_confirmation_frames = 0
                    self.pose_candidate = None
                else:
                    if raw_pose == self.pose_candidate:
                        self.pose_confirmation_frames += 1
                    else:
                        self.pose_candidate = raw_pose
                        self.pose_confirmation_frames = 1
                
                if self.pose_candidate and self.pose_confirmation_frames >= POSE_CONFIRMATION_THRESHOLD:
                    print(f"Pose Changed: {self.current_pose.name} -> {self.pose_candidate.name}")
                    self.current_pose = self.pose_candidate
                    self.scroll_origin_y = None 
                    if self.is_dragging:
                        pyautogui.mouseUp()
                        self.is_dragging = False
                    self.pose_confirmation_frames = 0
                    self.pose_candidate = None

                if landmarks:
                    landmark_list = landmarks.landmark
                    if self.current_pose == Pose.POINTER:
                        self._handle_pointer_pose(landmark_list)
                    elif self.current_pose == Pose.THUMBS_UP:
                        self._handle_thumbs_up_pose(landmark_list)
                    elif self.current_pose == Pose.PEACE_SIGN:
                        self._handle_peace_sign_pose(landmark_list)
                    elif self.current_pose == Pose.CALL_ME and (time.time() - self.last_action_time) > 1.5:
                        pyautogui.hotkey('win', 'd')
                        print("Action: Show Desktop")
                        self.last_action_time = time.time()
                
                if self._update_debug_window(frame) == 27:
                    break
                time.sleep(0.001)
        finally:
            print("\nShutting down...")
            self.tracker.stop()
            self.tracker.join()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    controller = GestureController()
    controller.run()