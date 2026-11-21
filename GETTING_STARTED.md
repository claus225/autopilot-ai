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
- Définir une date limite facultative.
- Retrouver les tâches enregistrées après redémarrage grâce à SQLite.
- Marquer une tâche comme terminée ou à faire.
- Préparer un aperçu de tâche sans déclencher son exécution.
- Consulter les échéances en retard, du jour et des 7 prochains jours dans le tableau de bord.
- Activer des notifications locales du navigateur, avec choix de l'heure, pour les tâches dues aujourd'hui.
- Consulter l'API en lecture seule avec `GET /api/reminders?days=7` (période autorisée : 0 à 30 jours).

La base SQLite est créée localement par le backend dans `backend/data/` par défaut. Ce dossier est exclu de Git. Si une base plus ancienne existe, le backend ajoute automatiquement la colonne de date limite manquante.

## Limites et sécurité

Les notifications locales nécessitent une autorisation explicite dans le navigateur et fonctionnent uniquement tant que la page reste ouverte. Elles sont vérifiées toutes les 30 secondes et ne sont émises qu'une fois par tâche et par jour. Elles ne fonctionnent pas lorsque le site est fermé : aucune notification push, tâche de fond ou e-mail n'est configuré. L'heure et l'état d'activation sont stockés dans le stockage local du navigateur. Cette version ne comporte pas encore d'assistant IA connecté, d'automatisation du navigateur, de contrôle de l'ordinateur ni de publication sur les réseaux sociaux. Elle ne lance aucune action externe. N'ajoute aucune clé secrète dans GitHub et ne partage jamais un fichier `.env`.
