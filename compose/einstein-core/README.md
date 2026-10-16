# Einstein Core

Premier service applicatif de la plateforme Einstein : API FastAPI sans état.

## Endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `GET /docs`

## Documentation opérationnelle

Voir le [guide d'exploitation](../../docs/einstein-core-operations.md) pour la
configuration, le déploiement NAS, les contrôles HTTP, le reverse proxy VPN,
les logs, le redémarrage et le périmètre des données et secrets.

Le développement local et les tests sont décrits dans le
[README du projet](../../README.md).

Par défaut, le port Docker est publié sur `127.0.0.1:18081` du NAS. L'accès
HTTPS prévu est `https://einstein.chantevigne.com`, via le reverse proxy DSM
avec accès autorisé depuis le LAN et le VPN, sans accès Internet. Le guide distingue les validations antérieures des
contrôles restant à consigner pour la clôture du Sprint 3.
