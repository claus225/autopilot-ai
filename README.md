# AutoPilot AI

Assistant IA hybride pour préparer, organiser et planifier des tâches avec contrôle humain et sécurité en priorité.

 > **Prototype en construction :** le chat IA local est intégré au code, mais il ne répond qu'après installation et démarrage d'Ollama et du modèle sur le PC. L'application ne pilote pas encore le navigateur ou l'ordinateur et n'exécute aucune action externe.

## Fonctionnalités disponibles

- Interface React/Vite pour ajouter et consulter des tâches.
- API FastAPI pour créer, lister et mettre à jour l'état des tâches.
- Persistance locale avec SQLite, y compris les dates limites facultatives.
- Migration automatique de la base SQLite existante pour ajouter le champ d'échéance.
- Endpoint de prévisualisation qui prépare une proposition sans l'exécuter.
- Interface de chat et connecteur IA local via Ollama (modèle à installer sur le PC ; aucun service cloud).
- Première base de connexion Telegram en lecture seule : vérification du bot via `GET /api/telegram/status`, sans publication ni modification de groupes/canaux.
- Centre de sécurité avec état des capacités, arrêt d’urgence persistant dans SQLite et journal d’événements limité aux métadonnées.
- Tests backend et compilation frontend via GitHub Actions.

## Démarrage

Consulte [GETTING_STARTED.md](GETTING_STARTED.md) pour installer Ollama, télécharger le modèle local et lancer l'API FastAPI et l'interface React/Vite sur ton ordinateur.

## Architecture et sécurité

- `frontend/` : mini-application React.
- `backend/` : API FastAPI, stockage SQLite et tests.
- `docs/architecture.md` : flux et étapes de conception.
- `docs/AUTHENTICATION_DESIGN.md` : conception de l'authentification propriétaire.
- `docs/AUTHENTICATION_IMPLEMENTATION.md` : routes, sessions, protection CSRF et limites restantes.
- `docs/RENDER_DEPLOYMENT.md` : prérequis de sécurité et de stockage avant Render.
- `docs/SECURITY_AUDIT_PLAN.md` : périmètre et contrôles de l'audit de sécurité autorisé après publication.
- `SECURITY.md` : règles de sécurité obligatoires.

Aucune action externe sans confirmation explicite. Pas de contournement de protections de sites ni de commandes système arbitraires. Ne publie jamais de clé API ni de fichier `.env`.

**Le backend ne doit toujours pas être exposé sur Internet.** L'authentification propriétaire est intégrée et les routes métier sont protégées après configuration du compte, mais le garde-fou loopback reste actif. Le stockage persistant et les contrôles adaptés à l'hébergement ne sont pas encore prêts. Le déploiement Render n'est ni configuré ni publié. Voir [les prérequis Render](docs/RENDER_DEPLOYMENT.md).

## État du prototype

- [x] Structure frontend/backend
- [x] Interface de préparation de tâche
- [x] Prévisualisation API non exécutable
- [x] Création, consultation et suivi d'état des tâches
- [x] Stockage local SQLite
- [x] Dates limites facultatives enregistrées avec les tâches
- [x] Aperçu des échéances et classification des tâches à rappeler
- [x] Tests backend et compilation frontend dans CI
- [ ] Notifications réelles (push/e-mail) et planification en arrière-plan
- [x] Connecteur de chat IA local (Ollama, modèle à installer sur le PC)
- [x] Arrêt d’urgence persistant dans SQLite et journal de sécurité sans contenu de messages
- [x] Authentification propriétaire Argon2id, sessions expirables/révocables, protection globale des routes métier et CSRF
- [x] Écrans frontend de première configuration, connexion et déconnexion
- [ ] Base de données persistante adaptée à l'hébergement
- [ ] Déploiement Render
- [ ] Connexion Telegram complète : groupes/canaux autorisés, publications après confirmation, liens d’invitation et historique (seul le contrôle de connexion en lecture seule existe pour l’instant)
- [ ] Automatisation web contrôlée
- [ ] Agent local facultatif et isolé
- [ ] PWA et déploiement

**Important :** une date limite est actuellement enregistrée et affichée. L'aperçu des échéances est disponible, mais aucun rappel automatique, notification push ou e-mail n'est envoyé. Les fonctions non cochées ne sont pas disponibles.
