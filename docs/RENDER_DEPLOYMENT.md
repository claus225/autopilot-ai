# Préparation au déploiement Render

## Décision de sécurité

Le dépôt n'est pas prêt à recevoir un déploiement public du backend. Ne crée pas encore de service Render et ne renseigne aucun secret Telegram.

Le middleware actuel de `backend/app/main.py` refuse volontairement toutes les connexions qui ne viennent pas de la boucle locale. Cette protection doit rester active tant qu'une vraie authentification côté serveur n'est pas implémentée et testée. Il ne faut pas simplement supprimer cette vérification pour faire fonctionner Render.

## Conditions obligatoires avant un backend public

- Authentification serveur avec sessions sécurisées (cookies HttpOnly, Secure et SameSite adaptés à l'architecture), expiration et déconnexion.
- Protection CSRF et vérification stricte de l'origine autorisée.
- Limitation de débit adaptée à un déploiement multi-instance, et limite de taille réelle des corps de requête au niveau ASGI/proxy.
- CORS limité à l'origine exacte du frontend.
- Stockage persistant adapté à l'hébergement : SQLite sur le système de fichiers éphémère d'un service gratuit Render n'est pas une base durable. Évaluer PostgreSQL et ses limites de gratuité avant de choisir.
- Tests d'accès anonyme refusé, session valide acceptée, session expirée refusée, origine/CSRF invalide refusé, arrêt d'urgence et absence de fuite de secrets.
- Vérifier la disponibilité et les limites du plan Render au moment du déploiement.

## Plan de déploiement prudent

1. Garder l'API locale et le token Telegram non configuré.
2. Implémenter et tester l'authentification et la protection CSRF.
3. Choisir une base persistante sans supposer qu'un stockage gratuit est permanent.
4. Déployer d'abord un environnement de test sans token Telegram ni actions externes.
5. Vérifier les journaux, les sauvegardes et les contrôles d'accès.
6. Ajouter le token Telegram uniquement dans les variables secrètes du service backend, après validation de la connexion et des droits du bot.

## État actuel

- Préparation documentaire : en cours.
- Backend public : bloqué volontairement par les contrôles de sécurité locaux.
- Telegram : vérification en lecture seule uniquement ; aucune publication ni création de lien.
- Déploiement Render : non effectué.
