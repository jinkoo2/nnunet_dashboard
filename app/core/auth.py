import secrets
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings

security = HTTPBasic()


def verify_api_key(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


def verify_dashboard(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, settings.DASHBOARD_USER)
    correct_pass = secrets.compare_digest(credentials.password, settings.DASHBOARD_PASSWORD)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
