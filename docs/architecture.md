# Architecture initiale

## Composants

- `frontend/` : interface React servie par Vite.
- `backend/app/` : API FastAPI.
- `backend/tests/` : tests de base de l'API.
- `SECURITY.md` : règles de sécurité obligatoires.

## Flux actuel

1. L'utilisateur saisit une tâche dans l'interface.
2. Le frontend envoie le texte à `POST /api/tasks/preview`.
3. L'API valide la taille et le type des champs.
4. L'API renvoie une proposition marquée `draft`.
5. Aucune action externe ou locale n'est exécutée.

## Étapes avant toute automatisation

- Authentification et gestion de sessions sûres.
- Modèle de permissions explicites par action.
- Écran de confirmation récapitulant l'action, la cible et les données transmises.
- Journal d'audit sans secrets.
- Arrêt d'urgence vérifié.
- Tests d'isolation pour tout futur agent local.

L'agent local et le navigateur automatisé restent désactivés tant que ces protections ne sont pas conçues et testées.
