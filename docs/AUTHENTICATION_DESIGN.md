# Conception de l'authentification avant ouverture publique

## Décision provisoire

La première version hébergée doit être privée, avec un seul compte propriétaire et sans inscription publique. Le nombre de comptes pourra évoluer plus tard après une revue séparée des besoins et des risques.

Ce document décrit une conception à implémenter et à tester. Il ne signifie pas que l'authentification existe déjà.

## Parcours recommandé

1. Créer le compte propriétaire une seule fois au moyen d'une commande d'administration exécutée dans un environnement contrôlé, jamais par une route HTTP publique.
2. Refuser toute création de compte publique.
3. Authentifier avec un mot de passe long, stocké uniquement sous forme de hachage Argon2id avec paramètres maintenus à jour.
4. Après connexion, créer un identifiant de session aléatoire cryptographiquement sûr. Enregistrer uniquement son empreinte côté serveur, avec date d'expiration et possibilité de révocation.
5. Envoyer l'identifiant dans un cookie de session `HttpOnly`, `Secure` en production, `SameSite=Lax` ou plus strict si compatible, avec le chemin et la durée les plus limités possibles.
6. Renouveler l'identifiant après authentification et révoquer la session à la déconnexion, à l'expiration et lors d'une révocation administrative.
7. Ne jamais mettre le mot de passe, l'identifiant de session ou un secret dans le stockage local du navigateur, les URL, les journaux ou les réponses API.

## Protections navigateur et API

- Vérifier l'en-tête `Origin` contre l'origine exacte configurée pour toute requête qui modifie des données.
- Ajouter une protection CSRF avec un jeton lié à la session et envoyé dans un en-tête dédié ; refuser les requêtes mutatives sans jeton valide.
- Ne pas considérer CORS comme une authentification ou une protection CSRF.
- Autoriser uniquement l'origine exacte du frontend, les méthodes et en-têtes réellement nécessaires.
- Exiger une session valide sur toutes les routes privées ; seules la santé minimale et la connexion doivent être publiques.
- Ne pas exposer les routes privées par défaut, y compris les tâches, événements, permissions, chat, statut Telegram et arrêt d'urgence.
- Appliquer des limites distinctes et strictes aux tentatives de connexion et aux requêtes authentifiées.
- Garder les messages d'erreur de connexion génériques pour éviter l'énumération de comptes.

## Stockage et données

Les sessions et le compte propriétaire doivent être stockés dans la base persistante, avec dates UTC et index sur les empreintes de session et expirations. Les valeurs de session ne sont jamais conservées en clair.

Avant déploiement, choisir une base persistante supportée par l'hébergement, vérifier les sauvegardes et tester une restauration. Ne pas compter sur le disque éphémère d'une instance gratuite. La migration SQLite vers PostgreSQL doit être testée séparément ; ne pas changer le stockage existant sans migration et sauvegarde vérifiées.

## Variables et secrets

- Les secrets de production sont configurés dans le gestionnaire de secrets de l'hébergeur.
- Aucun secret par défaut ou mot de passe initial codé en dur.
- Aucun secret transmis dans le chat ou commité dans Git.
- Une clé de signature ou de chiffrement doit être générée aléatoirement, conservée côté serveur et pouvoir être renouvelée avec une procédure documentée.
- Les secrets de test sont fictifs et limités à la CI.

## Tests exigés avant de lever le garde-fou local

- Une requête anonyme vers chaque route privée est refusée.
- Une session valide permet uniquement les actions du compte propriétaire.
- Mot de passe incorrect, session expirée, session révoquée et cookie altéré sont refusés.
- L'identifiant de session change après connexion.
- Une requête mutative sans CSRF ou avec un jeton invalide est refusée.
- Une origine non autorisée est refusée, y compris lorsque le navigateur envoie des cookies.
- Le cookie de production porte les attributs attendus.
- Les tentatives répétées de connexion sont limitées sans bloquer durablement le propriétaire.
- Les réponses, journaux et traces d'erreur ne révèlent ni mot de passe, ni cookie, ni secret.
- Les tests vérifient que les tâches et événements ne sont pas accessibles sans session.

## Ordre d'implémentation

1. Écrire les tests d'authentification et de refus par défaut.
2. Ajouter les tables de compte et de session avec migrations.
3. Ajouter connexion, déconnexion, session courante et CSRF.
4. Protéger chaque route privée et tester les cas anonymes.
5. Ajouter la configuration stricte de l'origine et des cookies de production.
6. Choisir et valider le stockage persistant et la stratégie de sauvegarde.
7. Seulement ensuite, réévaluer le garde-fou local et préparer un environnement de préproduction.

## État

**Non implémenté.** Le middleware local-only reste obligatoire. Ce document ne constitue ni une autorisation de déploiement ni une preuve de sécurité.