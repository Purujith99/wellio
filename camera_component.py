import streamlit.components.v1 as components
import streamlit as st
import base64
import os
import tempfile

def camera_component(duration_seconds=15):
    """
    A custom Streamlit component that uses the browser's MediaRecorder API 
    to record video and return it as a base64 string.
    """
    
    html_code = f"""
    <div id="camera-container" style="position: relative; width: 100%; max-width: 640px; margin: auto; font-family: sans-serif; overflow: hidden; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <video id="webcam" autoplay playsinline muted style="width: 100%; display: block; background: #000;"></video>
        
        <!-- Face Guide Overlay -->
        <div id="guide" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 50%; height: 70%; border: 3px dashed rgba(255, 255, 255, 0.5); border-radius: 50% / 50%; pointer-events: none; transition: border-color 0.3s;"></div>
        
        <!-- Status Indicator -->
        <div id="status" style="position: absolute; top: 20px; left: 0; right: 0; text-align: center; color: white; background: rgba(0,0,0,0.5); padding: 5px; font-weight: bold;">Allow camera access to start</div>
        
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
                        frameRate: {{ ideal: 30 }}
                    }}, 
                    audio: false 
                }});
                video.srcObject = stream;
                status.innerText = "Position your face in the guide";
                recordBtn.disabled = false;
                recordBtn.style.opacity = "1";
                btnText.innerText = "Start Recording";
                
                // Show guide as active
                guide.style.borderColor = "rgba(0, 255, 0, 0.7)";
            }} catch (err) {{
                status.innerText = "Error: " + err.message;
                status.style.background = "rgba(255, 0, 0, 0.5)";
            }}
        }}

        function startRecording() {{
            recordedChunks = [];
            mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'video/webm' }});
            
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
                    const base64data = reader.result;
                    // Send message to Streamlit
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: base64data
                    }}, '*');
                }};
                
                // Cleanup stream
                stream.getTracks().forEach(track => track.stop());
            }};
            
            mediaRecorder.start();
            status.innerText = "Recording rPPG data... Stay still";
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
                status.innerText = "Sending to server...";
            }}
        }}

        recordBtn.addEventListener('click', startRecording);
        initCamera();

        // Communication boilerplate for Streamlit components
        function sendMessageToStreamlit(value) {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: value
            }}, '*');
        }}
    </script>
    """
    
    # Render component
    # We use a unique key per session or intent to reset the component properly
    component_data = components.html(html_code, height=500)
    return component_data

def save_camera_video(base64_data):
    """Decodes and saves base64 webm data to a temporary file."""
    if not base64_data or not isinstance(base64_data, str):
        return None
        
    try:
        # Data format: "data:video/webm;base64,..."
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        video_bytes = base64.b64decode(base64_data)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(video_bytes)
            return tmp.name
    except Exception as e:
        st.error(f"Error saving video: {e}")
        return None
