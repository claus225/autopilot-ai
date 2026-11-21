# Démarrage rapide

## Prérequis

- Python 3.10 ou plus récent
- Node.js 18 ou plus récent
- npm

## 1. Lancer l'API (Windows PowerShell)

Depuis la racine du dépôt :

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Si PowerShell bloque l'activation, ouvre un terminal autorisé par ton système ou lance directement :
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Vérifie ensuite http://127.0.0.1:8000/api/health

## 2. Lancer l'interface

Dans un autre terminal, depuis la racine :
```powershell
cd frontend
npm install
npm run dev
```

Ouvre l'adresse locale affichée par Vite (normalement http://localhost:5173).

## 3. Tester l'API

Depuis le dossier `backend` avec l'environnement virtuel activé :
```powershell
python -m pytest
```

## Limites de cette version

Le formulaire envoie une demande à l'API pour créer un aperçu non exécutable. Il ne pilote pas encore le navigateur, l'ordinateur, les réseaux sociaux ou des services tiers. N'ajoute aucune clé secrète dans GitHub.
