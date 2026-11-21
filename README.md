# AutoPilot AI

Assistant IA hybride pour préparer et organiser des tâches web avec contrôle humain et sécurité en priorité.

> **Prototype en construction :** cette version prépare des propositions de tâches, mais n'exécute aucune action sur le navigateur ou l'ordinateur.

## Démarrage

Consulte [GETTING_STARTED.md](GETTING_STARTED.md) pour lancer l'API FastAPI et l'interface React/Vite sur ton ordinateur.

## Architecture

- `frontend/` : mini-application React.
- `backend/` : API FastAPI et tests.
- `docs/architecture.md` : flux et étapes de conception.
- `SECURITY.md` : règles de sécurité obligatoires.

## Sécurité

Aucune action externe sans confirmation explicite. Pas de collecte de mots de passe, pas de contournement de protections de sites, pas de commandes système arbitraires. Ne publie jamais de clé API ni de fichier `.env`.

## État

- [x] Structure frontend/backend
- [x] Première interface de préparation de tâche
- [x] Endpoint API de prévisualisation non exécutable
- [ ] Assistant IA connecté
- [ ] Planification et historique persistants
- [ ] Automatisation web contrôlée
- [ ] Agent local facultatif et isolé
- [ ] PWA et déploiement
