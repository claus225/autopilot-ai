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

Si PowerShell bloque l'activation, utilise directement :

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

## 3. Tester le backend

Depuis le dossier `backend` avec l'environnement virtuel activé :

```powershell
python -m pytest
```

La compilation frontend est vérifiée automatiquement par le workflow GitHub Actions.

## Fonctionnalités présentes

- Ajouter une tâche avec un titre et une description.
- Retrouver les tâches enregistrées après redémarrage grâce à SQLite.
- Marquer une tâche comme terminée ou à faire.
- Préparer un aperçu de tâche sans déclencher son exécution.

La base SQLite est créée localement par le backend dans `backend/data/` par défaut. Ce dossier est exclu de Git.

## Limites et sécurité

Cette version ne comporte pas encore de rappels programmés, d'assistant IA connecté, d'automatisation du navigateur, de contrôle de l'ordinateur ni de publication sur les réseaux sociaux. Elle ne lance aucune action externe. N'ajoute aucune clé secrète dans GitHub et ne partage jamais un fichier `.env`.