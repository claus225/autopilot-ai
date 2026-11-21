# Authentification propriétaire — état d'implémentation

## Routes et interface

- `GET /api/auth/status` : indique si le compte propriétaire existe et si la configuration initiale est disponible.
- `POST /api/auth/setup` : création unique du compte, protégée par un secret d'initialisation d'au moins 32 caractères.
- `POST /api/auth/login` : vérification du mot de passe avec Argon2id.
- `GET /api/auth/me` : vérifie la session active.
- `POST /api/auth/logout` : révocation de session avec contrôle CSRF.
- L'interface React présente l'écran de première configuration, de connexion et de déconnexion.

## Protection des routes métier

Une fois le compte propriétaire créé, les routes tâches, assistant, sécurité et Telegram exigent une session valide. Les requêtes mutatives exigent aussi une origine exactement autorisée et un jeton CSRF lié à la session. Les cookies sont HttpOnly pour la session, SameSite=Strict et Secure par défaut ; le cookie CSRF est lisible par le frontend afin de le renvoyer dans `X-CSRF-Token`.

En environnement `APP_ENV=production`, l'API se verrouille aussi si le compte propriétaire n'a pas encore été créé. Elle ne laisse accessibles que la santé, le statut d'authentification et la route de configuration initiale. Un secret de configuration présent déclenche également ce verrouillage en attendant la création du compte.

Les sessions expirent après 12 heures par défaut et ne peuvent pas dépasser 24 heures. Seules les empreintes des jetons sont stockées. La connexion limite aussi les tentatives à cinq par adresse cliente sur une fenêtre glissante de 15 minutes (limiteur en mémoire, défense complémentaire).

## Configuration

- Définir `APP_ENV=production` sur le serveur.
- Définir `AUTOPILOT_SETUP_TOKEN` comme secret aléatoire d'au moins 32 caractères dans l'environnement privé du serveur.
- Définir `FRONTEND_ORIGIN` sur l'origine exacte du frontend.
- Garder `AUTH_COOKIE_SECURE=true` en HTTPS. `false` est réservé au développement local HTTP.
- Utiliser un mot de passe propriétaire long et unique. Ne jamais le mettre dans le dépôt.
- Pour le développement local HTTP, vérifier que le frontend et l'API utilisent le même nom d'hôte (par exemple localhost) et définir `AUTH_COOKIE_SECURE=false` dans l'environnement local.

Le secret d'initialisation n'est pas le mot de passe de connexion. Après la création du compte, toute nouvelle tentative de configuration est refusée.

## Limites restantes — déploiement public toujours bloqué

L'authentification et les contrôles de session sont intégrés au code et couverts par les tests CI, mais cela ne suffit pas à autoriser une ouverture sur Internet.

- Le middleware continue de refuser les connexions distantes : le garde-fou loopback n'a pas été retiré.
- Le stockage est toujours SQLite local ; il faut une base persistante et une stratégie de sauvegarde adaptées à l'hébergement.
- Le limiteur de débit reste en mémoire et par processus ; il doit être adapté à un environnement multi-instance.
- La limite de taille de requête actuelle contrôle l'en-tête `Content-Length` ; elle doit être complétée par une limite effective au niveau ASGI/proxy, y compris pour les requêtes chunked.
- Les cookies SameSite=Strict exigent une architecture frontend/API compatible avec ce choix (même site ou proxy de même origine). Ne pas supposer que deux domaines Render distincts fonctionneront directement avec cette configuration.
- La configuration CORS, les cookies HTTPS, les sauvegardes et le flux complet doivent être validés dans un environnement de test avant publication.

**Ne pas exposer le backend et ne pas créer le service Render public à ce stade.**
