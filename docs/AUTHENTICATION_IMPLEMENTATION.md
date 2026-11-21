# Authentification propriétaire — état d'implémentation

## Routes ajoutées

- `GET /api/auth/status` : indique si le compte propriétaire existe.
- `POST /api/auth/setup` : création unique, protégée par un secret d'initialisation.
- `POST /api/auth/login` : vérification du mot de passe Argon2id.
- `GET /api/auth/me` : vérifie la session active.
- `POST /api/auth/logout` : révocation de session avec contrôle CSRF.

Les sessions sont limitées à 12 heures par défaut et à 24 heures maximum. Le cookie de session est HttpOnly, SameSite=Strict et Secure par défaut. Le cookie CSRF est associé à la session et doit être renvoyé dans l'en-tête `X-CSRF-Token` pour la déconnexion. Les routes d'écriture vérifient aussi l'en-tête Origin.

## Configuration

- Définir `AUTOPILOT_SETUP_TOKEN` comme secret aléatoire d'au moins 32 caractères dans l'environnement privé du serveur.
- Définir `FRONTEND_ORIGIN` sur l'origine exacte du frontend.
- Garder `AUTH_COOKIE_SECURE=true` en HTTPS. La valeur `false` est réservée au développement local HTTP.
- Utiliser un mot de passe propriétaire long et unique. Ne jamais le mettre dans le dépôt.

Le secret d'initialisation n'est pas un mot de passe de connexion. Il sert uniquement à autoriser la toute première création du compte. Après la création, la route de setup refuse toute nouvelle tentative.

## Limite de sécurité importante — non prêt pour Internet

**L'authentification HTTP n'est pas encore appliquée à l'ensemble des routes de l'API.** Les nouvelles routes permettent de créer et vérifier une session, mais les routes tâches, assistant, sécurité et Telegram n'exigent pas encore cette session. L'interface frontend n'a pas encore d'écran de connexion.

Par conséquent :
- Ne pas exposer le backend sur Internet.
- Ne pas créer le service Render public.
- Conserver le garde-fou local-only existant.
- Ne pas considérer `/api/auth/me` comme une protection des autres endpoints.

Étapes suivantes obligatoires : intégrer une dépendance d'authentification à toutes les routes privées, protéger les requêtes mutatives avec CSRF, ajouter l'interface de connexion, puis tester les accès anonymes et les sessions expirées/révoquées sur chaque famille de routes.
