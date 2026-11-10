# Homebridge

Pont HomeKit du NAS : plugins Hue, Google Smart Home et KNX (via `eibd` sur
le DS212j `192.168.1.4`). Décision et limites :
[ADR-0015](../../docs/adr/0015-homebridge-compose.md).

| Élément | Valeur |
|---|---|
| Conteneur | `homebridge`, réseau `host` |
| Image | `homebridge/homebridge:synology-2026-11-02` (Ubuntu 22.04, Node 24) |
| Données | `/volume1/docker/Homebridge` (inchangé depuis l'ancien conteneur) |
| Interface | `http://192.168.1.3:8080` (port de la plateforme `config`) |
| Pont principal | `Homebridge 9045`, port 52891 ; ponts enfants KNX, Hue, Google |

Plugins et version de Homebridge sont dans `/volume1/docker/Homebridge/package.json`
et installés par npm à chaque démarrage du conteneur ; ils se mettent à jour
depuis l'interface, pas par l'image.

## Migration depuis le conteneur DSM `Homebridge` (oznu)

À faire une fois, sur le NAS, depuis le clone à jour (`git pull --ff-only`).
L'identité HomeKit est dans `persist/` : pas de nouvel appairage.

```bash
cd ~/Development/Einstein

# 1. Configuration locale
cp compose/homebridge/.env.example compose/homebridge/.env
chmod 600 compose/homebridge/.env

# 2. Aperçu : l'ancien conteneur et sa politique de redémarrage
sudo docker inspect --format '{{.Name}} {{.Config.Image}} {{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}}' Homebridge

# 3. Arrêt de l'ancien conteneur, sans le supprimer, et sans redémarrage au boot
#    (sinon deux Homebridge avec la même identité HomeKit après un redémarrage du NAS)
sudo docker stop Homebridge
sudo docker update --restart=no Homebridge

# 4. Sauvegarde des données, conteneur arrêté
sudo scripts/backup-stack.sh homebridge

# 5. Démarrage du nouveau conteneur
sudo scripts/stack-up.sh homebridge
```

### Vérifications

```bash
scripts/stack-status.sh homebridge         # healthy après quelques minutes
scripts/stack-logs.sh homebridge --tail 80 # pas de « s6-rc: fatal: timed out »
grep -E 'is running on port|ERROR' /volume1/docker/Homebridge/homebridge.log | tail
```

Puis, dans l'app Maison de l'iPhone, les accessoires Hue répondent.

### Retour arrière

```bash
sudo docker stop homebridge
sudo docker update --restart=always Homebridge
sudo docker start Homebridge
```

L'ancien conteneur reste disponible tant qu'il n'a pas été supprimé (DSM,
Container Manager) ; ne le supprimer qu'après quelques jours sans problème.

## Mise à jour Homebridge et KNX

Après la migration, dans l'interface (onglet Plugins) :

1. vérifier que `eibd` répond sur le DS212j (depuis le NAS :
   `timeout 3 bash -c '</dev/tcp/192.168.1.4/6720' && echo ouvert`) ;
2. mettre à jour **Homebridge** vers 2.5.0 (requis par `homebridge-hue` ≥ 2.4.0) ;
3. mettre à jour **homebridge-knx** vers 0.6.0 (compatibilité Homebridge 2) ;
4. redémarrer Homebridge et vérifier dans `homebridge.log` que le pont
   `Homebridge Knx` démarre avec ses 7 accessoires.

Sauvegarde avant chaque mise à jour : `sudo scripts/backup-stack.sh homebridge`.

## Exploitation

- **Image.** Changer le tag daté dans `compose.yaml`, committer, puis
  `sudo scripts/stack-up.sh homebridge`. Rester sur la ligne `synology`.
- **Santé.** Le healthcheck interroge l'interface ; Docker ne redémarre pas
  un conteneur `unhealthy`, il le signale seulement.
- **Sauvegardes.** Homebridge fait sa propre sauvegarde à 04:00 dans
  `backups/instance-backups/` ; `homebridge-knx.startlog` (10 Mo) en est exclu.
