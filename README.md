🫀 Wellio – Camera-Based Heart Rate & HRV Estimation

Wellio is an experimental remote photoplethysmography (rPPG) system that estimates heart rate and heart rate variability using nothing more than a standard RGB camera.

It combines computer vision, signal processing, and modern web architecture to explore how far we can push camera-based vital sign estimation — responsibly.

This is a research and hackathon project, not a medical device.

🌍 Why This Project Exists

Access to vital sign monitoring isn’t always convenient or affordable.

What if a simple camera could provide meaningful physiological insights?

Wellio explores that idea — carefully, transparently, and with full acknowledgment of its limitations.

🚀 What Wellio Can Do

Estimate Heart Rate (HR)

Compute HRV metrics (SDNN, pNN50)

Extract physiological signals from facial video

Visualize waveform and spectral plots

Run locally (Streamlit)

Expose a REST API (FastAPI)

Deploy via Docker

Integrate authentication (Supabase) and storage (AWS S3)

🏗 System Architecture

Wellio is designed as a modular, scalable system.

High-Level Infrastructure Flow
User (Browser)
        ↓
Streamlit UI  OR  React Frontend
        ↓
FastAPI Backend
        ↓
rPPG Processing Engine
        ↓
Supabase (Auth + Database)
        ↓
AWS S3 (Report Storage)

Architecture Philosophy

Clear separation between frontend and backend

Modular signal processing core

Cloud-ready deployment

Environment-based credential management

Scalable storage integration

🔬 Signal Processing Pipeline

This is where the physiological estimation happens.

Video Input
    ↓
Face Detection (MediaPipe / Haar)
    ↓
Forehead ROI Isolation
    ↓
Green Channel Signal Extraction
    ↓
Preprocessing:
    - Interpolation
    - Detrending
    - Normalization
    - Bandpass Filtering (0.75–3.0 Hz)
    ↓
Welch PSD → Dominant Frequency
    ↓
Heart Rate (BPM)
    ↓
Peak Detection → RR Intervals
    ↓
HRV (SDNN, pNN50)
    ↓
Visualization & Risk Output


Two layers exist:

System layer → Infrastructure & deployment

Signal layer → Physiological computation

🔬 How Heart Rate Is Estimated

Uses the green channel due to hemoglobin absorption properties

Applies:

Detrending

Normalization

Butterworth bandpass filtering

Welch Power Spectral Density identifies dominant frequency

Frequency × 60 → BPM

Expected visible-light accuracy:

±5–10 BPM under stable lighting

📈 HRV in This Project

RR intervals derived from peak detection

Metrics:

SDNN

pNN50

Short recordings (<2 minutes) reduce reliability

Intended for research exploration, not clinical interpretation

🧪 Experimental Components

Some features are exploratory:

Heuristic risk scoring

Stress inference from short HRV recordings

Blood pressure modeling (concept only)

These are clearly marked and not validated.

SpO₂ is not implemented (RGB cameras are insufficient for reliable oxygen saturation).

⚠ Important Disclaimer

This project:

Is not clinically validated

Is not FDA/CE approved

Is not intended for diagnosis

Does not replace ECG, pulse oximeters, or BP monitors

Use it for:

Learning signal processing

Hackathon demonstrations

Research exploration

Do not use it for medical decisions.

🚀 Getting Started
▶ Local (Streamlit)
pip install -r requirements.txt
streamlit run rppg_streamlit_ui.py


Open:
http://localhost:8501

▶ Backend (FastAPI)
pip install fastapi uvicorn aiofiles
python rppg_fastapi.py


Swagger UI:
http://localhost:8000/docs

▶ Docker Deployment
docker build -f Dockerfile.fastapi -t rppg-api .
docker run -p 8000:8000 rppg-api

🔐 Security & Deployment Notes

Wellio follows basic production security principles:

No API keys stored in repository

All secrets loaded via environment variables

.env excluded in .gitignore

Service-role keys never exposed to frontend

Restricted IAM permissions for S3

File size validation on backend

Public deployments should enable:

CORS restrictions

Rate limiting

Required environment variables:

SUPABASE_URL

SUPABASE_ANON_KEY

SUPABASE_SERVICE_ROLE_KEY (backend only)

AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY

S3_BUCKET_NAME

🧪 Validation Strategy

To evaluate accuracy:

Compare HR with Apple Watch or Fitbit

Compute absolute & percentage error

Use 2–5 minute recordings for HRV

Known research challenges:

Motion artifacts

Lighting variability

Skin tone bias

Camera sensor differences

📂 Repository Structure
wellio/
├── rppg_refactored.py        # Core signal engine
│   ├── FaceDetector
│   ├── SignalExtractor
│   ├── SignalProcessor
│   ├── VitalsEstimator
│   └── RiskAssessor
├── rppg_streamlit_ui.py      # UI
├── rppg_fastapi.py           # Backend API
├── s3_utils.py               # S3 integration
├── auth.py                   # Supabase authentication
├── requirements.txt
└── README.md

🤝 Contributing

Potential improvements:

Motion robustness (ICA, CHROM+, optical flow)

Bias mitigation across skin tones

Real-time streaming

Clinical benchmarking studies

📄 License

For educational and research use only.
Not approved for clinical use.

Final Note

Wellio is an exploration — not a medical product.

It is built with curiosity, engineering rigor, and respect for scientific boundaries.

Use responsibly.
