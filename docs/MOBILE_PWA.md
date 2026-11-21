# Utiliser AutoPilot AI sur mobile

## Installation PWA

La version web possède un manifeste et un service worker. **L'installation mobile sera possible après publication du site sur une adresse HTTPS** (le dépôt GitHub seul n'est pas une application installable).

- **Android / Chrome :** ouvre le site publié, puis le menu ⋮ et choisis **Installer l'application** ou **Ajouter à l'écran d'accueil**. Le libellé dépend de la version de Chrome.
- **iPhone / Safari :** ouvre le site, touche **Partager**, puis **Sur l'écran d'accueil** si cette option est proposée.
- Si l'option d'installation n'apparaît pas, vérifie que le site est publié en HTTPS et que le navigateur prend en charge l'installation PWA.

Quand le navigateur déclenche l'événement d'installation, le bouton **Installer** apparaît dans l'en-tête. Certains navigateurs ne déclenchent pas cet événement ; les étapes manuelles ci-dessus restent alors utiles.

## Fonctionnement hors connexion

Le service worker met en cache la coque de l'interface et certaines ressources statiques après une première visite en ligne. Cela peut permettre d'ouvrir l'interface lorsque le réseau est indisponible.

**Limite importante :** les données et fonctions nécessitant l'API Python ne sont pas disponibles hors connexion. Les requêtes API ne sont jamais mises en cache. Le backend doit être démarré et joignable pour créer ou consulter les tâches, utiliser le chat ou modifier les réglages de sécurité.

## État de validation

Les modifications PWA et l'interface d'installation passent les deux derniers workflows CI GitHub. Cela confirme les contrôles automatisés du dépôt, mais ne remplace pas un essai réel sur Chrome Android et Safari iOS.

Le projet n'est pas encore déployé publiquement. L'API reste locale uniquement et l'URL frontend par défaut pointe vers `127.0.0.1` ; une architecture backend adaptée et une authentification devront être conçues avant toute publication publique.
