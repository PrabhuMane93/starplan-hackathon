# login_app.py
import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv, set_key
import uvicorn
import time

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# OAuth setup
oauth = OAuth()
oauth.register(
    name="microsoft",
    server_metadata_url=(
        "https://login.microsoftonline.com/consumers/v2.0/.well-known/openid-configuration"
    ),
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    client_kwargs={
        "scope": "openid email profile offline_access Mail.Read Mail.Send IMAP.AccessAsUser.All"
    },
)

# -------------------------
# HOME
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><body>
        <h1>Outlook Login</h1>
        <a href="/login">
            <button style="padding:10px 20px; font-size:18px;">Login with Microsoft</button>
        </a>
    </body></html>
    """

# -------------------------
# LOGIN
# -------------------------
@app.get("/login")
async def login(request: Request):
    return await oauth.microsoft.authorize_redirect(request, REDIRECT_URI)

# -------------------------
# CALLBACK
# -------------------------
@app.get("/callback")
async def callback(request: Request):
    token = await oauth.microsoft.authorize_access_token(request)

    access = token["access_token"]
    refresh = token["refresh_token"]

    set_key(".env", "ACCESS_TOKEN", access)
    set_key(".env", "REFRESH_TOKEN", refresh)
    time.sleep(5)

    requests.get("http://localhost:4000/subscribe")  # Notify backend to subscribe
    return {
        "message": "OAuth success!",
        "access_token": access[:40] + "...",
        "refresh_token": refresh[:40] + "..."
    }

if __name__ == "__main__":
    print("Login service running at http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000)