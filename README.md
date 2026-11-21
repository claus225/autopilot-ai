# AutoPilot AI

Assistant IA hybride pour préparer, organiser et planifier des tâches avec contrôle humain et sécurité en priorité.

> **Prototype en construction :** l'application enregistre des tâches et leurs échéances. Elle ne pilote pas encore le navigateur ou l'ordinateur et n'exécute aucune action externe.

## Fonctionnalités disponibles

- Interface React/Vite pour ajouter et consulter des tâches.
- API FastAPI pour créer, lister et mettre à jour l'état des tâches.
- Persistance locale avec SQLite, y compris les dates limites facultatives.
- Migration automatique de la base SQLite existante pour ajouter le champ d'échéance.
- Endpoint de prévisualisation qui prépare une proposition sans l'exécuter.
- Tests backend et compilation frontend via GitHub Actions.

## Démarrage

Consulte [GETTING_STARTED.md](GETTING_STARTED.md) pour lancer l'API FastAPI et l'interface React/Vite sur ton ordinateur.

## Architecture

- `frontend/` : mini-application React.
- `backend/` : API FastAPI, stockage SQLite et tests.
- `docs/architecture.md` : flux et étapes de conception.
- `SECURITY.md` : règles de sécurité obligatoires.

## Sécurité

Aucune action externe sans confirmation explicite. Pas de collecte de mots de passe, pas de contournement de protections de sites, pas de commandes système arbitraires. Ne publie jamais de clé API ni de fichier `.env`.

## État du prototype

- [x] Structure frontend/backend
- [x] Interface de préparation de tâche
- [x] Prévisualisation API non exécutable
- [x] Création, consultation et suivi d'état des tâches
- [x] Stockage local SQLite
- [x] Dates limites facultatives enregistrées avec les tâches
- [x] Tests backend et compilation frontend dans CI
- [ ] Notifications et rappels effectifs
- [ ] Assistant IA connecté
- [ ] Automatisation web contrôlée
- [ ] Agent local facultatif et isolé
- [ ] PWA et déploiement

**Important :** une date limite est actuellement enregistrée et affichée. Aucun rappel automatique ou notification n'est encore envoyé. Les fonctions non cochées ne sont pas disponibles.
