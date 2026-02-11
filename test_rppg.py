"""
Quick test script to verify rPPG backend is working
"""
import sys
sys.path.insert(0, r'c:\IMPORTANT FILES\codes\wellio')

from rppg_refactored import process_rppg_video

# Test with a video file
video_path = input("Enter path to test video file: ").strip().strip('"').strip("'")

print(f"\n[INFO] Processing: {video_path}")
print("="*60)
print("Testing rPPG Backend")
print("="*60 + "\n")

try:
    vitals = process_rppg_video(video_path)
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"Heart Rate: {vitals.heart_rate} BPM")
    print(f"HRV SDNN: {vitals.hrv_sdnn} ms")
    print(f"HRV RMSSD: {vitals.hrv_rmssd} ms")
    print(f"Stress Index: {vitals.stress_index}")
    print(f"SpO2: {vitals.spo2}%")
    print(f"Confidence: {vitals.confidence}%")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
