import os
import uuid
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Portada Movilab")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "data.db"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT,
            repo_url TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_session(request: Request) -> bool:
    session = request.cookies.get("session")
    if not session:
        return False
    secret = os.getenv("SECRET_KEY", "default-secret")
    expected = hash_password(f"{os.getenv('USER', 'admin')}:{secret}")
    return session == expected


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_image(filename: str, size: int) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return "Formato no soportado. Solo PNG y JPG."
    if size > MAX_FILE_SIZE:
        return "Imagen demasiado grande. Máximo 5MB."
    return None


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "projects": projects})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if verify_session(request):
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    valid_user = os.getenv("USER", "admin")
    valid_pass = os.getenv("PASSWORD", "admin")

    if username == valid_user and password == valid_pass:
        secret = os.getenv("SECRET_KEY", "default-secret")
        session_value = hash_password(f"{valid_user}:{secret}")
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie(
            key="session",
            value=session_value,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
        )
        return response

    return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario o contraseña incorrectos"})


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "projects": projects})


@app.post("/projects")
async def create_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    url: str = Form(""),
    repo_url: str = Form(""),
    image: UploadFile = File(None),
):
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)

    if not title.strip():
        return RedirectResponse(url="/admin", status_code=302)

    image_url = None
    if image and image.filename:
        contents = await image.read()
        error = validate_image(image.filename, len(contents))
        if error:
            return RedirectResponse(url="/admin", status_code=302)

        ext = Path(image.filename).suffix.lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = UPLOADS_DIR / filename
        filepath.write_bytes(contents)
        image_url = filename

    conn = get_db()
    conn.execute(
        "INSERT INTO projects (title, description, url, repo_url, image_url) VALUES (?, ?, ?, ?, ?)",
        (title.strip(), description.strip(), url.strip() or None, repo_url.strip() or None, image_url),
    )
    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin", status_code=302)


@app.post("/projects/{project_id}/edit")
async def edit_project(
    request: Request,
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    url: str = Form(""),
    repo_url: str = Form(""),
    image: UploadFile = File(None),
):
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

    if not project:
        conn.close()
        return RedirectResponse(url="/admin", status_code=302)

    image_url = project["image_url"]

    if image and image.filename:
        contents = await image.read()
        error = validate_image(image.filename, len(contents))
        if error:
            conn.close()
            return RedirectResponse(url="/admin", status_code=302)

        if project["image_url"]:
            old_path = UPLOADS_DIR / project["image_url"]
            if old_path.exists():
                old_path.unlink()

        ext = Path(image.filename).suffix.lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = UPLOADS_DIR / filename
        filepath.write_bytes(contents)
        image_url = filename

    conn.execute(
        "UPDATE projects SET title = ?, description = ?, url = ?, repo_url = ?, image_url = ? WHERE id = ?",
        (title.strip(), description.strip(), url.strip() or None, repo_url.strip() or None, image_url, project_id),
    )
    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin", status_code=302)


@app.post("/projects/{project_id}/delete")
async def delete_project(request: Request, project_id: int):
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

    if project and project["image_url"]:
        image_path = UPLOADS_DIR / project["image_url"]
        if image_path.exists():
            image_path.unlink()

    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin", status_code=302)


@app.get("/uploads/{filename}")
async def get_upload(filename: str):
    filepath = UPLOADS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)
