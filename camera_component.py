import streamlit.components.v1 as components
import streamlit as st
import base64
import os
import tempfile

# Force a clean path for the component build
_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "camera_record_component",
        url="http://localhost:3001",
    )
else:
    # Use a dummy component that renders our HTML
    # In a real setup, we'd have a separate frontend folder
    # But we can trick declare_component by pointing it to an empty folder 
    # and then manually serving the HTML for simplicity in this script-based setup.
    # Actually, the most reliable way for a single file is to use a trick:
    pass

def camera_component(duration_seconds=15, key=None):
    """
    A custom Streamlit component that uses the browser's MediaRecorder API 
    to record video and return it as a base64 string.
    """
    
    # We use a unique key to ensure the component is fresh
    if key is None:
        key = "camera_record_v1"

    html_code = f"""
    <div id="camera-container" style="position: relative; width: 100%; max-width: 640px; margin: auto; font-family: sans-serif; overflow: hidden; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <video id="webcam" autoplay playsinline muted style="width: 100%; display: block; background: #000;"></video>
        
        <!-- Face Guide Overlay -->
        <div id="guide" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 50%; height: 70%; border: 3px dashed rgba(255, 255, 255, 0.5); border-radius: 50% / 50%; pointer-events: none; transition: border-color 0.3s;"></div>
        
        <!-- Status Indicator -->
        <div id="status" style="position: absolute; top: 20px; left: 0; right: 0; text-align: center; color: white; background: rgba(0,0,0,0.5); padding: 5px; font-weight: bold; font-size: 14px;">Allow camera access to start</div>
        
        <!-- Controls Overlay -->
        <div id="controls" style="position: absolute; bottom: 0; left: 0; right: 0; padding: 20px; background: linear-gradient(transparent, rgba(0,0,0,0.7)); text-align: center;">
            <button id="record-btn" disabled style="padding: 12px 30px; font-size: 16px; font-weight: bold; border-radius: 50px; border: none; background: #ff4b4b; color: white; cursor: pointer; transition: all 0.2s; opacity: 0.6;">
                <span id="btn-text">Initializing...</span>
            </button>
            <div id="progress-container" style="width: 100%; height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px; margin-top: 15px; display: none;">
                <div id="progress-bar" style="width: 0%; height: 100%; background: #ff4b4b; border-radius: 3px; transition: width 0.1s linear;"></div>
            </div>
        </div>
    </div>

    <script>
        // --- Streamlit Lifecycle Helper ---
        function onStreamlitMessage(event) {{
            if (event.data.type === "streamlit:render") {{
                // Handle initial render or updates
            }}
        }}

        function setComponentValue(value) {{
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                value: value
            }}, "*");
        }}

        window.addEventListener("message", onStreamlitMessage);

        const video = document.getElementById('webcam');
        const recordBtn = document.getElementById('record-btn');
        const btnText = document.getElementById('btn-text');
        const status = document.getElementById('status');
        const guide = document.getElementById('guide');
        const progressBar = document.getElementById('progress-bar');
        const progressContainer = document.getElementById('progress-container');
        
        let mediaRecorder;
        let recordedChunks = [];
        let stream;
        let timer;
        const duration = {duration_seconds} * 1000; 

        // Initialize Camera
        async function initCamera() {{
            try {{
                stream = await navigator.mediaDevices.getUserMedia({{ 
                    video: {{ 
                        width: {{ ideal: 1280 }},
                        height: {{ ideal: 720 }},
                        frameRate: {{ ideal: 30 }},
                        facingMode: "user"
                    }}, 
                    audio: false 
                }});
                video.srcObject = stream;
                status.innerText = "Position your face in the guide";
                recordBtn.disabled = false;
                recordBtn.style.opacity = "1";
                btnText.innerText = "Start Recording";
                guide.style.borderColor = "rgba(0, 255, 0, 0.7)";
                
                // Adjust iframe height
                sendFrameHeight();
            }} catch (err) {{
                status.innerText = "Error: " + err.message;
                status.style.background = "rgba(255, 0, 0, 0.5)";
            }}
        }}

        function sendFrameHeight() {{
             window.parent.postMessage({{
                type: "streamlit:setFrameHeight",
                height: document.body.scrollHeight
            }}, "*");
        }}

        function startRecording() {{
            recordedChunks = [];
            
            // Check supported types
            let options = {{ mimeType: 'video/webm;codecs=vp8' }};
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {{
                options = {{ mimeType: 'video/webm' }};
            }}
            
            mediaRecorder = new MediaRecorder(stream, options);
            
            mediaRecorder.ondataavailable = (e) => {{
                if (e.data.size > 0) {{
                    recordedChunks.push(e.data);
                }}
            }};
            
            mediaRecorder.onstop = () => {{
                const blob = new Blob(recordedChunks, {{ type: 'video/webm' }});
                const reader = new FileReader();
                reader.readAsDataURL(blob);
                reader.onloadend = () => {{
                    setComponentValue(reader.result);
                }};
                
                // Cleanup stream
                stream.getTracks().forEach(track => track.stop());
            }};
            
            mediaRecorder.start();
            status.innerText = "Recording... Stay still";
            status.style.color = "#ff4b4b";
            recordBtn.disabled = true;
            recordBtn.style.opacity = "0.5";
            btnText.innerText = "Recording...";
            
            // Progress Bar Logic
            progressContainer.style.display = "block";
            let startTime = Date.now();
            
            timer = setInterval(() => {{
                let elapsed = Date.now() - startTime;
                let percent = (elapsed / duration) * 100;
                progressBar.style.width = Math.min(percent, 100) + "%";
                
                if (elapsed >= duration) {{
                    stopRecording();
                }}
            }}, 100);
        }}

        function stopRecording() {{
            clearInterval(timer);
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                mediaRecorder.stop();
                status.innerText = "Processing Pulse... Please wait";
                status.style.color = "white";
            }}
        }}

        recordBtn.addEventListener('click', startRecording);
        initCamera();

    </script>
    <style>
        body {{ margin: 0; padding: 0; background-color: transparent; overflow: hidden; }}
    </style>
    """
    
    # We use st.components.v1.html for simplicity in a single-file environment,
    # but we MUST handle the return value correctly.
    # Actually, for components.html to return a value, we can't.
    # We NEED declare_component.
    
    # Let's use the local 'build' trick.
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "camera_component_build")
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
        
    with open(os.path.join(build_dir, "index.html"), "w") as f:
        f.write(html_code)
        
    camera_func = components.declare_component("camera_record_component", path=build_dir)
    return camera_func(duration_seconds=duration_seconds, key=key)

def save_camera_video(base64_data):
    """Decodes and saves base64 webm data to a temporary file."""
    if not base64_data or not isinstance(base64_data, str):
        return None
        
    try:
        # Data format: "data:video/webm;base64,..."
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        video_bytes = base64.b64decode(base64_data)
        
        # Save to temp file with fixed name for predictable processing
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"wellio_record_{base64.b64encode(os.urandom(4)).decode()}.webm")
        
        with open(tmp_path, "wb") as f:
            f.write(video_bytes)
            
        return tmp_path
    except Exception as e:
        st.error(f"Error saving video: {e}")
        return None
