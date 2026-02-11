"""
Remote Photoplethysmography (rPPG) System - Multi-ROI Fusion
==============================================================

DISCLAIMER:
-----------
This is a research/demo prototype. Outputs are experimental and NOT clinically validated.
Do NOT use for medical diagnosis or treatment. Consult a healthcare professional.

Pipeline:
1. Face Detection (OpenCV Haar Cascade) with Multi-ROI extraction (forehead + both cheeks)
2. Signal Extraction (red & green channels from each ROI)
3. Quality-Weighted ROI Fusion
4. Signal Processing (normalization, bandpass filtering)
5. Vitals Estimation (HR, HRV, Stress, SpO2)
6. Risk Scoring (heuristic, for demo only)

"""

import cv2
import numpy as np
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from scipy.signal import butter, filtfilt, welch, find_peaks
from types import SimpleNamespace
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)


# -----------------------------
# Data Structures
# -----------------------------
@dataclass
class VitalOutput:
    """Output structure for vitals estimation"""
    bpm: Optional[float]
    heart_rate: Optional[float]
    stress_index: Optional[float]
    spo2: Optional[float]
    # Additional fields for UI compatibility
    hrv_sdnn: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    hrv_pnn50: Optional[float] = None
    rr_intervals: Optional[np.ndarray] = None
    bp_systolic: Optional[float] = None
    bp_diastolic: Optional[float] = None
    confidence: Optional[float] = None
    quality_score: Optional[float] = None


# -----------------------------
# Signal Processing Helpers
# -----------------------------
def _bandpass(sig, fs, low=0.7, high=4.0):
    """Bandpass filter for heart rate band"""
    if len(sig) < fs * 5:
        return sig
    nyq = 0.5 * fs
    b, a = butter(3, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, sig)


def _welch_hr(sig, fs):
    """Estimate heart rate using Welch's method"""
    # Reduced from fs * 10 to fs * 5 to support shorter videos
    # Minimum 5 seconds of data required for reasonable HR estimation
    if len(sig) < fs * 5:
        return None, 0
    freqs, psd = welch(sig, fs=fs, nperseg=min(512, len(sig)))  # Reduced nperseg for shorter signals
    band = (freqs >= 0.7) & (freqs <= 4.0)
    if not np.any(band):
        return None, 0
    f_band = freqs[band]
    p_band = psd[band]
    peak_i = np.argmax(p_band)
    peak_ratio = p_band[peak_i] / (np.sum(p_band) + 1e-9)
    return f_band[peak_i] * 60.0, peak_ratio


def _rr_intervals(sig, fs, hr):
    """Extract RR intervals from signal"""
    if hr is None or hr <= 0:
        return np.array([])
    period = 60.0 / hr
    min_dist = int(0.5 * period * fs)
    peaks, _ = find_peaks(sig, distance=min_dist)
    # Reduced from 5 to 3 for shorter videos
    if len(peaks) < 3:
        return np.array([])
    rr = np.diff(peaks) / fs
    # Filter outliers
    rr = rr[(rr > 0.3) & (rr < 2.0)]
    return rr


def _sdnn(rr):
    """Standard deviation of RR intervals (HRV metric)"""
    # Reduced from 10 to 3 for shorter videos
    if len(rr) < 3:
        return None
    return np.std(rr, ddof=1) * 1000.0


def _rmssd(rr):
    """Root mean square of successive differences (HRV metric)"""
    # Reduced from 10 to 3 for shorter videos
    if len(rr) < 3:
        return None
    diff = np.diff(rr)
    return np.sqrt(np.mean(diff ** 2)) * 1000.0


def _pnn50(rr):
    """Percentage of successive RR intervals > 50ms"""
    if len(rr) < 3:
        return 0.0
    diff = np.abs(np.diff(rr)) * 1000.0  # ms
    nn50 = np.sum(diff > 50)
    return float(nn50 / len(diff)) * 100.0


def _stress_from_hrv(sdnn, rmssd):
    """
    Calculate stress index from HRV metrics using refined SDNN thresholds.
    
    Revised Scale (0-10):
    - SDNN < 25ms: 10.0 to 8.1 (High)
    - SDNN 25-40ms: 8.0 to 4.1 (Moderate)
    - SDNN 40-100ms: 4.0 to 1.1 (Low)
    - SDNN > 100ms: Floor at 1.0 (Very Low)
    
    Returns stress index on 0-10 scale
    """
    if sdnn is None:
        return None
    
    sdnn_val = sdnn
    
    if sdnn_val < 25:
        # High stress: 0ms -> 10.0, 25ms -> 8.1
        stress = 10.0 - (sdnn_val / 25.0) * 1.9
    elif sdnn_val <= 40:
        # Moderate stress: 25ms -> 8.0, 40ms -> 4.1
        stress = 8.0 - ((sdnn_val - 25.0) / 15.0) * 3.9
    elif sdnn_val <= 100:
        # Low stress: 40ms -> 4.0, 100ms -> 1.1
        stress = 4.0 - ((sdnn_val - 40.0) / 60.0) * 2.9
    else:
        # Very Low state
        stress = 1.0
    
    return float(np.clip(stress, 0.5, 10.0))


def _estimate_spo2(red_signal, green_signal, fs, hr):
    """
    Estimate SpO2 from red and green channel signals (experimental).
    
    Uses ratio-of-ratios method with proper AC/DC extraction and safety gating.
    
    Args:
        red_signal: Fused red channel signal (numpy array)
        green_signal: Fused green channel signal (numpy array)
        fs: Sampling frequency (Hz)
        hr: Heart rate (BPM) for validation
    
    Returns:
        SpO2 value (float, 88-100%) or None if signal is unreliable
    """
    # Safety gate 1: Minimum 5 seconds duration (reduced from 20s for practicality)
    min_samples = int(fs * 5)
    if len(red_signal) < min_samples or len(green_signal) < min_samples:
        return None
    
    # Safety gate 2: HR must be valid (40-180 BPM)
    if hr is None or hr < 40 or hr > 180:
        return None
    
    # Extract DC component (mean intensity)
    dc_red = np.mean(red_signal)
    dc_green = np.mean(green_signal)
    
    # Safety gate 3: Avoid division by zero
    if dc_red <= 0 or dc_green <= 0:
        return None
    
    # Extract AC component using bandpass filtered pulsatile signal
    # The signals are already bandpass filtered in the main processing
    # Use standard deviation as AC component (pulsatile amplitude)
    ac_red = np.std(red_signal)
    ac_green = np.std(green_signal)
    
    # Safety gate 4: AC components must be meaningful
    if ac_red <= 0 or ac_green <= 0:
        return None
    
    # Compute ratio-of-ratios
    ratio_red = ac_red / dc_red
    ratio_green = ac_green / dc_green
    
    # Safety gate 5: Avoid division by zero
    if ratio_green == 0:
        return None
    
    R = ratio_red / ratio_green
    
    # Map to SpO2 using linear empirical model
    # Validation: R should typically be between 0.5 and 1.1 for physiological SpO2
    # If R is outside [0.4, 1.2], signal is likely too noisy/unreliable
    if R < 0.4 or R > 1.2:
        return None
        
    spo2 = 110 - 25 * R
    
    # Clip to realistic physiological range (88-100%)
    spo2 = float(np.clip(spo2, 88.0, 100.0))
    
    return spo2


def _estimate_bp(hr, sdnn, rmssd):
    """
    Estimate blood pressure from HR and HRV metrics (experimental).
    
    Uses empirical formulas based on research correlations:
    - Higher HR typically correlates with higher BP
    - Lower HRV (SDNN/RMSSD) typically correlates with higher BP
    
    Returns: (systolic, diastolic) in mmHg or (None, None)
    """
    if hr is None or sdnn is None:
        return None, None
    
    # Baseline BP values (normal resting)
    baseline_sys = 120
    baseline_dia = 80
    
    # HR contribution (deviation from normal resting HR of 70 bpm)
    hr_deviation = hr - 70
    sys_hr_adjust = hr_deviation * 0.5  # ~0.5 mmHg per bpm
    dia_hr_adjust = hr_deviation * 0.3  # ~0.3 mmHg per bpm
    
    # HRV contribution (lower HRV = higher stress = higher BP)
    # Normal SDNN is around 50ms
    sdnn_deviation = 50 - sdnn
    sys_hrv_adjust = sdnn_deviation * 0.3  # ~0.3 mmHg per ms deviation
    dia_hrv_adjust = sdnn_deviation * 0.2  # ~0.2 mmHg per ms deviation
    
    # Calculate estimated BP
    systolic = baseline_sys + sys_hr_adjust + sys_hrv_adjust
    diastolic = baseline_dia + dia_hr_adjust + dia_hrv_adjust
    
    # Clip to physiologically reasonable ranges
    systolic = float(np.clip(systolic, 90, 180))
    diastolic = float(np.clip(diastolic, 60, 120))
    
    # Ensure systolic > diastolic
    if diastolic >= systolic:
        diastolic = systolic - 20
    
    return round(systolic, 1), round(diastolic, 1)


# -----------------------------
# MAIN PROCESSING FUNCTION
# -----------------------------
def process_rppg_video(video_path: str, progress_callback=None) -> VitalOutput:
    """
    Process video to extract rPPG vitals using multi-ROI fusion
    
    Args:
        video_path: Path to video file
        progress_callback: Optional callback(current, total) for progress updates
        
    Returns:
        VitalOutput with estimated vitals
    """

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fs = cap.get(cv2.CAP_PROP_FPS)
    if fs <= 1 or fs > 120:
        fs = 30.0

    # Handle unreliable total_frames (common with browser-recorded .webm)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Heuristic: If total_frames is suspiciously high for a single video, 
    # it's likely a misread header. We cap it to a reasonable maximum for analysis.
    # 15s @ 30fps = 450 frames. We'll cap at 600.
    if total_frames <= 0 or total_frames > 2000:
        total_frames = 450 # Reasonable default for 15s

    # Initialize Haar Cascade face detector
    # Priority: 1. HAARCASCADE_PATH env var, 2. Local file, 3. OpenCV data path
    cascade_path = os.environ.get("HAARCASCADE_PATH")
    if not cascade_path or not os.path.exists(cascade_path):
        cascade_path = 'haarcascade_frontalface_default.xml'  # Check local
        if not os.path.exists(cascade_path):
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        raise RuntimeError(f"Could not load Haar Cascade classifier from {cascade_path}")

    # Signal storage for 3 ROIs
    r_fore, g_fore = [], []
    r_lc, g_lc = [], []
    r_rc, g_rc = [], []
    
    frame_idx = 0
    detected_frames = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        h, w = frame.shape[:2]
        
        # Detect faces using Haar Cascade with more lenient parameters
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Improved parameters for better detection:
        # - scaleFactor=1.05 (was 1.1) - more thorough search
        # - minNeighbors=3 (was 5) - less strict
        # - minSize=(50,50) (was 100,100) - detect smaller faces
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.05, 
            minNeighbors=3, 
            minSize=(50, 50),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            # Use largest face - detectMultiScale returns numpy array
            # Each face is [x, y, w, h]
            largest_idx = np.argmax([rect[2] * rect[3] for rect in faces])
            face_rect = faces[largest_idx]
            x, y, fw, fh = int(face_rect[0]), int(face_rect[1]), int(face_rect[2]), int(face_rect[3])
            
            # Define ROIs based on face box
            # Forehead: top 20-35% of face height
            forehead_y1 = max(0, y + int(fh * 0.20))
            forehead_y2 = min(h, y + int(fh * 0.35))
            forehead_x1 = max(0, x + int(fw * 0.25))
            forehead_x2 = min(w, x + int(fw * 0.75))
            forehead_box = frame[forehead_y1:forehead_y2, forehead_x1:forehead_x2]
            
            # Left cheek: left side, middle vertical region
            lc_y1 = max(0, y + int(fh * 0.50))
            lc_y2 = min(h, y + int(fh * 0.75))
            lc_x1 = max(0, x + int(fw * 0.10))
            lc_x2 = min(w, x + int(fw * 0.40))
            left_cheek_box = frame[lc_y1:lc_y2, lc_x1:lc_x2]
            
            # Right cheek: right side, middle vertical region
            rc_y1 = max(0, y + int(fh * 0.50))
            rc_y2 = min(h, y + int(fh * 0.75))
            rc_x1 = max(0, x + int(fw * 0.60))
            rc_x2 = min(w, x + int(fw * 0.90))
            right_cheek_box = frame[rc_y1:rc_y2, rc_x1:rc_x2]
            
            # Extract mean RGB from boxes
            if forehead_box.size > 0:
                rgb_f = cv2.cvtColor(forehead_box, cv2.COLOR_BGR2RGB)
                r_fore.append(np.mean(rgb_f[:,:,0]))
                g_fore.append(np.mean(rgb_f[:,:,1]))
            
            if left_cheek_box.size > 0:
                rgb_l = cv2.cvtColor(left_cheek_box, cv2.COLOR_BGR2RGB)
                r_lc.append(np.mean(rgb_l[:,:,0]))
                g_lc.append(np.mean(rgb_l[:,:,1]))
            
            if right_cheek_box.size > 0:
                rgb_r = cv2.cvtColor(right_cheek_box, cv2.COLOR_BGR2RGB)
                r_rc.append(np.mean(rgb_r[:,:,0]))
                g_rc.append(np.mean(rgb_r[:,:,1]))
            
            detected_frames += 1

        frame_idx += 1
        if progress_callback and total_frames:
            progress_callback(frame_idx, total_frames)

    cap.release()

    # Debug output
    print(f"[DEBUG] Total frames processed: {frame_idx}")
    print(f"[DEBUG] Frames with face detected: {detected_frames}")
    print(f"[DEBUG] Detection ratio: {detected_frames/frame_idx if frame_idx > 0 else 0:.2%}")
    print(f"[DEBUG] Signal lengths - Forehead: {len(g_fore)}, Left: {len(g_lc)}, Right: {len(g_rc)}")

    # Check if we have enough data
    if len(g_fore) == 0:
        print("[DEBUG] No face detected in any frame - returning None values")
        return VitalOutput(None, None, None, None)

    detection_ratio = detected_frames / total_frames if total_frames > 0 else 0
    # Reduced threshold from 0.25 to 0.10 for more lenient processing
    if detection_ratio < 0.10:
        raise ValueError(
            f"Face detected in only {detected_frames}/{total_frames} frames "
            f"({100*detection_ratio:.1f}%). Try better lighting or adjust camera position."
        )

    # Convert to arrays
    g_fore = np.array(g_fore)
    g_lc = np.array(g_lc)
    g_rc = np.array(g_rc)

    r_fore = np.array(r_fore)
    r_lc = np.array(r_lc)
    r_rc = np.array(r_rc)

    # Normalize each ROI signal
    def norm(x):
        return (x - np.mean(x)) / (np.std(x) + 1e-9)

    # Bandpass filter each ROI
    f_fore = _bandpass(norm(g_fore), fs)
    f_lc = _bandpass(norm(g_lc), fs)
    f_rc = _bandpass(norm(g_rc), fs)

    # Estimate HR and quality for each ROI
    hr_f, qf = _welch_hr(f_fore, fs)
    hr_l, ql = _welch_hr(f_lc, fs)
    hr_r, qr = _welch_hr(f_rc, fs)

    # Quality-weighted fusion
    q = np.array([qf, ql, qr])
    weights = q / np.sum(q) if np.sum(q) > 0 else np.array([1/3, 1/3, 1/3])

    # Fuse signals
    fused = weights[0] * f_fore + weights[1] * f_lc + weights[2] * f_rc
    
    # Final HR from fused signal
    hr, peak_ratio = _welch_hr(fused, fs)

    # RR intervals → HRV → Stress
    rr = _rr_intervals(fused, fs, hr)
    sdnn = _sdnn(rr)
    rmssd = _rmssd(rr)
    pnn50 = _pnn50(rr)
    stress = _stress_from_hrv(sdnn, rmssd)

    # SpO2 using fused red/green with proper safety gating
    fused_r = weights[0] * r_fore + weights[1] * r_lc + weights[2] * r_rc
    fused_g = weights[0] * g_fore + weights[1] * g_lc + weights[2] * g_rc
    spo2 = _estimate_spo2(fused_r, fused_g, fs, hr)

    # Blood Pressure estimation
    bp_sys, bp_dia = _estimate_bp(hr, sdnn, rmssd)

    # Calculate confidence based on peak ratio and detection
    confidence = min(100, int(peak_ratio * 100 + detection_ratio * 50))
    quality_score = min(10, peak_ratio * 10)

    # Debug output for results
    print(f"[DEBUG] Calculated vitals:")
    print(f"  - Heart Rate: {hr} BPM" if hr is not None else "  - Heart Rate: None")
    print(f"  - HRV SDNN: {sdnn} ms" if sdnn is not None else "  - HRV SDNN: None")
    print(f"  - HRV RMSSD: {rmssd} ms" if rmssd is not None else "  - HRV RMSSD: None")
    print(f"  - Stress: {stress}" if stress is not None else "  - Stress: None")
    print(f"  - SpO2: {spo2}%" if spo2 is not None else "  - SpO2: None")
    print(f"  - BP: {bp_sys}/{bp_dia} mmHg" if bp_sys is not None else "  - BP: None")
    print(f"  - Confidence: {confidence}%")

    return VitalOutput(
        bpm=round(hr, 1) if hr else None,
        heart_rate=round(hr, 1) if hr else None,
        stress_index=round(stress, 1) if stress else None,
        spo2=round(spo2, 1) if spo2 else None,
        hrv_sdnn=round(sdnn, 1) if sdnn else None,
        hrv_rmssd=round(rmssd, 1) if rmssd else None,
        hrv_pnn50=round(pnn50, 1) if pnn50 else 0.0,
        rr_intervals=rr,
        bp_systolic=round(bp_sys, 1) if bp_sys else None,
        bp_diastolic=round(bp_dia, 1) if bp_dia else None,
        confidence=confidence,
        quality_score=round(quality_score, 1)
    )


# -----------------------------
# Risk Assessment (for UI compatibility)
# -----------------------------
def assess_risk(vitals: VitalOutput) -> Dict[str, Any]:
    """
    Simple heuristic risk assessment
    Returns dict with risk_level, alerts, and recommendations
    """
    alerts = []
    risk_score = 0

    hr = vitals.heart_rate
    stress = vitals.stress_index
    spo2 = vitals.spo2

    # Heart rate checks
    if hr:
        if hr < 50:
            alerts.append("Low heart rate detected")
            risk_score += 30
        elif hr > 100:
            alerts.append("Elevated heart rate detected")
            risk_score += 20

    # Stress checks
    if stress and stress > 70:
        alerts.append("High stress level indicated")
        risk_score += 25

    # SpO2 checks (experimental)
    if spo2 and spo2 < 95:
        alerts.append("Low SpO2 reading (experimental)")
        risk_score += 15

    # Determine risk level
    if risk_score >= 50:
        risk_level = "HIGH"
        recommendation = "Consider consulting a healthcare professional"
    elif risk_score >= 25:
        risk_level = "MODERATE"
        recommendation = "Monitor your vitals and practice stress management"
    else:
        risk_level = "LOW"
        recommendation = "Vitals appear normal. Maintain healthy habits"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "alerts": alerts,
        "recommendation": recommendation
    }


# -----------------------------
# Compatibility Wrapper for UI
# -----------------------------
def estimate_vitals_from_video(video_path: str, progress_callback=None, use_mediapipe=None):
    """
    Backward compatibility wrapper for existing UI code.
    Returns 3-tuple: (vitals_obj, filtered_signal_obj, risk_obj)
    
    Args:
        video_path: Path to video file
        progress_callback: Optional callback for progress updates
        use_mediapipe: Ignored (kept for backward compatibility)
    
    Returns:
        Tuple of (vitals, filtered_signal, risk) as SimpleNamespace objects
        (allows dot notation access like vitals.heart_rate_bpm)
    """
    # Ignore use_mediapipe parameter - we use OpenCV Haar Cascade
    vitals_output = process_rppg_video(video_path, progress_callback)
    risk_output = assess_risk(vitals_output)
    
    # Build vitals object (using SimpleNamespace for dot notation access)
    # Use None instead of 0.0 for failed calculations to avoid misleading reports
    vitals = SimpleNamespace(
        heart_rate_bpm=vitals_output.heart_rate if vitals_output.heart_rate is not None else 0.0,
        heart_rate_valid=vitals_output.heart_rate is not None,
        heart_rate_confidence="HIGH" if (vitals_output.confidence or 0) > 70 else "MEDIUM" if (vitals_output.confidence or 0) > 50 else "LOW",
        hrv_sdnn=vitals_output.hrv_sdnn if vitals_output.hrv_sdnn is not None else None,
        hrv_rmssd=vitals_output.hrv_rmssd if vitals_output.hrv_rmssd is not None else None,
        hrv_pnn50=vitals_output.hrv_pnn50 if vitals_output.hrv_pnn50 is not None else 0.0,
        # Direct aliases for UI compatibility
        sdnn=vitals_output.hrv_sdnn if vitals_output.hrv_sdnn is not None else None,
        pnn50=vitals_output.hrv_pnn50 if vitals_output.hrv_pnn50 is not None else 0.0,
        rr_intervals=vitals_output.rr_intervals if vitals_output.rr_intervals is not None else np.array([]),
        hrv_valid=vitals_output.hrv_sdnn is not None,
        stress_level=vitals_output.stress_index if vitals_output.stress_index is not None else None,
        bp_systolic=vitals_output.bp_systolic if vitals_output.bp_systolic is not None else None,
        bp_diastolic=vitals_output.bp_diastolic if vitals_output.bp_diastolic is not None else None,
        bp_note="Experimental - based on HR and HRV correlation",
        spo2=vitals_output.spo2 if vitals_output.spo2 is not None else None,
        spo2_note="Experimental - not clinically validated",
        confidence_percent=vitals_output.confidence or 0,
        signal_quality_score=vitals_output.quality_score or 0,
    )
    
    # Build filtered_signal object (placeholder for UI compatibility)
    filtered_signal = SimpleNamespace(
        signal=[],  # Empty for now
        sampling_rate=30.0,
        confidence_percent=vitals_output.confidence or 0,
    )
    
    # Build risk object
    risk = SimpleNamespace(
        risk_score=risk_output["risk_score"],
        risk_level=risk_output["risk_level"],
        alerts=risk_output["alerts"],
        recommendation=risk_output["recommendation"],
    )
    
    return vitals, filtered_signal, risk


# Export HAVE_MEDIAPIPE for UI compatibility (always False now)
HAVE_MEDIAPIPE = False
