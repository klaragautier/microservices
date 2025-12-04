# API Gateway :  reçoit toutes les requêtes des pages web
# vérifie que le JWT est valable puis redirige vers le bon microservice

# from flask import request : données reçues par l'API (formulaire JSON, méthode HTTP)
# import requests : outil pour envoyer les requêtes HTTP vers d'autres services
from app import app
from flask import render_template, request, url_for, redirect, session
import requests
#avec Docker
import os

#sans Docker
"""AUTH_URL = "http://localhost:5001" # route du Auth Service
USER_URL = "http://localhost:5002" # route du User Service
ORDERS_URL = "http://localhost:5003" # route du Orders Service"""

#avec Docker
USER_URL = os.getenv("USER_URL")
AUTH_URL = os.getenv("AUTH_URL")
ORDERS_URL = os.getenv("ORDERS_URL")
print(AUTH_URL)


# Une route est une URL à laquelle l'application répond.
# Chaque route correspond à une fonction Python qui s'éxécute quand l'application est visité.
# Lors de l'appel à la route, la fonction (ici index()) est executé.
# Ici seulement une chaine de caractère est affichée.
@app.route('/')
def index():
    return render_template("login.html")


# Pour afficher une page web on utilise render_template()
# On arrive sur la page login.html
# On récupère le username et le password du formulaire
# ils vont être envoyés au User Service pour vérifier et avoir la hash
# resp_user = requests.post(URL, json), on doit toujours avoir l'URL et après on peut avoir un json, data, files
# Le User Service renvoie le password_hash 
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get("user")
    password = request.form.get("password")
    action = request.form.get("action")
    if action == "register":
        resp = requests.post(
            USER_URL+"/user",
            json = {"username": username, "password": password}
        )
        if resp.status_code != 201:
            return render_template("login.html", error="Impossible de créer le compte")
        return render_template("login.html", error="Compte créé ! Vous pouvez vous connecter")    
    resp_user = requests.post(
        USER_URL+"/user/login",
        json = {"username": username, "password": password}
    )
    if resp_user.status_code != 200:
        return render_template("login.html", error="Utilisateur introuvable ou mot de passe incorrect")
    
    resp_auth = requests.post(
        AUTH_URL+"/auth/login",
        json = {"username": username}
    )
    if resp_auth.status_code != 200:
        return render_template("login.html", error="Erreur Auth Service")

    tokens = resp_auth.json()
    session["user"] = username
    session["access_token"] = tokens.get("access_token")
    session["refresh_token"] = tokens.get("refresh_token")
    return redirect(url_for("accueil", user=username))


# On arrive sur la page accueil.html
@app.route('/accueil')
def accueil():
    user = request.args.get("user")
    resp = requests.get(ORDERS_URL+"/articles")
    articles = resp.json()
    return render_template("accueil.html", articles=articles, user=user)

# On arrive sur la page achat.html
# On récupère le panier du formulaire et les quantité envoyées par accueil.html
# On envoie le panier au Orders Service 
# Si le code HTTP n'est pas 200, on affiche un message d'erreur
# On calcule le total de la commande
# Sinon on affiche le résultat de la commande
@app.route('/submit_order/<user>', methods=['POST'])
def submit_order(user):
    basket = request.form.to_dict()
    resp = requests.post(ORDERS_URL+"/orders", json=basket)
    if resp.status_code != 200:
        return render_template("accueil.html", user=user, error="Erreur lors du traitement de la commande")
    result = resp.json()
    order_details = resp.json().get("order_details", [])
    grand_total = sum(item["total_price"] for item in order_details)
    return render_template("achat.html", 
                           user=user,
                           status=result.get("status"), 
                           order_details=result.get("order_details"),
                           grand_total=grand_total)




