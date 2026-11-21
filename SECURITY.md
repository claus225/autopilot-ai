# Politique de sécurité

La sécurité prime sur l'autonomie. AutoPilot AI est un prototype et ne doit pas être utilisé pour exécuter des actions sensibles.

## Règles obligatoires

1. Ne jamais demander, afficher, journaliser ou stocker un mot de passe, une clé privée ou un code à usage unique.
2. Ne jamais intégrer de secret réel dans le code, les issues, les captures d'écran ou les commits. Utiliser des variables d'environnement locales.
3. Ne jamais contourner les CAPTCHA, les contrôles d'accès, les limites d'utilisation ou les protections d'un site.
4. Ne jamais envoyer de message, publier, acheter, supprimer ou modifier des données externes sans validation explicite de l'utilisateur.
5. Ne pas exécuter de commandes shell arbitraires fournies par un modèle.
6. Limiter l'agent local à une liste d'actions et de répertoires autorisés ; désactivé par défaut.
7. Prévoir un arrêt d'urgence, des journaux expurgés de données sensibles et une confirmation avant chaque action à impact externe.

## Assistant IA local

Le connecteur de chat contacte uniquement Ollama à l'adresse fixe `127.0.0.1:11434`. Aucun fournisseur distant ni clé API n'est utilisé. Le modèle reçoit uniquement l'historique textuel du chat, dans une limite de taille. Il ne reçoit aucun outil, accès aux fichiers, navigateur, compte ou commande système. Le statut « prêt » signifie que le service local répond et que le modèle configuré est installé ; cela ne signifie pas que l'application est autorisée à agir.

## Centre de sécurité et arrêt d'urgence

L'API expose `GET /api/security/status` pour afficher les capacités réellement activées et `POST /api/security/emergency-stop` pour suspendre le chat IA. Lorsque l'arrêt est activé, `POST /api/assistant/chat` répond avec le statut HTTP 423 et refuse la génération. L'état de l'arrêt d'urgence est conservé dans SQLite et survit donc au redémarrage normal de l'API.

`GET /api/security/events` fournit un journal limité aux métadonnées des changements d'arrêt d'urgence (type, état, date). Aucun message de chat, texte de tâche ou secret n'est écrit dans ce journal. La limite de consultation est de 50 événements.

**Limites connues :** ce mécanisme protège le chat et l'interface locale contre les nouvelles demandes, mais ne constitue pas encore un coupe-circuit universel pour des automatisations futures. Les automatisations du navigateur et le contrôle du PC restent absents et désactivés. L'API refuse les connexions distantes, applique une limite simple de requêtes par adresse cliente, limite les corps de requête annoncés et ajoute des en-têtes HTTP de protection. Elle n'a toutefois pas encore d'authentification par utilisateur : elle doit rester liée à 127.0.0.1 et ne doit pas être exposée directement sur Internet. Ces mesures ne constituent pas une sécurité suffisante pour un service public.

## Signaler une vulnérabilité

Ne publiez pas de secret ni de détail exploitable dans une issue publique. Contactez le propriétaire du dépôt via les moyens privés de GitHub.

## Données

Le prototype ne doit pas recevoir de données personnelles sensibles. Les données de test doivent être fictives.

## Permissions à refus par défaut

Le registre SQLite contient cinq catégories de capacités futures : automatisation du navigateur, contrôle du PC, publication sociale, envoi de messages externes et achats en ligne. Elles sont toutes initialisées à `false`. L'API `GET /api/security/permissions` permet de les consulter. Toute tentative de les activer via `PATCH /api/security/permissions/{permission_key}` est refusée tant que la capacité correspondante n'est pas implémentée. Les tentatives de déblocage sont journalisées sans contenu de message. Ce registre n'accorde donc aucun accès externe.

## Protection de l'API locale

Le middleware refuse les clients dont l'adresse n'est pas une adresse de boucle locale, limite le débit à 60 requêtes par minute et par adresse cliente, refuse les corps annoncés au-delà de 64 Ko et ajoute des en-têtes de protection. Le serveur doit être lancé explicitement sur `127.0.0.1`. La limite basée sur `Content-Length` est une défense complémentaire et ne remplace pas une limite stricte au niveau du serveur/proxy. L'API n'ayant pas encore de gestion de comptes ni d'authentification, aucun déploiement public n'est autorisé.

## Intégration Telegram (phase initiale)

La première version du connecteur lit TELEGRAM_BOT_TOKEN uniquement depuis l'environnement du serveur et appelle getMe pour vérifier le bot. Le token n'est jamais renvoyé dans l'API, l'interface ou les journaux. Cette phase est strictement en lecture seule : aucun message n'est envoyé, aucun lien n'est créé et aucun paramètre de groupe ou de canal n'est modifié. L'arrêt d'urgence suspend également cette vérification. Ne configure jamais le token dans le code source, dans GitHub ou dans une conversation.

## Conditions avant déploiement public sur Render

Le backend doit rester local tant que les points suivants ne sont pas réalisés et testés :

- Authentification côté serveur, sessions sécurisées, expiration et déconnexion.
- Protection CSRF et vérification stricte de l'origine autorisée.
- CORS limité au domaine exact du frontend.
- Limites de débit et de taille de requête adaptées au proxy et à l'environnement multi-instance.
- Base de données persistante. Le système de fichiers d'un service gratuit peut être éphémère ; SQLite local ne doit pas être supposé durable après redémarrage ou remplacement d'instance.
- Tests négatifs pour les accès anonymes, les sessions expirées, les origines et jetons CSRF invalides.
- Déploiement initial sans token Telegram ni actions externes.

Ne supprime jamais le garde-fou loopback pour « faire marcher » le déploiement. La liste complète des étapes figure dans [docs/RENDER_DEPLOYMENT.md](docs/RENDER_DEPLOYMENT.md).
