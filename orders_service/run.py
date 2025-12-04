# Ce fichier ne sert qu'au lancement du serveur web
# Il est possible de passer du mode debug au mode prod sans altérer le code de l'application

from app import app
app.run(host="0.0.0.0", port=5003, debug=True)