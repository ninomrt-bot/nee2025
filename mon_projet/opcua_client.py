# opcua_client.py ────────────────────────────────────────────────
"""
Wrapper "friendly" autour de la librairie *freeopcua*.
─ Gestion de plusieurs îlots : LGN01 / LGN02 / LGN03
─ Lecture / écriture de tags (NodeId)
─ Fonctions utilitaires : start_order, send_order_details + get_states
"""

from __future__ import annotations
import os
from dotenv import load_dotenv
from opcua import Client, ua
import time

ROLE_UNKNOWN, ROLE_OPERATOR, ROLE_MAINT = 0, 1, 2
# -----------------------------------------------------------------------------
# 1) Chargement des variables d’environnement (.env facultatif)
# -----------------------------------------------------------------------------
load_dotenv()

# Un endpoint par îlot ▸ surchargeable via `.env`, nettoyage des espaces
OPCUA_ENDPOINTS: dict[str, str] = {
    "LGN01": os.getenv("OPCUA_LGN01", "opc.tcp://172.30.30.110:4840").strip(),
    "LGN02": os.getenv("OPCUA_LGN02", "opc.tcp://172.30.30.120:4840").strip(),
    "LGN03": os.getenv("OPCUA_LGN03", "opc.tcp://172.30.30.130:4840").strip(),
}

# -----------------------------------------------------------------------------
# 2) NodeIds standards (à adapter selon ta config automate)
# -----------------------------------------------------------------------------
NODE_START_ORDER   = (
    "ns=4;"
    "s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL_OPCUA.REF_OF"
)    # OK:  OF
NODE_ORDER_CODE = (
    "ns=4;"
    "s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL_OPCUA.Code_Produit"
)

NODE_ORDER_QTY     =  (
    "ns=4;"
    "s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL_OPCUA.QTS"
)   # quantité
NODE_ORDER_DATE    = "ns=4;s=OrderDate"       # date ou timestamp
NODE_STATE_MACHINE = "ns=2;s=State"           # état machine (0=STOP,1=RUN,2=ALARM...)
NODE_CURRENT_USER_ROLE  = (
    "ns=4;"
    "s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL_OPCUA.Mode_IHM"
)   # quantité
NODE_VALIDATE_P4 = "ns=4;s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL_OPCUA.BP_Vld_OF_P4"


# -----------------------------------------------------------------------------
# 3) Classe bas niveau : connexion + lecture / écriture
# -----------------------------------------------------------------------------
class OPCUAHandler:
    """
    Usage:
        with OPCUAHandler("LGN01") as plc:
            plc.write(NODE_START_ORDER, "WH/MO/00012")
            status = plc.read(NODE_STATE_MACHINE)
    """
    def __init__(self, key_or_url: str) -> None:
        # clé (ex: "LGN01") ou URL complète
        url = OPCUA_ENDPOINTS.get(key_or_url, key_or_url)
        self._client = Client(url)

    def __enter__(self) -> "OPCUAHandler":
        self._client.connect()
        return self

    def __exit__(self, *_exc) -> None:
        self._client.disconnect()

    def write(self, node_id: str, value) -> None:
        node = self._client.get_node(node_id)

        # si on fournit déjà un Variant, on l’utilise tel quel
        if isinstance(value, ua.Variant):
            node.set_value(value); return

        # sinon on adapte dynamiquement au type du nœud
        dtype = node.get_data_type_as_variant_type()
        if isinstance(value, str):
            v = ua.Variant(value, ua.VariantType.String)
        elif isinstance(value, bool):
            v = ua.Variant(value, ua.VariantType.Boolean)
        elif isinstance(value, int):
            # UInt16, Int16, Int32… suivant le PLC
            v = ua.Variant(value, dtype if dtype.name.startswith("UInt") else ua.VariantType.Int32)
        else:
            v = ua.Variant(str(value), ua.VariantType.String)
        node.set_value(v)


    def read(self, node_id: str):
        """Renvoie la valeur brute du nœud."""
        node = self._client.get_node(node_id)
        return node.get_value()

# -----------------------------------------------------------------------------
# 4) Fonctions haut niveau utilisées par l’IHM ou la REST
# -----------------------------------------------------------------------------
def start_order(ilot: str, of_number: str) -> bool:
    """
    Écrit uniquement le numéro d’OF dans le tag StartOrder.
    Retourne True si succès, False sinon.
    """
    try:
        with OPCUAHandler(ilot) as plc:
            plc.write(NODE_START_ORDER, of_number)
        return True
    except Exception as e:
        print(f"[OPCUA] start_order KO sur {ilot}: {e}")
        return False


def send_order_details(ilot: str, of_number: str, code: str, qty: float | int) -> bool:

    try:
        with OPCUAHandler(ilot) as plc:
            # ▶ numéro OF : extraire les 5 derniers chiffres (ex: "WH/MO/00017" → 17)
            of_id = int(of_number[-5:])

            # ▶ code article : extraire chiffre entre parenthèses (ex: "Assemblage (27)" → 27)
            import re
            match = re.search(r"\((\d+)\)", code)
            code_id = int(match.group(1)) if match else 0  # fallback = 0 si pas trouvé

            # ▶ quantité : forcer Int32
            qty_int = int(qty)

            # ▶ écrire dans les nœuds OPC-UA
            plc.write(NODE_START_ORDER, of_id)
            plc.write(NODE_ORDER_CODE, ua.Variant(code_id, ua.VariantType.UInt16))
            plc.write(NODE_ORDER_QTY, qty_int)
            # pas d'envoi de NODE_ORDER_DATE


        return True
    except Exception as e:
        print(f"[OPCUA] send_order_details KO sur {ilot}: {e}")
        return False



def get_states() -> dict[str, str]:
    res: dict[str, str] = {}
    for ilot, url in OPCUA_ENDPOINTS.items():
        try:
            client = Client(url)
            client.connect()
            client.disconnect()
            res[ilot] = "ON"
        except Exception:
            res[ilot] = "OFF"
    return res




def push_user(ilot: str, role: int) -> bool:
    """
    Écrit 0 / 1 / 2 dans CurrentUserRole (UInt16).
    """
    try:
        with OPCUAHandler(ilot) as plc:
            plc.write(NODE_CURRENT_USER_ROLE,
                      ua.Variant(role, ua.VariantType.UInt16))
        return True
    except Exception as e:
        print(f"[OPCUA] push_user KO : {e}")
        return False

def pulse_bit(ilot: str, node_id: str, duration: float = 1.0):
    try:
        with OPCUAHandler(ilot) as plc:
            plc.write(node_id, True)      # 1
            time.sleep(duration)
            plc.write(node_id, False)     # 0
        return True
    except Exception as e:
        print(f"[OPCUA] pulse_bit KO : {e}")
        return False
# -----------------------------------------------------------------------------
# 5) Petit test local
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, pprint
    # usage: python3 opcua_client.py start LGN02 WH/MO/00012
    #        python3 opcua_client.py send LGN02 WH/MO/00012 Code 1 2025-04-29T13:00:00
    if len(sys.argv) >= 3 and sys.argv[1] == "start":
        _, _, ilot, ofn = sys.argv
        print("→ start_order :", start_order(ilot, ofn))
    elif len(sys.argv) == 7 and sys.argv[1] == "send":
        _, _, ilot, ofn, code, qty, date = sys.argv
        ok = send_order_details(ilot, ofn, code, float(qty), date)
        print("→ send_order_details :", ok)
    else:
        pprint.pp(get_states())
