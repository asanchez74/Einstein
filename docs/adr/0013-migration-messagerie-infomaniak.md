# ADR-0013 — Migration de la messagerie vers Infomaniak

- **Statut :** proposé
- **Date :** 2 novembre 2026

## Contexte

La messagerie `@chantevigne.com` est hébergée sur le NAS (Synology MailPlus
Server), les contacts dans Synology Contacts. L'incident du
[1er novembre 2026](../incidents/2026-11-01-suppression-volume1.md) a montré les
limites de ce choix :

- messagerie coupée plus d'une heure, base Contacts perdue ;
- MailPlus dépend de PostgreSQL, Perl, PHP et Node.js : chaque panne du NAS
  devient une panne de messagerie ;
- ports 25, 465, 587, 993 et 995 exposés sur Internet vers le NAS qui contient
  tous les documents ;
- envoi depuis une IP résidentielle (`193.164.25.214`, PTR générique
  `…sefanet.net`) défavorable à la délivrabilité.

État relevé le 2 novembre 2026 :

| Élément | Valeur |
|---|---|
| Domaine, DNS public | Namecheap (`dns1/dns2.registrar-servers.com`) |
| MX | `10 mail.chantevigne.com` → `193.164.25.214` |
| SPF | `v=spf1 +a +mx -all` |
| DMARC | `v=DMARC1; p=reject; pct=100` |
| DKIM | sélecteur `s1` (clé MailPlus, trouvée le 5 novembre 2026 dans Namecheap) |
| Boîtes actives | tonio (4,5 Go), mimi (8,0 Go), clara et nono (quasi vides) |
| Volume MailPlus | 22 Go au total (`/volume1/@MailPlus-Server`) |
| Alias, listes, groupes | aucun relevé le 2 novembre ; 5 alias de comptes trouvés ensuite (voir Avancement) |
| Contacts | 1 488 dans Synology Contacts (CardDAV) |
| Agendas | iCloud (Synology Calendar non utilisé) |

## Décision

- Héberger la messagerie chez **Infomaniak** (Suisse), sur le domaine
  `chantevigne.com` : boîtes tonio, mimi, clara, nono, puis une boîte
  famille/maison.
- **Contacts et agendas dans iCloud** (révisé le 6 novembre 2026, initialement
  contacts chez Infomaniak) : mimi, clara et nono y ont déjà leurs contacts et
  tous les agendas y sont ; seul tonio utilisait Synology Contacts. iCloud+
  (2 To, partage familial) reste de toute façon utilisé pour les photos et les
  sauvegardes, et iOS/macOS n'exigent alors aucun compte CardDAV ni réglage de
  compte par défaut. Une sortie éventuelle d'Apple serait un projet distinct,
  avec sa propre ADR.
- Garder le domaine et le DNS chez **Namecheap** ; seuls les enregistrements
  liés au courrier changent.
- Après rodage, fermer les ports mail sur la FRITZ!Box et désinstaller
  MailPlus Server, MailPlus et Synology Contacts.

Alternative écartée : Proton Mail (chiffrement de bout en bout, mais plus cher
et moins bien intégré à Mail, Contacts et Calendrier d'Apple).

## Plan de migration

1. **Préparation.** Commander le Service Mail Infomaniak (5 adresses), y
   déclarer `chantevigne.com`, créer les boîtes. Aucun relevé ni client POP3
   n'est utilisé (confirmé le 2 novembre 2026) : IMAP seulement. Abaisser à 300 s le TTL des
   enregistrements MX, SPF et `mail` chez Namecheap, au moins 24 h avant la
   bascule.
2. **Première copie.** Copier l'historique IMAP de MailPlus vers Infomaniak
   (outil d'import d'Infomaniak ou `imapsync`), boîte par boîte.
3. **Bascule DNS** chez Namecheap : remplacer le MX par `5 mta-gw.infomaniak.ch`.
   SPF, DKIM et `autoconfig`/`autodiscover` sont publiés à l'avance (voir
   Avancement) ; DMARC reste en `p=reject`. Ne jamais publier un SPF sans
   Infomaniak tant que DMARC est en `p=reject`.
4. **Seconde copie** pour rattraper les messages reçus par MailPlus pendant la
   propagation DNS.
5. **Clients.** Reconfigurer Mail, Contacts et réglages sur Mac et iPhone
   (IMAP/SMTP Infomaniak). Exporter Synology Contacts en vCard (garder le
   fichier en sauvegarde), l'importer dans iCloud, puis retirer le compte
   CardDAV du NAS des appareils de tonio.
6. **Contrôles.** Envoi et réception depuis et vers Gmail et iCloud, en-têtes
   SPF, DKIM et DMARC `pass`, réception sur chaque appareil.
7. **Rodage** d'au moins deux semaines, MailPlus laissé actif en lecture.
8. **Démantèlement.** Sauvegarde finale de MailPlus et Contacts (Hyper Backup),
   fermeture des ports 25, 465, 587, 993 et 995 sur la FRITZ!Box, désinstallation
   des paquets, suppression de l'enregistrement `mail.chantevigne.com` s'il n'a
   plus d'usage. SPF final `v=spf1 include:spf.infomaniak.ch -all`, suppression
   de la clé DKIM `s1._domainkey` de MailPlus.

Retour arrière avant l'étape 8 : remettre l'ancien MX et l'ancien SPF chez
Namecheap ; MailPlus reçoit de nouveau le courrier.

## Coûts

Service Mail Infomaniak pour 5 adresses : **CHF 2,50 par mois** (tarif relevé
par le propriétaire le 2 novembre 2026), soit CHF 30 par an. Avec Swiss Backup
(CHF 6,02 par mois), l'ensemble messagerie et sauvegarde hors site coûte
environ CHF 8,50 par mois.

## Conséquences

- La messagerie ne dépend plus du NAS ni de la connexion du domicile.
- Moins de ports exposés et moins de paquets à maintenir sur le NAS ; PostgreSQL
  n'y sert plus qu'aux paquets restants.
- La [stratégie de sauvegarde](0014-strategie-sauvegarde-3-2-1.md) n'a plus à
  couvrir la messagerie.
- Les mails (Infomaniak) et les contacts (iCloud) dépendent de prestataires
  externes : conserver une exportation périodique des contacts et une copie IMAP
  locale ou Hyper Backup si un historique hors Infomaniak est souhaité.

## Avancement

Valeurs du Manager Infomaniak (Diagnostic DNS, 5 novembre 2026) :

| Enregistrement | Valeur |
|---|---|
| MX | `5 mta-gw.infomaniak.ch` |
| SPF | `include:spf.infomaniak.ch` |
| DKIM | sélecteur `20261105` (RSA 2048 bits) |
| `autoconfig`, `autodiscover` | CNAME `infomaniak.com.` |

- **5 novembre 2026.** Service Mail commandé, domaine déclaré, boîtes tonio,
  mimi, clara et nono créées, alias `antonio.sanchez` sur tonio. TTL du MX et du
  SPF à 5 min chez Namecheap. Publiés sans effet sur la réception (vérifiés par
  `dig`) : DKIM `20261105._domainkey`, CNAME `autoconfig` et `autodiscover`, SPF
  transitoire `v=spf1 +a +mx include:spf.infomaniak.ch -all` (NAS et
  Infomaniak autorisés). MX inchangé.
- **6 novembre 2026.** Premier import IMAP (outil d'import Infomaniak, source
  `mail.chantevigne.com:993`) : clara, nono, tonio, puis mimi (07:22–07:50,
  ~6 Mo/s, attente disque du NAS < 1). MX basculé à 07:57, puis remis à
  `mail.chantevigne.com` à ~08:05 : l'alias `antonio.sanchez` était refusé par
  Infomaniak (`550 User unknown`) car il servait d'identifiant de connexion au
  compte Infomaniak. Identifiant changé pour une adresse hors `chantevigne.com`
  (évite qu'une panne de messagerie bloque la récupération du compte), alias
  recréés, chaque adresse testée par `RCPT TO` sur `mta-gw.infomaniak.ch` sans
  envoi. MX définitivement basculé à 08:12.

Alias (oubliés au relevé du 2 novembre, définis dans les comptes MailPlus) :

| Boîte | Alias |
|---|---|
| tonio | `antonio.sanchez` |
| mimi | `mireille.sanchez` |
| clara | `clara.sanchez` |
| nono | `noemie`, `noemie.sanchez` |

Validation le 6 novembre 2026 : envoi Infomaniak → Microsoft 365 (eduvaud.ch)
avec `spf=pass`, `dkim=pass` (`s=20261105`), `dmarc=pass`, SCL 1 ; réponse
reçue chez Infomaniak (MX suivi par un expéditeur extérieur). Seconde copie IMAP
des 4 boîtes faite après la bascule (dernière livraison MailPlus 08:10:36).
Mac et iPhone de tonio reconfigurés (IMAP 143 et SMTP 587 avec STARTTLS,
expéditeur par défaut `antonio.sanchez@`), ancien compte désactivé, non
supprimé.

iPad de tonio, iPhone et Mac de mimi reconfigurés le même jour ; aucun message
livré par MailPlus après la bascule. Restent les iPhone et sessions Mac de clara
et nono.

Contacts de tonio passés dans iCloud le 6 novembre 2026. Synology Contacts n'en
affichait plus que 757 (export `.vcf` incomplet) contre 1 488 le 1er novembre ;
la copie locale du compte CardDAV sur le Mac en gardait 1 490. Méthode : compte
CardDAV désactivé, puis réactivé **réseau coupé** (sinon la synchronisation
aurait aligné la copie locale sur le serveur), export vCard, compte désactivé,
réseau rétabli, import dans iCloud avec mise à jour des doublons. Résultat :
1 769 fiches iCloud, les 1 490 du NAS retrouvées par comparaison des bases
locales. Archives dans `Documents/03_Tonio/Administratif/Archives contacts -
06112026` (archive `.abbu` complète du Mac).

Démantèlement anticipé en deux temps, étape A (réversible) le 6 novembre 2026 :

- notifications DSM basculées sur `mail.infomaniak.com:587` (STARTTLS, compte
  `tonio@chantevigne.com`) ; elles passaient par MailPlus, seul expéditeur local
  du NAS (aucun envoi `sendmail`/PHP) ; courriel de test reçu ;
- sauvegarde Hyper Backup finale de MailServerPlus réussie ;
- redirections 25, 465, 587, 993 et 995 retirées de la FRITZ!Box ; ports
  fermés sur l'adresse publique (test depuis le LAN) ;
- paquets arrêtés, non désinstallés : MailPlus Server, MailPlus, Synology
  Contacts, Synology Calendar (dépendant de Contacts, inutilisé), Note Station
  (vide). Mémoire utilisée 3,4 → 2,0 Go, disponible 3,9 → 5,3 Go, swap occupé
  3,1 → 1,25 Go.

Hors messagerie, le même jour : redirection 6690 (Synology Drive Client) retirée
de la FRITZ!Box. Depuis l'extérieur, la synchronisation Drive passe par le VPN
(OpenVPN 1194) ; sur le LAN, les clients joignent `192.168.1.3` directement.
Redirections restantes : 443, 80, 1194 (UDP).

Retour arrière jusqu'à l'étape B : redémarrer les paquets, rétablir les
redirections, remettre l'ancien MX.

Étape B (définitive), vers le 20 novembre 2026 : désinstaller les paquets,
supprimer la tâche Hyper Backup MailServerPlus et retirer les applications
MailPlus des tâches Swiss Backup et DS212j, SPF final
`v=spf1 include:spf.infomaniak.ch -all`, suppression de `s1._domainkey` et du
CNAME `mail` chez Namecheap, mise à jour de l'ADR-0014.

**Dépendance critique :** l'identifiant Apple du propriétaire est
`antonio.sanchez@chantevigne.com`. Les codes et la récupération du compte Apple
passent par cet alias : ne jamais le supprimer ni laisser expirer le domaine.

Contrôle d'une adresse sans envoyer de message : session SMTP sur
`mta-gw.infomaniak.ch:25`, `MAIL FROM:<>` puis `RCPT TO:<adresse>` ; `250` =
acceptée, `550 5.1.1` = inconnue. Toujours tester toutes les adresses avant de
changer un MX.

Ordre retenu : mettre en place la sauvegarde hors site
([ADR-0014](0014-strategie-sauvegarde-3-2-1.md)) avant la migration.
