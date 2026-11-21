# Préparation au déploiement Render

## Décision actuelle

Le backend n'est pas prêt pour un déploiement public. Ne crée pas encore de service Render et ne renseigne aucun secret Telegram.

L'authentification propriétaire et la protection CSRF sont maintenant intégrées dans le code :
- création unique du compte par secret d'initialisation ;
- connexion par mot de passe Argon2id ;
- sessions sécurisées, expirables et révocables ;
- protection des routes métier après configuration du compte ;
- écran frontend de configuration/connexion ;
- verrouillage des routes métier en production avant la création du compte.

Le garde-fou loopback reste volontairement actif. Il ne faut pas le supprimer pour « faire marcher » Render.

## Bloqueurs avant backend public

- Remplacer ou compléter SQLite local par une base persistante adaptée à l'hébergement et aux sauvegardes.
- Adapter le limiteur de débit actuellement en mémoire et par processus à un environnement multi-instance.
- Ajouter une limite effective de corps de requête au niveau ASGI/proxy, y compris pour les requêtes chunked.
- Concevoir une architecture de même site ou un proxy de même origine pour les cookies `SameSite=Strict`, puis valider CORS avec credentials et HTTPS.
- Tester le parcours complet de configuration initiale, connexion, expiration, déconnexion, CSRF et accès anonymes sur un environnement de préproduction.
- Confirmer les limites réelles du plan Render au moment du déploiement.
- Déployer sans token Telegram et sans action externe dans un premier temps.

## Plan prudent

1. Conserver le backend local et Telegram en lecture seule.
2. Choisir la base persistante et définir les sauvegardes.
3. Adapter les protections réseau, le débit et la taille des corps de requête.
4. Préparer un frontend/API même-site et tester les cookies HTTPS.
5. Déployer un environnement de test sans actions externes.
6. Réaliser l'audit de sécurité autorisé.
7. Ajouter le token Telegram uniquement comme secret privé du backend, après validation des droits du bot.

## État actuel

- Authentification propriétaire et protection CSRF : intégrées au code, tests CI locaux.
- Protection loopback : toujours active.
- Base de données persistante hébergée : non configurée.
- Backend public : non déployé.
- Telegram : contrôle de connexion en lecture seule uniquement.
- Service Render : non créé.
