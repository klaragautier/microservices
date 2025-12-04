# Auth Service : reçoit le username/password
# créer un JWT et vérifie les JWT quand on lui demande

from app import app
from flask import request, jsonify
import jwt
import secrets
import datetime
import os
import json

# Clé secrète pour signer les JWT
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

# Durées d'expiration des tokens
ACCESS_TOKEN_EXPIRES_MINUTES = 15
REFRESH_TOKEN_EXPIRES_DAYS = 30

# Fichier pour stocker les refresh tokens
REFRESH_TOKENS_FILE = "/app/tokens/refresh_tokens.json"

# --- Fichier JSON pour stocker les refresh tokens ---
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def initialize_files():
    os.makedirs("/app/tokens", exist_ok=True)
    if not os.path.exists(REFRESH_TOKENS_FILE):
        save_data({}, REFRESH_TOKENS_FILE)

initialize_files()


# --- Fonctions de création et vérification des tokens ---

# On va créer un access token
def create_access_token(username:str):
    now = datetime.datetime.utcnow()

    payload = {
        "sub": username,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    }

    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    return token


# On va créer un refresh token
def create_refresh_token(username:str):
    token = secrets.token_urlsafe(64)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)

    data = load_data(REFRESH_TOKENS_FILE)

    if username not in data:
        data[username] = []

    data[username].append({
        "token": token,
        "expires_at": expires_at.isoformat(),
        "revoked": False
    })

    save_data(data, REFRESH_TOKENS_FILE)
    return token


def verify_refresh_token(token:str):
    data = load_data(REFRESH_TOKENS_FILE)
    for user, tokens in data.items():
        for entry in tokens:
            if entry["token"] == token and entry["revoked"] is False:
                exp = datetime.datetime.fromisoformat(entry["expires_at"])
                if exp > datetime.datetime.utcnow():
                    return user
    return None



@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.json
    username = data.get("username")

    access = create_access_token(username)
    refresh = create_refresh_token(username)

    return jsonify({
        "access_token": access,
        "refresh_token": refresh
    }), 200


@app.route("/auth/refresh", methods=["POST"])
def auth_refresh():
    token = request.json.get("refresh_token")
    user = verify_refresh_token(token)

    if user is None:
        return jsonify({"error": "Refresh token invalide"}), 401

    new_access = create_access_token(user)
    return jsonify({"access_token": new_access}), 200
