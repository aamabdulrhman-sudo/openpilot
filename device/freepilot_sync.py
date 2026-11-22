#!/usr/bin/env python3
"""
FreePilots Comma Sync Client
Runs directly on the Comma device (Comma 3/3X/4) running Sunnypilot / AGNOS.
Watches /data/media/0/realdata and streams drive recordings to your private FreePilots Vault.
"""

import os
import sys
import time
import glob
import json
import logging
from pathlib import Path
import urllib.request
import urllib.parse
import mimetypes

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [FreePilots]: %(message)s'
)

CONFIG_PATH = Path("/data/freepilots.json")
REALDATA_PATH = Path("/data/media/0/realdata")
STATE_PATH = Path("/data/freepilots_synced.json")

def load_config():
    if not CONFIG_PATH.exists():
        logging.error("Configuration file /data/freepilots.json not found! Run install.sh first.")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def load_synced_state():
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_synced_state(synced_files):
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(list(synced_files), f)
    except Exception as e:
        logging.error(f"Failed to save state: {e}")

def upload_file(server_url, token, route_id, segment_num, file_path):
    url = f"{server_url.rstrip('/')}/api/upload"
    boundary = "----WebKitFormBoundaryFreePilots7MA4YWxkTrZu0gW"
    
    file_name = file_path.name
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Build multipart/form-data
    body = bytearray()
    
    # route_id
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="route_id"\r\n\r\n{route_id}\r\n'.encode())
    
    # segment_num
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="segment_num"\r\n\r\n{segment_num}\r\n'.encode())
    
    # filename
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="filename"\r\n\r\n{file_name}\r\n'.encode())
    
    # file payload
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode())
    body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
    body.extend(file_bytes)
    body.extend(b'\r\n')
    
    body.extend(f"--{boundary}--\r\n".encode())
    
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Vault-Token": token,
            "User-Agent": "FreePilots-CommaClient/1.0"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status == 200:
            return True
    return False

def sync_loop():
    config = load_config()
    server_url = config.get("server")
    token = config.get("token")
    delete_after_upload = config.get("delete_after_upload", False)
    
    logging.info(f"FreePilots sync daemon active. Vault target: {server_url}")
    synced_files = load_synced_state()

    while True:
        try:
            if not REALDATA_PATH.exists():
                time.sleep(10)
                continue

            for route_dir in sorted(REALDATA_PATH.iterdir()):
                if not route_dir.is_dir() or route_dir.name.startswith("."):
                    continue
                
                route_name = route_dir.name
                
                # Check segment files
                for seg_path in sorted(route_dir.iterdir()):
                    if not seg_path.is_file():
                        continue
                    
                    # Target files: fcamera, dcamera, ecamera, qcamera, rlog, qlog
                    ext = seg_path.suffix.lower()
                    if ext not in [".hevc", ".ts", ".zst", ".mp4"]:
                        continue

                    # Segment naming convention in openpilot: e.g. fcamera.hevc or segment number folders
                    segment_num = "0"
                    if "--" in route_name:
                        parts = route_name.split("--")
                        if len(parts) > 2:
                            segment_num = parts[-1]

                    file_key = f"{route_name}/{seg_path.name}"
                    if file_key in synced_files:
                        continue

                    # Ensure file is not currently actively being written
                    initial_size = seg_path.stat().st_size
                    time.sleep(0.5)
                    if seg_path.exists() and seg_path.stat().st_size != initial_size:
                        continue # File is still being recorded by loggerd

                    logging.info(f"Syncing: {file_key} ({round(initial_size/(1024*1024), 2)} MB)...")
                    try:
                        success = upload_file(server_url, token, route_name, segment_num, seg_path)
                        if success:
                            synced_files.add(file_key)
                            save_synced_state(synced_files)
                            logging.info(f"Successfully uploaded: {file_key}")
                            
                            if delete_after_upload:
                                seg_path.unlink()
                                logging.info(f"Cleaned up local file: {seg_path}")
                    except Exception as upload_err:
                        logging.warning(f"Upload failed for {file_key}: {upload_err}")

        except Exception as e:
            logging.error(f"Sync loop error: {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    sync_loop()
