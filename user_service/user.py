# user_service/user.py
# Rôle : gérer la base utilisateurs (création & récupération).


from flask import Flask, request, jsonify
from database import init_db, add_user, get_user_by_username, verify_password
import os
import json

users_app = Flask(__name__)
init_db()

@users_app.route("/users/<username>", methods=["GET"])
def get_user_route(username):
    user = get_user_by_username(username)
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404

@users_app.route("/users", methods=["POST"])
def add_user_route():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if add_user(username, password):
        return jsonify({"status": "created"}), 201
    return jsonify({"error": "User already exists"}), 409

@users_app.route("/verify_password", methods=["POST"])
def verify_password_route():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = get_user_by_username(username)
    if not user:
        return jsonify({"valid": False}), 404

    is_valid = verify_password(user["password_hash"], password)
    return jsonify({"valid": is_valid}), 200