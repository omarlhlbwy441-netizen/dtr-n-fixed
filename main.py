from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="DTR-N", version="1.2.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Serve static files if directory exists
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    file_path = os.path.join(BASE_DIR, "thank-you-egypt.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>DTR-N System</h1>")

@app.get("/thank-you-egypt.html", response_class=HTMLResponse)
async def thank_you_page():
    file_path = os.path.join(BASE_DIR, "thank-you-egypt.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Thank You Egypt</h1>")

@app.get("/app.html", response_class=HTMLResponse)
async def app_page():
    file_path = os.path.join(BASE_DIR, "app.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>App Page</h1>")

@app.get("/app", response_class=HTMLResponse)
async def app_redirect():
    return await app_page()

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    file_path = os.path.join(BASE_DIR, "app.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Login Page</h1>")

@app.get("/login.html", response_class=HTMLResponse)
async def login_html_page():
    return await login_page()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    file_path = os.path.join(BASE_DIR, "session-dashboard.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard</h1>")

@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard_html_page():
    return await dashboard_page()

@app.get("/sessions", response_class=HTMLResponse)
async def sessions_page():
    file_path = os.path.join(BASE_DIR, "session-dashboard.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Sessions</h1>")

@app.get("/session-dashboard.html", response_class=HTMLResponse)
async def session_dashboard_page():
    return await sessions_page()

@app.get("/index.html", response_class=HTMLResponse)
async def index_page():
    return await root()

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
