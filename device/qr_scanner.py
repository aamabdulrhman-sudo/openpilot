#!/usr/bin/env python3
"""
FreePilots QR Code Scanner for Comma Devices
Utilizes device camera / OpenCV to scan server pairing QR code
"""

import sys
import json
import cv2

def scan_qr_from_camera():
    print("Opening camera to scan FreePilots QR Code...")
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None

    print("Point your phone screen containing the FreePilots QR code to the camera.")
    
    timeout = 30 # seconds
    start_time = cv2.getTickCount()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        data, bbox, _ = detector.detectAndDecode(frame)
        if data:
            print("\nQR Code Detected!")
            try:
                parsed = json.loads(data)
                print(f"Server URL: {parsed.get('server')}")
                cap.release()
                return parsed
            except Exception:
                print(f"Raw data: {data}")
                cap.release()
                return data

        # Check timeout
        elapsed = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
        if elapsed > timeout:
            print("Scan timed out.")
            break

    cap.release()
    return None

if __name__ == "__main__":
    result = scan_qr_from_camera()
    if result and isinstance(result, dict):
        with open("/data/freepilots.json", "w") as f:
            json.dump(result, f)
        print("Saved configuration to /data/freepilots.json")
