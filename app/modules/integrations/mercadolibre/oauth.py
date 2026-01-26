import os
import requests
from urllib.parse import urlencode

ML_CLIENT_ID = os.getenv("MERCADOLIBRE_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("MERCADOLIBRE_CLIENT_SECRET")
ML_REDIRECT_URI = os.getenv("MERCADOLIBRE_REDIRECT_URI")

AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

class MLOAuthError(Exception):
    pass

def _validate_env():
    missing = [k for k, v in {
        "MERCADOLIBRE_CLIENT_ID": ML_CLIENT_ID,
        "MERCADOLIBRE_CLIENT_SECRET": ML_CLIENT_SECRET,
        "MERCADOLIBRE_REDIRECT_URI": ML_REDIRECT_URI,
    }.items() if not v]
    if missing:
        raise MLOAuthError(f"Missing env vars: {', '.join(missing)}")

def get_authorization_url(state: str):
    _validate_env()
    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_REDIRECT_URI,
        "state": state,  # ✅ CLAVE
    }
    return f"{AUTH_URL}?{urlencode(params)}"

def exchange_code_for_token(code: str):
    _validate_env()
    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }

    try:
        r = requests.post(TOKEN_URL, data=payload, timeout=20)
    except requests.RequestException as e:
        raise MLOAuthError(f"OAuth request failed: {e}")

    if r.status_code != 200:
        raise MLOAuthError(f"OAuth error {r.status_code}: {r.text}")

    return r.json()

def refresh_access_token(refresh_token: str):
    _validate_env()
    payload = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    try:
        r = requests.post(TOKEN_URL, data=payload, timeout=20)
    except requests.RequestException as e:
        raise MLOAuthError(f"Refresh request failed: {e}")

    if r.status_code != 200:
        raise MLOAuthError(f"Refresh error {r.status_code}: {r.text}")

    return r.json()
