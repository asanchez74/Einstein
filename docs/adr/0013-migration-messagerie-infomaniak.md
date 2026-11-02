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
| DKIM | aucun sélecteur trouvé (`default`, `mail`, `synology`, `dkim`) |
| Boîtes actives | tonio (4,5 Go), mimi (8,0 Go), clara et nono (quasi vides) |
| Volume MailPlus | 22 Go au total (`/volume1/@MailPlus-Server`) |
| Alias, listes, groupes | aucun |
| Contacts | 1 488 dans Synology Contacts (CardDAV) |
| Agendas | iCloud (Synology Calendar non utilisé) |

## Décision

- Héberger la messagerie chez **Infomaniak** (Suisse), sur le domaine
  `chantevigne.com` : boîtes tonio, mimi, clara, nono, puis une boîte
  famille/maison.
- Y migrer aussi les **contacts** (CardDAV). Les agendas restent pour
  l'instant dans l'écosystème Apple (iCloud).
- Garder le domaine et le DNS chez **Namecheap** ; seuls les enregistrements
  liés au courrier changent.
- Après rodage, fermer les ports mail sur la FRITZ!Box et désinstaller
  MailPlus Server, MailPlus et Synology Contacts.

Alternative écartée : Proton Mail (chiffrement de bout en bout, mais plus cher
et moins bien intégré à Mail, Contacts et Calendrier d'Apple).

## Plan de migration

1. **Préparation.** Commander le Service Mail Infomaniak (5 adresses), y
   déclarer `chantevigne.com`, créer les boîtes. Vérifier dans MailPlus si des
   utilisateurs relèvent des comptes POP3 externes (option activée sur le
   serveur) et quels appareils utilisent POP3. Abaisser à 300 s le TTL des
   enregistrements MX, SPF et `mail` chez Namecheap, au moins 24 h avant la
   bascule.
2. **Première copie.** Copier l'historique IMAP de MailPlus vers Infomaniak
   (outil d'import d'Infomaniak ou `imapsync`), boîte par boîte.
3. **Bascule DNS** chez Namecheap, avec les valeurs fournies par le Manager
   Infomaniak : MX, SPF (remplacer `+a +mx` par l'inclusion Infomaniak), DKIM
   (nouvel enregistrement), DMARC conservé en `p=reject` une fois SPF et DKIM
   vérifiés. Ne jamais publier un SPF sans Infomaniak tant que DMARC est en
   `p=reject`.
4. **Seconde copie** pour rattraper les messages reçus par MailPlus pendant la
   propagation DNS.
5. **Clients.** Reconfigurer Mail, Contacts et réglages sur Mac et iPhone
   (IMAP/SMTP Infomaniak). Importer les contacts (vCard) dans Infomaniak.
6. **Contrôles.** Envoi et réception depuis et vers Gmail et iCloud, en-têtes
   SPF, DKIM et DMARC `pass`, réception sur chaque appareil.
7. **Rodage** d'au moins deux semaines, MailPlus laissé actif en lecture.
8. **Démantèlement.** Sauvegarde finale de MailPlus et Contacts (Hyper Backup),
   fermeture des ports 25, 465, 587, 993 et 995 sur la FRITZ!Box, désinstallation
   des paquets, suppression de l'enregistrement `mail.chantevigne.com` s'il n'a
   plus d'usage.

Retour arrière avant l'étape 8 : remettre l'ancien MX et l'ancien SPF chez
Namecheap ; MailPlus reçoit de nouveau le courrier.

## Coûts

Service Mail Infomaniak pour 5 adresses : de l'ordre de quelques CHF par mois
(sources tierces divergentes, entre ~1,50 € et ~7,30 CHF par mois). À confirmer
dans le Manager lors de la commande.

## Conséquences

- La messagerie ne dépend plus du NAS ni de la connexion du domicile.
- Moins de ports exposés et moins de paquets à maintenir sur le NAS ; PostgreSQL
  n'y sert plus qu'aux paquets restants.
- La [stratégie de sauvegarde](0014-strategie-sauvegarde-3-2-1.md) n'a plus à
  couvrir la messagerie.
- Les mails et contacts dépendent d'un prestataire externe : conserver une
  exportation périodique des contacts et une copie IMAP locale ou Hyper Backup
  si un historique hors Infomaniak est souhaité.

## Points à confirmer

- Valeurs exactes MX, SPF et DKIM dans le Manager Infomaniak.
- Relevés POP3 externes configurés dans MailPlus, et appareils en POP3.
