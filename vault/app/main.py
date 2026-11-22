import os
import io
import qrcode
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from .storage import get_storage_stats, list_drives, save_uploaded_file, STORAGE_DIR
from .auth import is_setup_completed, create_admin_user, verify_credentials, get_session_secret

app = FastAPI(
    title="FreePilots Private Vault",
    description="Self-hosted dashcam and drive archive server for Sunnypilot and Comma 4",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VAULT_TOKEN = os.getenv("VAULT_TOKEN", "freepilot_secret_token_2026")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8107")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def is_authenticated(request: Request) -> bool:
    session = request.cookies.get("freepilots_session")
    if not session:
        return False
    return session == get_session_secret()

def verify_token(x_vault_token: str = Header(None)):
    """Device authentication for Comma uploader"""
    if VAULT_TOKEN and x_vault_token != VAULT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Vault-Token header")
    return True

# ----------------- Auth & Setup Routes -----------------

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    if is_setup_completed():
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("setup.html", {"request": request, "error": None})

@app.post("/setup")
async def do_setup(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    if is_setup_completed():
        return RedirectResponse(url="/login", status_code=302)
    
    if len(password) < 6:
        return templates.TemplateResponse("setup.html", {"request": request, "error": "كلمة المرور يجب أن تكون 6 خانات على الأقل / Password must be at least 6 characters"})
        
    if password != confirm_password:
        return templates.TemplateResponse("setup.html", {"request": request, "error": "كلمات المرور غير متطابقة / Passwords do not match"})

    user_data = create_admin_user(username, password)
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.set_cookie(
        key="freepilots_session",
        value=user_data["session_secret"],
        httponly=True,
        samesite="lax",
        max_age=60*60*24*30 # 30 days
    )
    return redirect

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if not is_setup_completed():
        return RedirectResponse(url="/setup", status_code=302)
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def do_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if not is_setup_completed():
        return RedirectResponse(url="/setup", status_code=302)
        
    if verify_credentials(username, password):
        redirect = RedirectResponse(url="/", status_code=302)
        redirect.set_cookie(
            key="freepilots_session",
            value=get_session_secret(),
            httponly=True,
            samesite="lax",
            max_age=60*60*24*30
        )
        return redirect
    return templates.TemplateResponse("login.html", {"request": request, "error": "اسم المستخدم أو كلمة المرور غير صحيحة / Invalid username or password"})

@app.get("/logout")
async def do_logout():
    redirect = RedirectResponse(url="/login", status_code=302)
    redirect.delete_cookie("freepilots_session")
    return redirect

# ----------------- Dashboard & Web Routes -----------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_setup_completed():
        return RedirectResponse(url="/setup", status_code=302)
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
        
    stats = get_storage_stats()
    drives = list_drives()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "drives": drives,
        "public_url": PUBLIC_URL,
        "token": VAULT_TOKEN
    })

@app.get("/api/stats")
async def api_stats(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_storage_stats()

@app.get("/api/drives")
async def api_drives(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return list_drives()

@app.get("/api/qrcode")
async def generate_qr(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    payload = f'{{"server":"{PUBLIC_URL}","token":"{VAULT_TOKEN}"}}'
    qr = qrcode.QRCode(version=1, box_size=10, border=3)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00E5FF", back_color="#0F172A")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# ----------------- Device Upload Endpoints (Comma Device) -----------------

@app.put("/api/upload_raw")
async def upload_raw_stream(
    request: Request,
    key: str,
    dongle_id: Optional[str] = None,
    authorized: bool = Depends(verify_token)
):
    """Direct streaming upload endpoint called by Sunnypilot's uploader.py"""
    clean_key = key.split("|")[-1]
    parts = clean_key.split("/")
    filename = parts[-1]
    route_seg = parts[0] if len(parts) > 1 else "misc"
    
    if "--" in route_seg:
        rparts = route_seg.split("--")
        seg = rparts[-1]
        route_name = "--".join(rparts[:-1])
    else:
        route_name = route_seg
        seg = "0"
        
    target_dir = Path(STORAGE_DIR) / route_name / seg
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    with open(target_file, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
            
    return {"status": "success", "file": str(target_file), "size": target_file.stat().st_size}

@app.post("/api/upload")
async def upload_segment_file(
    route_id: str = Form(...),
    segment_num: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    authorized: bool = Depends(verify_token)
):
    content = await file.read()
    saved_path = save_uploaded_file(route_id, segment_num, filename, content)
    return {"status": "success", "path": saved_path}

@app.get("/api/video/{route_id}/{segment_num}/{filename}")
async def stream_video(route_id: str, segment_num: str, filename: str, request: Request):
    if not is_authenticated(request):
        # allow if token is present
        token = request.query_params.get("token")
        if token != VAULT_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

    file_path = Path(STORAGE_DIR) / route_id / segment_num / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
        
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    start = 0
    end = file_size - 1
    
    if range_header:
        parts = range_header.replace("bytes=", "").split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

    chunk_size = (end - start) + 1
    
    def file_iterator(file_path: Path, offset: int, length: int):
        with open(file_path, "rb") as f:
            f.seek(offset)
            remaining = length
            while remaining > 0:
                read_bytes = min(remaining, 64 * 1024)
                data = f.read(read_bytes)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4" if filename.endswith(".mp4") else "application/octet-stream",
    }
    return StreamingResponse(file_iterator(file_path, start, chunk_size), status_code=206 if range_header else 200, headers=headers)
