🫀 Wellio – Experimental rPPG Vitals Estimation

Modular remote photoplethysmography system for camera-based heart rate and HRV estimation

Wellio is a research-grade rPPG system that estimates heart rate and heart rate variability (HRV) from standard RGB cameras using signal processing and spectral analysis.
It demonstrates a full-stack architecture combining computer vision, biomedical signal processing, REST APIs, and cloud deployment.

📊 Project Overview

Wellio implements a complete pipeline for camera-based vital signal extraction:

✅ Implemented Features

Heart Rate estimation via Welch Power Spectral Density

HRV metrics (SDNN, pNN50)

Signal preprocessing (detrend + Butterworth bandpass)

Modular rPPG processing engine

Streamlit interactive UI

FastAPI REST backend

Docker-ready deployment

🧪 Experimental / Research Components

Heuristic risk scoring

Short-duration stress inference from HRV

Exploratory blood pressure modeling (not validated)

🏗️ System Architecture
High-Level Deployment Flow
User (Browser)
   ↓
Streamlit UI  OR  React Frontend
   ↓
FastAPI Backend
   ↓
rPPG Processing Engine
   ↓
Supabase (Auth / DB)
   ↓
AWS S3 (Report Storage)

Repository Structure
wellio/
├── rppg_refactored.py        # Core signal processing engine
│   ├── FaceDetector
│   ├── SignalExtractor
│   ├── SignalProcessor
│   ├── VitalsEstimator
│   └── RiskAssessor
├── rppg_streamlit_ui.py      # Streamlit interface
├── rppg_fastapi.py           # REST backend
├── s3_utils.py               # S3 storage integration
├── auth.py                   # Supabase authentication
├── requirements.txt
└── README.md

🔬 Signal Processing Pipeline
Video Input
    ↓
📹 Face Detection (MediaPipe / Haar)
    ↓
🎬 ROI Extraction (Forehead)
    ↓
📊 Temporal Color Signal Extraction (Green channel)
    ↓
🔬 Preprocessing (Detrend → Normalize → Bandpass 0.75–3.0 Hz)
    ↓
❤️ Heart Rate (Welch PSD Peak → BPM)
    ↓
📈 HRV (RR intervals → SDNN, pNN50)
    ↓
📊 Visualization (Signal plots, FFT, HRV histograms)

⚠️ Research Disclaimer

This is an experimental research tool.

Not clinically validated

Not FDA/CE approved

Not intended for medical diagnosis

Not a replacement for ECG, pulse oximeter, or BP monitor

Typical expected performance:

Heart Rate: ±5–10 BPM (visible-light rPPG)

HRV (SDNN): ±20–40% for short recordings

Blood Pressure: Not clinically supported

SpO₂: Not implemented (requires NIR hardware)

Use for:

Signal processing education

Hackathon demonstrations

Research exploration

Do not use for medical decisions.

🚀 Quick Start
Local Streamlit App
pip install -r requirements.txt
streamlit run rppg_streamlit_ui.py


Open: http://localhost:8501

FastAPI Backend
pip install fastapi uvicorn aiofiles
python rppg_fastapi.py


Swagger UI:

http://localhost:8000/docs


Health check:

curl http://localhost:8000/health

Docker
docker build -f Dockerfile.fastapi -t rppg-api .
docker run -p 8000:8000 rppg-api

💻 Programmatic Usage
from rppg_refactored import estimate_vitals_from_video

vitals, filtered_signal, risk = estimate_vitals_from_video(
    video_path="video.mp4",
    use_mediapipe=True
)

print(f"Heart Rate: {vitals.heart_rate_bpm:.1f} BPM")
print(f"SDNN: {vitals.sdnn:.1f} ms")
print(f"Stress Level: {vitals.stress_level:.1f}/10")

🔬 Technical Summary
Heart Rate

Welch PSD used for frequency-domain robustness

HR band: 0.75–3.0 Hz (45–180 BPM)

Peak frequency × 60 → BPM

HRV

Peak detection → RR intervals

Time-domain metrics:

SDNN

pNN50

Short recordings (<2 min) reduce reliability

Blood Pressure

Currently modeled as exploratory heuristic.
Accurate BP estimation requires:

Multi-wavelength signals (Red + IR)

Calibration dataset

ML regression models

Clinical validation study

SpO₂

Not implemented.
RGB cameras cannot reliably estimate oxygen saturation without IR channel.

🧪 Validation

To evaluate performance:

Compare HR vs Apple Watch / Fitbit

Compute absolute and percentage error

Validate SDNN on longer recordings (2–5 minutes recommended)

Expected visible-light rPPG error:

HR: ±5–10 BPM

HRV: Higher variance under motion

🛠️ Troubleshooting

Face not detected

Improve lighting

Reduce occlusion

Move closer to camera

Unrealistic heart rate

Reduce motion

Re-record video

Ensure stable lighting

CORS errors
Update FastAPI CORS middleware:

CORSMiddleware(allow_origins=["https://yourdomain.com"])

🔐 Security Notes

No API keys stored in repository

All credentials loaded via environment variables

Required environment variables:

SUPABASE_URL

SUPABASE_ANON_KEY

SUPABASE_SERVICE_ROLE_KEY (server-side only)

AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY

S3_BUCKET_NAME

Security practices:

.env excluded via .gitignore

Service role keys never exposed client-side

S3 uses restricted IAM permissions

Backend enforces file size limits

Configure CORS and rate limiting for public deployments

📚 References

Verkruysse et al. (2008) – Remote plethysmographic imaging

de Haan & Jeanne (2013) – CHROM algorithm

Wang et al. (2016) – POS algorithm

UBFC-rPPG Dataset

PURE Dataset

🤝 Contributing

Contributions welcome in:

Motion artifact removal (ICA, CHROM+, optical flow)

Bias mitigation across skin tones

Real-time streaming support

Validation benchmarking studies

📄 License

For educational and research use only.
Not approved for clinical use.

See LICENSE for details.

📞 Support

Open GitHub Issues for bugs

Contact author for academic inquiries

Consult medical professionals for health concerns

Wellio is a research platform. Prioritize safety and scientific integrity.
