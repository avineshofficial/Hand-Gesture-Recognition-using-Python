import numpy as np
import time
from enum import Enum

# --- Define the Poses and Events ---

class Pose(Enum):
    """Defines the recognized hand poses."""
    IDLE = 0
    FIST = 1
    OPEN_PALM = 2
    POINTER = 3
    PEACE_SIGN = 4
    THUMBS_UP = 5
    CALL_ME = 6

class GestureEvent(Enum):
    """Defines the discrete actions that can be triggered."""
    LEFT_CLICK = 10
    RIGHT_CLICK = 11
    DOUBLE_CLICK = 12
    DRAG_START = 13
    DRAG_END = 14
    SCROLL = 15
    SHOW_DESKTOP = 16

class GestureDetector:
    """
    Analyzes hand landmarks to detect poses and trigger gesture events.
    This class is independent of PyAutoGUI and OpenCV.
    """
    def __init__(self, action_cooldown=0.5, pinch_threshold=0.04):
        """
        Initializes the gesture detector.
        Args:
            action_cooldown (float): Minimum time in seconds between discrete actions.
            pinch_threshold (float): Normalized distance to be considered a pinch.
        """
        self.current_pose = Pose.IDLE
        self.last_action_time = 0
        self.is_dragging = False
        self.scroll_origin_y = None
        
        # Configuration
        self.ACTION_COOLDOWN = action_cooldown
        self.PINCH_THRESHOLD = pinch_threshold

    def _get_distance(self, landmark_list, p1_idx, p2_idx):
        """Calculates the Euclidean distance between two landmark points."""
        if not landmark_list: return float('inf')
        p1 = landmark_list[p1_idx]
        p2 = landmark_list[p2_idx]
        return np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p2.x, p2.y]))

    def _get_hand_pose(self, landmarks):
        """
        Determines the current hand pose based on which fingers are extended.
        This method is robust and checks for specific finger combinations.
        """
        if not landmarks: return Pose.IDLE
        
        landmark_list = landmarks.landmark
        
        # Check the state of each finger (True if extended, False if not)
        is_thumb_up = landmark_list[4].y < landmark_list[3].y < landmark_list[2].y
        is_index_up = landmark_list[8].y < landmark_list[6].y
        is_middle_up = landmark_list[12].y < landmark_list[10].y
        is_ring_up = landmark_list[16].y < landmark_list[14].y
        is_pinky_up = landmark_list[20].y < landmark_list[18].y

        # Create a tuple representing the state of the 4 non-thumb fingers
        four_fingers_state = (is_index_up, is_middle_up, is_ring_up, is_pinky_up)

        # --- Pose Matching Logic (from most specific to least specific) ---
        if is_thumb_up and is_pinky_up and not is_index_up and not is_middle_up and not is_ring_up:
            return Pose.CALL_ME

        if is_thumb_up and not any(four_fingers_state):
            return Pose.THUMBS_UP
        
        if all(four_fingers_state):
            return Pose.OPEN_PALM
        
        if not any(four_fingers_state):
            return Pose.FIST
            
        if four_fingers_state == (True, False, False, False):
            return Pose.POINTER

        if four_fingers_state == (True, True, False, False):
            return Pose.PEACE_SIGN

        return Pose.IDLE # Default if no specific pose is matched

    def recognize(self, landmarks):
        """
        The main public method to recognize gestures from landmarks.
        Args:
            landmarks: The hand landmarks object from MediaPipe.
        Returns:
            A tuple containing:
            - new_pose (Pose): The currently detected pose.
            - events (list): A list of triggered GestureEvents or tuples for events with data.
        """
        events = []
        
        # --- FIX IS HERE ---
        new_pose = self._get_hand_pose(landmarks) # Changed self_get_hand_pose to self._get_hand_pose

        # --- Handle Pose Changes ---
        if new_pose != self.current_pose:
            if self.is_dragging:
                events.append(GestureEvent.DRAG_END)
                self.is_dragging = False
            self.scroll_origin_y = None
        
        self.current_pose = new_pose
        
        # --- Handle Actions within the Current Pose ---
        if landmarks:
            landmark_list = landmarks.landmark
            can_act = (time.time() - self.last_action_time) > self.ACTION_COOLDOWN

            if self.current_pose == Pose.POINTER and can_act:
                if self._get_distance(landmark_list, 4, 8) < self.PINCH_THRESHOLD:
                    events.append(GestureEvent.LEFT_CLICK)
                    self.last_action_time = time.time()
                elif self._get_distance(landmark_list, 4, 12) < self.PINCH_THRESHOLD:
                    events.append(GestureEvent.RIGHT_CLICK)
                    self.last_action_time = time.time()
                elif self._get_distance(landmark_list, 4, 16) < self.PINCH_THRESHOLD:
                    events.append(GestureEvent.DOUBLE_CLICK)
                    self.last_action_time = time.time()
            
            elif self.current_pose == Pose.THUMBS_UP:
                distance = self._get_distance(landmark_list, 4, 8)
                if distance < self.PINCH_THRESHOLD and not self.is_dragging:
                    events.append(GestureEvent.DRAG_START)
                    self.is_dragging = True
                elif distance > (self.PINCH_THRESHOLD + 0.015) and self.is_dragging:
                    events.append(GestureEvent.DRAG_END)
                    self.is_dragging = False

            elif self.current_pose == Pose.PEACE_SIGN:
                if self.scroll_origin_y is None:
                    self.scroll_origin_y = landmark_list[8].y
                
                current_y = landmark_list[8].y
                delta_y = self.scroll_origin_y - current_y
                events.append((GestureEvent.SCROLL, {'delta_y': delta_y}))
                self.scroll_origin_y = current_y

            elif self.current_pose == Pose.CALL_ME and can_act:
                events.append(GestureEvent.SHOW_DESKTOP)
                self.last_action_time = time.time()

        return self.current_pose, events

if __name__ == '__main__':
    print("Gesture Detector Module")
    print("This file should be imported by main.py, not run directly.")
    
    detector = GestureDetector()
    print(f"Initialized with default pose: {detector.current_pose.name}")