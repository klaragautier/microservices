FROM python:3.10-slim

# Crée un dossier pour l’application
WORKDIR /app

# Copier les fichiers
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code du microservice
COPY . .

# Exposer le port (adapter selon le service)
EXPOSE 5003

# Commande de lancement (adapter le fichier main)
CMD ["python", "run.py"]