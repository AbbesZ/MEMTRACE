# Utilisation stricte de Python 3.12 imposée par le cahier des charges
FROM python:3.12-slim

# Définition du répertoire de travail dans le conteneur
WORKDIR /app

# Copie et installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de tout le code source
COPY . .

# Exposition du port de l'API
EXPOSE 8000

# Commande de lancement
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]