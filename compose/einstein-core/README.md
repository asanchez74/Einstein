# Einstein Core

Premier service applicatif de la plateforme Einstein.

## Endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `GET /docs`

## Déploiement sur le NAS

```bash
cd ~/Development/Einstein/compose/einstein-core
cp .env.example .env
chmod 600 .env

cd ~/Development/Einstein
./scripts/stack-up.sh einstein-core
```

Le service écoute uniquement sur `127.0.0.1:18081`.
