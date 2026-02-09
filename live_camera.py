"""
Live Camera Recording Module for Wellio rPPG Application
(Streamlit WebRTC Implementation with MediaPipe Face Mesh)

This module provides a live camera interface with advanced face tracking,
stability checks, and automatic recording integration.
"""

import av
import cv2
import numpy as np
import time
import threading
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode, RTCConfiguration
import mediapipe as mp
import tempfile
import os

# Import translations
from translations import get_text as t

# Helper class for thread-safe value storage
class SharedState:
    def __init__(self):
        self.face_detected = False
        self.is_aligned = False
        self.guidance_text = ""
        self.guidance_color = (255, 255, 255) # RGB
        self.recording_active = False
        self.recording_start_time = 0
        self.recorded_frames = []
        self.process_complete = False
        self.countdown_active = False
        self.countdown_start = 0
        self.alignment_stable_start = 0

class FaceGuidanceProcessor(VideoProcessorBase):
    def __init__(self, language="en"):
        self.language = language
        self.shared_state = SharedState()
        self.lock = threading.Lock()
        
        try:
            # Initialize MediaPipe Face Mesh
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.use_mediapipe = True
        except Exception as e:
            # Fallback to Haar Cascade if MediaPipe fails (e.g. Python 3.13 issues)
            print(f"MediaPipe initialization failed: {e}. Falling back to Haar Cascades.")
            self.use_mediapipe = False
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        height, width = img.shape[:2]
        
        # Mirror image for better UX
        img = cv2.flip(img, 1)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process frame
        if self.use_mediapipe:
            # MediaPipe Logic
            results = self.face_mesh.process(rgb_img)
            
            if not results.multi_face_landmarks:
                current_guidance = "Face not detected"
                self.shared_state.alignment_stable_start = 0
            else:
                face_detected = True
                landmarks = results.multi_face_landmarks[0].landmark
                
                # Get key landmarks for alignment
                nose = landmarks[1]
                left_ear = landmarks[234]
                right_ear = landmarks[454]
                
                # Convert to pixels
                nose_x, nose_y = int(nose.x * width), int(nose.y * height)
                face_width = int(abs(right_ear.x - left_ear.x) * width)
                
                # Check centering
                offset_x = abs(nose_x - center_x)
                offset_y = abs(nose_y - center_y)
                
                # Heuristics
                if offset_x > radius_x * 0.4 or offset_y > radius_y * 0.4:
                    current_guidance = "Center your face"
                    self.shared_state.alignment_stable_start = 0
                elif face_width < radius_x * 0.8:
                    current_guidance = "Move closer"
                    self.shared_state.alignment_stable_start = 0
                elif face_width > radius_x * 1.5:
                    current_guidance = "Move back"
                    self.shared_state.alignment_stable_start = 0
                else:
                    current_guidance = "Perfect! Stay still"
                    current_color = (0, 255, 0) # Green
                    aligned = True
        else:
            # Fallback Usage (Haar Cascade)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                current_guidance = "Face not detected (Basic Mode)"
                self.shared_state.alignment_stable_start = 0
            else:
                face_detected = True
                largest_face = max(faces, key=lambda r: r[2] * r[3])
                x, y, w, h = largest_face
                face_center_x = x + w // 2
                face_center_y = y + h // 2
                
                offset_x = abs(face_center_x - center_x)
                offset_y = abs(face_center_y - center_y)
                
                if offset_x > radius_x * 0.5 or offset_y > radius_y * 0.5:
                    current_guidance = "Center your face"
                    self.shared_state.alignment_stable_start = 0
                elif w < radius_x * 1.0:
                    current_guidance = "Move closer"
                    self.shared_state.alignment_stable_start = 0
                else:
                    current_guidance = "Perfect! Stay still"
                    current_color = (0, 255, 0)
                    aligned = True

        with self.lock:
            # Shared logic for recording (same for both modes)
            # Logic for Auto-Recording
            now = time.time()
            # ... (Rest of logic continues below)
                
            # Logic for Auto-Recording
            now = time.time()
            
            if not self.shared_state.recording_active and not self.shared_state.process_complete:
                if aligned:
                    if self.shared_state.alignment_stable_start == 0:
                        self.shared_state.alignment_stable_start = now
                        current_guidance = "Hold still..."
                    else:
                        stable_duration = now - self.shared_state.alignment_stable_start
                        if stable_duration < 2.0:
                             current_guidance = f"Hold still... {2.0 - stable_duration:.1f}s"
                        else:
                            # Stability achieved -> Start Countdown
                            if not self.shared_state.countdown_active:
                                self.shared_state.countdown_active = True
                                self.shared_state.countdown_start = now
                else:
                    self.shared_state.alignment_stable_start = 0
                    self.shared_state.countdown_active = False
                
                # Handle Countdown
                if self.shared_state.countdown_active:
                    elapsed = now - self.shared_state.countdown_start
                    if elapsed < 3.0:
                        count = 3 - int(elapsed)
                        current_guidance = f"Starting in {count}..."
                        current_color = (0, 255, 255) # Yellow
                    else:
                        self.shared_state.recording_active = True
                        self.shared_state.recording_start_time = now
                        self.shared_state.countdown_active = False
            
            elif self.shared_state.recording_active:
                # Record frame
                self.shared_state.recorded_frames.append(img.copy())
                
                elapsed = now - self.shared_state.recording_start_time
                remaining = 15 - int(elapsed) # 15s recording
                current_guidance = f"Recording... {remaining}s"
                current_color = (0, 0, 255) # Red
                
                if elapsed >= 15.0:
                    self.shared_state.recording_active = False
                    self.shared_state.process_complete = True
                    current_guidance = "Recording Complete!"
            
            elif self.shared_state.process_complete:
                current_guidance = "Processing..."
                
            # Draw overlay
            # Oval guidance
            color = current_color
            cv2.ellipse(img, (center_x, center_y), (radius_x, radius_y), 0, 0, 360, color, 2)
            
            # Text overlay
            # Add a background box for text readability
            (text_w, text_h), baseline = cv2.getTextSize(current_guidance, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(img, (center_x - text_w//2 - 10, 50 - text_h - 10), (center_x + text_w//2 + 10, 50 + baseline + 5), (0,0,0), -1)
            cv2.putText(img, current_guidance, (center_x - text_w//2, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            self.shared_state.guidance_text = current_guidance

        return av.VideoFrame.from_ndarray(img, format="bgr24")


def live_camera_interface():
    """
    Renders the Webrtc streamer and handles the recording logic.
    Returns path to video file if recording is complete, else None.
    """
    
    # Enhanced ICE Servers for better connectivity
    rtc_config = RTCConfiguration(
        {"iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302"]},
            {"urls": ["stun:stun3.l.google.com:19302"]},
            {"urls": ["stun:stun4.l.google.com:19302"]},
        ]}
    )
    
    ctx = webrtc_streamer(
        key="live_camera",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_config,
        video_processor_factory=FaceGuidanceProcessor,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )
    
    if ctx.video_processor:
        processor = ctx.video_processor
        placeholder = st.empty()
        
        while ctx.state.playing:
            if processor.shared_state.process_complete:
                placeholder.success("Recording complete! Processing data...")
                
                frames = processor.shared_state.recorded_frames
                if frames:
                    try:
                        tmp_dir = tempfile.mkdtemp()
                        tmp_path = os.path.join(tmp_dir, "live_recording.mp4")
                        
                        height, width, _ = frames[0].shape
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        out = cv2.VideoWriter(tmp_path, fourcc, 30.0, (width, height))
                        
                        for frame in frames:
                            out.write(frame)
                        out.release()
                        
                        return tmp_path
                    except Exception as e:
                        st.error(f"Error saving video: {e}")
                        return None
                else:
                    st.error("No frames captured.")
                    return None
            
            # Update UI status messages
            state = processor.shared_state
            if state.recording_active:
                elapsed = time.time() - state.recording_start_time
                placeholder.progress(min(elapsed / 15.0, 1.0), text="Recording typical rPPG segment...")
            elif state.countdown_active:
                placeholder.warning(f"Get ready! Starting in {3 - int(time.time() - state.countdown_start)}...")
            elif state.alignment_stable_start > 0:
                placeholder.info("Face locked! Hold still...")
            else:
                 # Minimal update to keep loop responsive without burning CPU
                 time.sleep(0.1)
            
            time.sleep(0.1)
                
    return None

def process_recorded_video(video_path: str):
    return video_path
