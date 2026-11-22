import os
import shutil
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess

STORAGE_DIR = os.getenv("STORAGE_DIR", "/data")
Path(STORAGE_DIR).mkdir(parents=True, exist_ok=True)

def get_storage_stats() -> Dict[str, Any]:
    total, used, free = shutil.disk_usage(STORAGE_DIR)
    
    # Count routes and video files
    routes = [d for d in Path(STORAGE_DIR).iterdir() if d.is_dir() and not d.name.startswith(".")]
    video_count = len(list(Path(STORAGE_DIR).rglob("*.hevc"))) + len(list(Path(STORAGE_DIR).rglob("*.mp4")))
    
    return {
        "total_gb": round(total / (1024**3), 2),
        "used_gb": round(used / (1024**3), 2),
        "free_gb": round(free / (1024**3), 2),
        "routes_count": len(routes),
        "videos_count": video_count
    }

def list_drives() -> List[Dict[str, Any]]:
    drives = []
    base_path = Path(STORAGE_DIR)
    if not base_path.exists():
        return []
        
    for route_dir in sorted(base_path.iterdir(), reverse=True):
        if not route_dir.is_dir() or route_dir.name.startswith("."):
            continue
            
        segments = []
        route_size = 0
        for seg_dir in sorted(route_dir.iterdir()):
            if not seg_dir.is_dir():
                continue
            seg_files = []
            seg_size = 0
            for f in seg_dir.iterdir():
                if f.is_file():
                    size = f.stat().st_size
                    seg_size += size
                    seg_files.append({
                        "name": f.name,
                        "size_mb": round(size / (1024**2), 2),
                        "type": f.suffix.replace(".", "")
                    })
            route_size += seg_size
            segments.append({
                "segment": seg_dir.name,
                "files": seg_files,
                "size_mb": round(seg_size / (1024**2), 2)
            })
            
        drives.append({
            "route_id": route_dir.name,
            "created_at": route_dir.stat().st_ctime,
            "segments_count": len(segments),
            "size_mb": round(route_size / (1024**2), 2),
            "segments": segments
        })
    return drives

def save_uploaded_file(route_id: str, segment_num: str, filename: str, content: bytes) -> str:
    target_dir = Path(STORAGE_DIR) / route_id / segment_num
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    with open(target_file, "wb") as f:
        f.write(content)
    return str(target_file)
