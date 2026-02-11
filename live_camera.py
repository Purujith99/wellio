"""
Live Camera Recording Module for Wellio rPPG Application
(Production-Safe Streamlit WebRTC Version)

- Auto face alignment
- Stability detection
- Countdown
- Direct-to-disk recording (no RAM frame storage)
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

# --- WebRTC Monkeypatch for Python 3.13 Compatibility ---
try:
    import streamlit_webrtc.shutdown
    # The error 'AttributeError: SessionShutdownObserver object has no attribute _polling_thread'
    # occurs during shutdown if the thread was never properly started/assigned.
    if hasattr(streamlit_webrtc.shutdown, "SessionShutdownObserver"):
        original_stop = streamlit_webrtc.shutdown.SessionShutdownObserver.stop
        def patched_stop(self):
            # Check if attribute exists before accessing it
            if hasattr(self, "_polling_thread") and self._polling_thread is not None:
                if self._polling_thread.is_alive():
                    original_stop(self)
            else:
                # Silently skip if the thread doesn't exist to avoid AttributeError
                pass
        streamlit_webrtc.shutdown.SessionShutdownObserver.stop = patched_stop
except (ImportError, AttributeError):
    pass
# -------------------------------------------------------


# =========================
# Shared State
# =========================

class SharedState:
    def __init__(self):
        self.recording_active = False
        self.recording_start_time = 0
        self.process_complete = False
        self.countdown_active = False
        self.countdown_start = 0
        self.alignment_stable_start = 0
        self.video_writer = None
        self.output_path = None


# =========================
# Video Processor
# =========================

class FaceGuidanceProcessor(VideoProcessorBase):
    def __init__(self):
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
            # Fallback to Haar Cascade if MediaPipe fails
            print(f"MediaPipe initialization failed: {e}. Falling back to Haar Cascades.")
            self.use_mediapipe = False
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)

        height, width = img.shape[:2]

        # ---- Define Guidance Frame ----
        center_x = width // 2
        center_y = height // 2
        radius_x = int(width * 0.25)
        radius_y = int(height * 0.35)

        # Defaults
        aligned = False
        current_guidance = "Align your face"
        current_color = (255, 255, 255)

        # Face Detection
        if self.use_mediapipe:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                nose = landmarks[1]
                left_ear = landmarks[234]
                right_ear = landmarks[454]

                nose_x = int(nose.x * width)
                nose_y = int(nose.y * height)
                face_width = int(abs(right_ear.x - left_ear.x) * width)

                offset_x = abs(nose_x - center_x)
                offset_y = abs(nose_y - center_y)

                if offset_x > radius_x * 0.4 or offset_y > radius_y * 0.4:
                    current_guidance = "Center your face"
                elif face_width < radius_x * 0.8:
                    current_guidance = "Move closer"
                elif face_width > radius_x * 1.5:
                    current_guidance = "Move back"
                else:
                    aligned = True
                    current_guidance = "Perfect! Hold still"
                    current_color = (0, 255, 0)
            else:
                current_guidance = "Face not detected"
        else:
            # Fallback to Haar Cascade
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) > 0:
                largest_face = max(faces, key=lambda r: r[2] * r[3])
                x, y, w, h = largest_face
                face_center_x = x + w // 2
                face_center_y = y + h // 2

                offset_x = abs(face_center_x - center_x)
                offset_y = abs(face_center_y - center_y)

                if offset_x > radius_x * 0.5 or offset_y > radius_y * 0.5:
                    current_guidance = "Center your face"
                elif w < radius_x * 1.0:
                    current_guidance = "Move closer"
                else:
                    aligned = True
                    current_guidance = "Perfect! Hold still"
                    current_color = (0, 255, 0)
            else:
                current_guidance = "Face not detected"

        # ========================
        # Recording Logic
        # ========================

        with self.lock:
            now = time.time()

            if not self.shared_state.recording_active and not self.shared_state.process_complete:

                if aligned:
                    if self.shared_state.alignment_stable_start == 0:
                        self.shared_state.alignment_stable_start = now
                    elif now - self.shared_state.alignment_stable_start >= 2.0:
                        if not self.shared_state.countdown_active:
                            self.shared_state.countdown_active = True
                            self.shared_state.countdown_start = now
                else:
                    self.shared_state.alignment_stable_start = 0
                    self.shared_state.countdown_active = False

                # Countdown
                if self.shared_state.countdown_active:
                    elapsed = now - self.shared_state.countdown_start
                    if elapsed < 3:
                        count = 3 - int(elapsed)
                        current_guidance = f"Starting in {count}..."
                        current_color = (0, 255, 255)
                    else:
                        # Start recording
                        tmp_dir = tempfile.mkdtemp()
                        output_path = os.path.join(tmp_dir, "recording.mp4")

                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        writer = cv2.VideoWriter(output_path, fourcc, 30.0, (width, height))

                        self.shared_state.video_writer = writer
                        self.shared_state.output_path = output_path
                        self.shared_state.recording_active = True
                        self.shared_state.recording_start_time = now
                        self.shared_state.countdown_active = False

            elif self.shared_state.recording_active:

                # Write frame directly to disk
                self.shared_state.video_writer.write(img)

                elapsed = now - self.shared_state.recording_start_time
                remaining = 15 - int(elapsed)

                current_guidance = f"Recording... {remaining}s"
                current_color = (0, 0, 255)

                if elapsed >= 15:
                    self.shared_state.video_writer.release()
                    self.shared_state.recording_active = False
                    self.shared_state.process_complete = True
                    current_guidance = "Recording Complete!"

            elif self.shared_state.process_complete:
                current_guidance = "Processing..."

        # ========================
        # Overlay Drawing
        # ========================

        cv2.ellipse(img, (center_x, center_y), (radius_x, radius_y),
                    0, 0, 360, current_color, 2)

        (text_w, text_h), baseline = cv2.getTextSize(
            current_guidance, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)

        cv2.rectangle(
            img,
            (center_x - text_w//2 - 10, 50 - text_h - 10),
            (center_x + text_w//2 + 10, 50 + baseline + 5),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            img,
            current_guidance,
            (center_x - text_w//2, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            current_color,
            2
        )

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# =========================
# Streamlit Interface
# =========================

def live_camera_interface():
    """
    Renders the WebRTC streamer and handles the recording logic.
    Returns path to video file if recording is complete, else None.
    """

    # Enhanced RTC Configuration with multiple reliable STUN servers
    # Using a variety of public STUN servers for better connectivity
    rtc_config = RTCConfiguration({
        "iceServers": [
            # Google STUN servers (most reliable)
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302"]},
            {"urls": ["stun:stun3.l.google.com:19302"]},
            {"urls": ["stun:stun4.l.google.com:19302"]},
            # Additional reliable STUN servers for fallback
            {"urls": ["stun:stun.services.mozilla.com:3478"]},
            {"urls": ["stun:stun.stunprotocol.org:3478"]},
        ],
        # ICE transport policy - "all" allows both STUN and host candidates
        "iceTransportPolicy": "all",
        # Bundle policy - "max-bundle" for better performance
        "bundlePolicy": "max-bundle",
        # RTCP mux policy
        "rtcpMuxPolicy": "require",
    })

    # Display connection tips
    st.info("📹 **Live Camera Tips:**\n"
            "- Allow camera permissions when prompted\n"
            "- Ensure good lighting for best results\n"
            "- Keep your face centered in the oval guide\n"
            "- Connection may take 5-10 seconds to establish")

    ctx = webrtc_streamer(
        key="live_camera_v3",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_config,
        video_processor_factory=FaceGuidanceProcessor,
        media_stream_constraints={
            "video": {
                "width": {"ideal": 1280},
                "height": {"ideal": 720},
                "frameRate": {"ideal": 30, "max": 30}
            },
            "audio": False
        },
        async_processing=True,
    )

    if ctx.video_processor:
        processor = ctx.video_processor
        placeholder = st.empty()

        # Monitor recording state
        connection_timeout = 30  # seconds
        start_time = time.time()
        
        while ctx.state.playing:
            # Check for connection timeout
            if not processor.shared_state.recording_active and not processor.shared_state.process_complete:
                elapsed = time.time() - start_time
                if elapsed > connection_timeout and processor.shared_state.alignment_stable_start == 0:
                    placeholder.warning(
                        "⚠️ Connection established but no face detected yet. "
                        "Make sure your camera is working and you're in frame."
                    )
            
            if processor.shared_state.process_complete:
                placeholder.success("✅ Recording complete! Processing data...")
                return processor.shared_state.output_path

            # Update UI status messages
            state = processor.shared_state
            if state.recording_active:
                elapsed = time.time() - state.recording_start_time
                placeholder.progress(
                    min(elapsed / 15.0, 1.0),
                    text=f"🔴 Recording rPPG segment... {int(15 - elapsed)}s remaining"
                )
            elif state.countdown_active:
                countdown_elapsed = time.time() - state.countdown_start
                remaining = max(0, 3 - int(countdown_elapsed))
                placeholder.warning(f"⏱️ Get ready! Starting in {remaining}...")
            elif state.alignment_stable_start > 0:
                placeholder.info("✅ Face locked! Hold still...")
            
            time.sleep(0.1)
    
    elif not ctx.state.playing:
        st.warning("📷 Click 'START' to begin the live camera session")

    return None


# =========================
# Processing Stub
# =========================

def process_recorded_video(video_path: str):
    """
    Placeholder for video processing.
    Returns the video path for further processing.
    """
    return video_path
