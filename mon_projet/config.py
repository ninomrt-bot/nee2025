# config.py ────────────────────────────────────────────────────
import os, json
from dotenv import load_dotenv

load_dotenv()

ODOO_URL  = os.getenv("ODOO_URL",  "http://10.10.0.10:9060")
ODOO_DB   = os.getenv("ODOO_DB",   "NEE")
ODOO_USER = os.getenv("ODOO_USER", "OperateurC@nee.com")
ODOO_PASS = os.getenv("ODOO_PASS", "nee25Codoo!")

# un endpoint par îlot ▼
OPCUA_ENDPOINT = {
    "LGN01": "opc.tcp://172.30.30.120:4840",
    "LGN02": "opc.tcp://172.30.30.130:4840",
    "LGN03": "opc.tcp://172.30.30.140:4840",
}
