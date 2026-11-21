# AutoPilot AI — plan d'audit de sécurité

## Statut et périmètre

Ce document prépare un audit défensif du site AutoPilot AI et de son API, uniquement sur les environnements appartenant au propriétaire du projet et explicitement autorisés.

Aucun test d'intrusion sur un site tiers, aucun déni de service, aucune tentative de vol de compte, aucune extraction de données et aucune modification destructive ne sont autorisés.

L'audit en production ne commence qu'après publication et confirmation de l'URL exacte, du périmètre autorisé et d'un créneau de test. Avant cela, seules la revue du code et les vérifications CI sont effectuées.

## État vérifié dans le dépôt

- Le backend refuse actuellement les connexions qui ne viennent pas de la boucle locale ou du client de test.
- Il n'existe pas encore d'authentification utilisateur côté serveur.
- Le stockage actuel est SQLite via un chemin local configurable.
- La limitation de débit est en mémoire et par adresse cliente ; elle n'est pas adaptée telle quelle à plusieurs instances.
- La limite actuelle vérifie l'en-tête Content-Length annoncé ; elle ne constitue pas une limite complète des corps reçus en flux/chunked.
- Les en-têtes de sécurité de base sont présents : X-Content-Type-Options, X-Frame-Options, Referrer-Policy et Cache-Control.
- Les actions externes et les capacités de publication Telegram restent désactivées.

Ces points proviennent de la revue du code et ne constituent pas un test d'intrusion en production.

## Bloquants avant exposition publique

1. Ajouter une authentification serveur robuste et une gestion de session sécurisée.
2. Ajouter protection CSRF pour les requêtes authentifiées par cookie et validation stricte de l'origine.
3. Définir CORS sur l'origine exacte de production.
4. Appliquer des limites de taille réelles au niveau ASGI et/ou du proxy, y compris pour les corps sans Content-Length.
5. Remplacer la limitation en mémoire par une stratégie adaptée au déploiement et à ses instances.
6. Choisir une base persistante et vérifier sauvegarde/restauration.
7. Protéger les journaux et vérifier qu'aucun secret ou contenu privé n'y est enregistré.
8. Garder Telegram sans token et sans envoi jusqu'à validation indépendante de ses permissions et de ses confirmations humaines.

Ne pas retirer le garde-fou local pour « faire fonctionner » un hébergement public. Ne pas publier le backend tant que les points ci-dessus ne sont pas traités et testés.

## Contrôles prévus après publication

### Contrôles passifs et non destructifs
- HTTPS, certificat, redirections HTTP vers HTTPS et en-têtes de sécurité.
- Pages publiques, fichiers statiques, manifest PWA et service worker.
- Exposition involontaire de fichiers de configuration, sauvegardes, dépôts ou secrets.
- Messages d'erreur : absence de traces internes, chemins locaux et détails sensibles.
- Configuration CORS et méthodes HTTP autorisées.

### Contrôles fonctionnels avec comptes de test
- Un visiteur non authentifié ne peut lire ni modifier les données privées.
- Une session valide fonctionne ; une session expirée ou révoquée est refusée.
- Les origines non autorisées et les requêtes sans jeton CSRF valide sont refusées.
- Les permissions restent en refus par défaut.
- L'arrêt d'urgence bloque les fonctions prévues sans supprimer les données.
- Les identifiants et données d'un compte de test ne sont pas accessibles depuis un autre compte de test.

### Vérifications API à faible impact
- Validation des champs, formats et tailles d'entrée.
- Réponses correctes pour les méthodes non autorisées et ressources absentes.
- Limitation de débit avec un faible volume de requêtes.
- Absence de fuite de token dans les réponses et journaux.
- Aucune action Telegram réelle : utiliser des réponses simulées ou un bot de test sans audience.

## Procédure et rapport

1. Confirmer l'URL exacte et que le propriétaire autorise les tests sur cette cible.
2. Définir une fenêtre de test à faible trafic et utiliser des comptes/données fictifs.
3. Commencer par les contrôles passifs, puis les tests fonctionnels authentifiés.
4. Arrêter immédiatement en cas d'instabilité, d'accès à des données réelles non nécessaires ou d'effet inattendu.
5. Documenter chaque constat avec gravité, preuve minimale non sensible, impact, correction et statut de vérification.
6. Corriger les constats critiques/élevés avant d'activer les fonctionnalités externes.

## Échelle de gravité

- **Critique** : compromission complète ou exposition massive de données ; publication bloquée.
- **Élevée** : accès non autorisé à des données/actions importantes ; correction avant ouverture publique.
- **Moyenne** : impact limité ou conditions d'exploitation spécifiques ; correction prioritaire.
- **Faible** : durcissement recommandé sans impact direct important.
- **Information** : amélioration ou observation sans vulnérabilité démontrée.

Un contrôle non effectué est marqué « non testé », jamais « réussi ». Une absence de vulnérabilité trouvée ne garantit pas une sécurité absolue.
