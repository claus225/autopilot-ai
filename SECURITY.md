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

**Limites connues :** ce mécanisme protège le chat et l'interface locale contre les nouvelles demandes, mais ne constitue pas encore un coupe-circuit universel pour des automatisations futures. Les automatisations du navigateur et le contrôle du PC restent absents et désactivés. L'API n'a pas encore d'authentification : elle doit rester locale et ne pas être exposée directement sur Internet.

## Signaler une vulnérabilité

Ne publiez pas de secret ni de détail exploitable dans une issue publique. Contactez le propriétaire du dépôt via les moyens privés de GitHub.

## Données

Le prototype ne doit pas recevoir de données personnelles sensibles. Les données de test doivent être fictives.
