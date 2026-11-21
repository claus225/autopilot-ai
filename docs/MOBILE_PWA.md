# Utiliser AutoPilot AI sur mobile

## Installation PWA

La version web possède un manifeste et un service worker. Une fois l'application publiée sur une origine HTTPS, ouvre-la dans Chrome sur Android, puis utilise le menu du navigateur et choisis **Installer l'application** ou **Ajouter à l'écran d'accueil** (le libellé varie selon Chrome).

## Fonctionnement hors connexion

Le service worker met en cache la coque de l'interface et les ressources statiques déjà consultées. Cela peut permettre d'ouvrir l'interface après une première visite en ligne.

**Limite importante :** les données et fonctions nécessitant l'API Python ne sont pas disponibles hors connexion. Les requêtes API ne sont jamais mises en cache. Le backend doit être démarré et joignable pour créer ou consulter les tâches, utiliser le chat ou modifier les réglages de sécurité.

## État de validation

L'intégration PWA est ajoutée au dépôt, mais elle doit encore être vérifiée par le workflow CI puis testée dans Chrome Android après publication HTTPS. Le projet n'est pas encore déployé publiquement et l'API reste locale uniquement.
