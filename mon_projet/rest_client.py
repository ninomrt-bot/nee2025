# rest_client.py ───────────────────────────────────────────────
import requests, json, pathlib
import os
from opcua_client import send_order_details
from opcua_client import pulse_bit, NODE_VALIDATE_P4


API = os.getenv("LGN_API", "http://127.0.0.1:5000/api")  # ← IP du Pi + port exposé
CACHE    = pathlib.Path("/tmp/of_cache.json")
TIMEOUT  = 3

# --- helpers -------------------------------------------------- #
def _get(url):
    r = requests.get(f"{API}{url}", timeout=TIMEOUT); r.raise_for_status()
    return r.json()

def _post(url, payload=None):
    r = requests.post(f"{API}{url}", json=payload, timeout=TIMEOUT)
    return r

# --- liste OF (avec cache) ----------------------------------- #
def get_of_list_cached():
    try:
        data = _get("/orders")["orders"]
        CACHE.write_text(json.dumps(data)); return data
    except Exception as e:
        print("[REST] fallback cache:", e)
        return json.loads(CACHE.read_text()) if CACHE.exists() else []

# --- composants ---------------------------------------------- #
def get_of_components(of_num):
    return _get(f"/orders/components?of_name={of_num}")["components"]

# --- statut des îlots ---------------------------------------- #
def status():
    return _get("/status")["ilots"]

# --- démarrer un OF ------------------------------------------ #
def start(ilot, of_number, code, qty, date_str):
    print(f"[DEBUG] Envoi OF: ilot={ilot}, of={of_number}, code={code}, qty={qty}, date={date_str}")
    return send_order_details(ilot, of_number, code, qty, date_str)

def start(ilot, of_number, code, qty):
    print(f"[DEBUG] Envoi OF: ilot={ilot}, of={of_number}, code={code}, qty={qty}")

    ok = send_order_details(ilot, of_number, code, qty)

    if ok:
        pulse_bit(ilot, NODE_VALIDATE_P4)  # ⚡ impulsion de 1s
    return ok



# --- simple ping --------------------------------------------- #
def can_connect_to_rest():
    try:
        _get("/test"); return True
    except Exception:  return False
