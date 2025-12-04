# User Service : s'occupe des infos des utilisateurs (profil, email, etc..)

from app import app
import sqlite3 
from flask import request, json
import bcrypt


# init_db() : crée la base de donnée et les tables si elles n'existent pas
# conn est la connexion à la base de donnée SQLite (ici user.db)
# cursor est l'outil qui permet d'envoyer les commandes SQL à la base
def init_db():
    print("Initialisation de la base de données...")
    conn = sqlite3.connect("user.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
                   )
                   """)
    conn.commit()
    conn.close()


# get_db() : ouvre la connexion à la base chaque fois que la route à besoin de lire ou écrire des données
# conn.row_factory = sqlite3.Row : récupère les résultats comme des dictionnaires => row["username"]
# On renvoie la connexion pour que la route puisse faire des requêtes (ex : conn.cursor())
def get_db():
    conn = sqlite3.connect("user.db")
    conn.row_factory = sqlite3.Row
    return conn
    


# Route pour créer un utilisateur
# data = request.get_json() : récupère le JSON envoyé par le client
# on va récupérer les deux champs du JSON, username + passord de Api Gateway
# on va hacher le mot de passe et enregistrer les données dans user_db
@app.route('/user', methods=['POST'])
def create_user_db():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user (username, password_hash) Values (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()
    return {"message": "Utilisateur créé avec succès"}, 201

# Route pour récupérer un utilisateur par son id
# on cherche l'user avec cette id
# user = cursor.fetchone() : on récupère une seule ligne ou None si existante
# on renvoie les infos trouvées sous forme JSON
@app.route('/user/<id>')
def fetch_user_db(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE id = ?", (id,))
    user = cursor.fetchone()
    conn.close()
    if user is None :
        return {"error" : "Utiliateur non trouvé"}, 404
    return {"id": user["id"], "username": user["username"]}


# Route pour vérifier le username et le password
# on renvoie le hash validé au Gateway
@app.route('/user/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user is None :
        return {"error": "Utilisateur introuvable"}, 404
    
    stored_hash = user["password_hash"].encode()
    if not bcrypt.checkpw(password.encode(), stored_hash) :
        return {"error": "Mot de passe incorrect"}, 401
    
    return {"password_hash": stored_hash.decode()}, 200


