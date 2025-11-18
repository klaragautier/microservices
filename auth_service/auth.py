# auth_service/auth.py
# Rôle : gérer l’authentification, les JWT et le refresh token.

import bcrypt
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import datetime
import os
import secrets  
import requests
from flask_bcrypt import Bcrypt
import jwt 

auth_app=Flask(__name__)

USER_SERVICE_URL = "http://localhost:5001" 


auth_app.config['SECRET_KEY'] = 'secret123'
ACCESS_TOKEN_EXPIRES_MINUTES = 15
REFRESH_TOKEN_EXPIRES_DAYS = 7


# --- Fichier pour stocker les refresh tokens (façon "base") ---
REFRESH_TOKENS_FILE = 'refresh_tokens.json'

DEFAULT_REFRESH_TOKENS = {}



# --- Fonctions de gestion des fichiers JSON ---
def load_data(filename):
    """Charge les données depuis un fichier JSON donné."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Retourne un dictionnaire vide si non trouvé
        return {} 
    except json.JSONDecodeError:
        # Retourne un dictionnaire vide si corrompu
        return {}

def save_data(data, filename):
    """Sauvegarde les données dans un fichier JSON donné."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# --- Helpers refresh token ---

def create_access_token(username: str):
    """Crée un JWT d'accès de courte durée pour un utilisateur."""
    now = datetime.datetime.utcnow()
    payload = {
        "sub": username,  # sujet = l'utilisateur
        "iat": now,
        "exp": now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    }
    token = jwt.encode(payload, auth_app.config['SECRET_KEY'], algorithm="HS256")
    # PyJWT >= 2 retourne déjà une str, sinon tu peux faire token.decode("utf-8")
    return token

def add_refresh_token(username: str, token: str, expires_at: datetime.datetime):
    """Enregistre un refresh token pour un utilisateur dans refresh_tokens.json."""
    data = load_data(REFRESH_TOKENS_FILE)
    if username not in data:
        data[username] = []
    data[username].append({
        "token": token,
        "expires_at": expires_at.isoformat(),
        "revoked": False
    })
    save_data(data, REFRESH_TOKENS_FILE)


def create_refresh_token(username: str) -> str:
    """Crée un refresh token aléatoire de longue durée et le stocke dans le JSON."""
    token = secrets.token_urlsafe(64)  # grande chaîne aléatoire
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
    add_refresh_token(username, token, expires_at)
    return token

def find_refresh_token(token: str):
    """Recherche un refresh token exact dans refresh_tokens.json."""
    data = load_data(REFRESH_TOKENS_FILE)
    for user, tokens in data.items():
        for entry in tokens:
            if entry["token"] == token:
                return user, entry
    return None, None


def revoke_refresh_token(token: str):
    """Marque un refresh token comme révoqué dans refresh_tokens.json."""
    data = load_data(REFRESH_TOKENS_FILE)
    for user, tokens in data.items():
        for entry in tokens:
            if entry["token"] == token:
                entry["revoked"] = True
                save_data(data, REFRESH_TOKENS_FILE)
                return True
    return False

# --- Fonction : Initialisation des fichiers au démarrage ---
def initialize_files():
    """Crée les fichiers JSON s'ils n'existent pas avec les données par défaut."""

    # 2. Initialisation de refresh_tokens.json vide si besoin
    if not os.path.exists(REFRESH_TOKENS_FILE):
        print(f"Création initiale de {REFRESH_TOKENS_FILE}...")
        save_data(DEFAULT_REFRESH_TOKENS, REFRESH_TOKENS_FILE)

# --- Exécuter l'initialisation au chargement du module ---
initialize_files()



### Inscription ###
@auth_app.route("/register", methods=["POST"])
def register():
    username = request.form.get("user")
    password = request.form.get("password")

    if not username or not password:
        return jsonify({"error": "Missing user or password"}), 400

    # Vérifier si l’utilisateur existe
    response = requests.get(f"{USER_SERVICE_URL}/users/{username}")

    if response.status_code == 200:
        return jsonify({"error": "User already exists"}), 409

    # Hacher le mot de passe
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    # Créer l’utilisateur dans user_service
    r = requests.post(f"{USER_SERVICE_URL}/users", json={
        "username": username,
        "password": hashed
    })

    if r.status_code != 201:
        return jsonify({"error": "User creation failed"}), 500

    # Générer les tokens
    access = create_access_token(username)
    refresh = create_refresh_token(username)

    return jsonify({
        "user": username,
        "access_token": access,
        "refresh_token": refresh
    }), 200


### Connexion ####
@auth_app.route("/login", methods=["POST"])
def login():
    data = request.form or request.json  # récupère peu importe le type

    username = data.get("user")
    password = data.get("password")

    # 1. Récupérer l'utilisateur dans user_service
    r = requests.get(f"{USER_SERVICE_URL}/users/{username}")
    if r.status_code != 200:
        return jsonify({"error": "Invalid username"}), 404

    user_info = r.json()

    # 2. Vérifier le mot de passe via user_service
    r2 = requests.post(
        f"{USER_SERVICE_URL}/verify_password",
        json={"username": username, "password": password}
    )

    if not r2.json().get("valid", False):
        return jsonify({"error": "Wrong password"}), 401

    # 3. Succès -> retourner le username + token plus tard
    return jsonify({"user": username}), 200


### Refresh Token ###
@auth_app.route("/refresh", methods=["POST"])
def refresh_token():
    refresh_token = request.form.get("refresh_token")

    if not refresh_token:
        return {"error": "No refresh token"}, 401

    data = load_data(REFRESH_TOKENS_FILE)

    found_user = None
    found_entry = None

    for user, tokens in data.items():
        for t in tokens:
            if t["token"] == refresh_token:
                found_user = user
                found_entry = t
                break

    if not found_entry:
        return {"error": "Unknown token"}, 401

    if found_entry["revoked"]:
        return {"error": "Token revoked"}, 401

    expiry = datetime.datetime.fromisoformat(found_entry["expires_at"])
    if datetime.datetime.utcnow() > expiry:
        return {"error": "Token expired"}, 401

    # rotation
    found_entry["revoked"] = True
    save_data(data, REFRESH_TOKENS_FILE)

    new_access = create_access_token(found_user)
    new_refresh = create_refresh_token(found_user)

    return jsonify({
        "user": found_user,
        "access_token": new_access,
        "refresh_token": new_refresh
    }), 200

