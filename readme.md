# Projet NEE-202504 – Poste de Pilotage LGN-04

Ce dépôt contient le code et l'infrastructure logicielle du **poste de pilotage** du projet **NEE-202504**, développé pour interconnecter les réseaux **OT (automates industriels)** et **IT (serveur ERP Odoo)**.

##  Objectifs du projet

- Lire dynamiquement les **Ordres de Fabrication (OF)** depuis Odoo (via XML-RPC).
- Afficher les OF dans une **IHM en Tkinter**.
- Envoyer un OF vers les **automates WAGO (réseau OT)** via **OPC UA**.
- Écrire les données suivantes dans l'automate :
  - Numéro d'OF (extrait de `WH/MO/00017` → `17`)
  - Code produit (extrait de `Assemblage (27)` → `27`)
  - Quantité
  - Bit de validation temporaire `BP_Vld_OF_P4` (impulsion de 1s)
  - Rôle utilisateur (opérateur / maintenance)
- Restreindre l'accès à certaines pages en fonction du badge RFID scanné.

##  Architecture

```text
[Odoo ERP] (IT) 
     ┗━━━ XML-RPC ━━━━━┓
                       |
                   [API Flask REST] → Tkinter (IHM)
                       |
        OPC UA         ┗━━━━━━━━━━━━━┓
                  [Automate WAGO] (OT)
```

##  Technologies

- **Python 3.11**
- **Flask** (API REST interne)
- **Tkinter** (IHM locale)
- **freeopcua** (client OPC UA)
- **xmlrpc.client** (connexion Odoo)
- **Docker / Portainer** pour déploiement en réseau isolé

##  Structure du projet

```
mon_projet/
├── app.py               # API REST principale
├── hmi.py               # IHM Tkinter
├── opcua_client.py      # Connexion OPC-UA (automates)
├── odoo_client.py       # Connexion XML-RPC à Odoo
├── rest_client.py       # Wrapper entre IHM et API
├── config.py            # Variables globales
├── routes.py            # Endpoints Flask
├── requirements.txt     # Dépendances
├── Dockerfile           # Build container local
├── docker-compose.yml   # Stack de déploiement
```

##  Exemples OPC UA

```python
# Envoi de l'OF
send_order_details("LGN01", "WH/MO/00017", "Assemblage (27)", 2)

# Active le bit de validation 1 seconde
pulse_bit("LGN01", NODE_VALIDATE_P4)

# Écrit le rôle utilisateur (1 = opérateur, 2 = maintenance)
push_user("LGN01", 1)
```

##  Environnement réseau

- **Raspberry Pi** connecté en Wi-Fi au réseau **IT** pour accéder à Odoo
- **OPC UA** sur le réseau **Indus (OT)** pour écrire vers les automates
- Accès aux deux via route statique ou conteneur inter-réseau

##  Limitations

- Utilisation locale uniquement (non accessible depuis l'externe)

##  Auteurs

Projet réalisé dans le cadre de la formation *Expert en numerique et informatique* pour le client **UIMM / NEE Electronics**.

**Développeur principal** : Nino marquet (Groupe C)

---

