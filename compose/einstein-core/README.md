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

## Accès sécurisé

- API : `https://einstein.chantevigne.com`
- Documentation OpenAPI : `https://einstein.chantevigne.com/docs`
- Reverse proxy : Synology DSM vers `127.0.0.1:18081`
- Accès autorisé uniquement depuis le réseau OpenVPN `10.8.0.0/24`
- Accès hors VPN testé et refusé

