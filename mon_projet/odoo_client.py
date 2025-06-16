# odoo_client.py ──────────────────────────────────────────────────
import xmlrpc.client
from typing import List, Dict
from config import ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS

def _connect():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid    = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    if not uid:
        raise RuntimeError("⛔️  Authentification Odoo impossible")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

# Liste OF
def list_orders() -> List[Dict]:
    uid, models = _connect()
    raws = models.execute_kw(
        ODOO_DB, uid, ODOO_PASS,
        'mrp.production', 'search_read',
        [[]],
        {'fields': ['name', 'product_id', 'product_qty', 'state', 'bom_id'],
         'limit': 100, 'order': 'id desc'}
    )

    def _bom_code(bom_id: int | None):
        if not bom_id:
            return "?"
        [rec] = models.execute_kw(
            ODOO_DB, uid, ODOO_PASS,
            'mrp.bom', 'read', [bom_id],
            {'fields': ['code']}
        )
        return rec.get("code") or "?"

    return [{
        "numero":   r['name'],
        "code":     f"{r['product_id'][1] if r['product_id'] else 'Article ?'} ({_bom_code(r.get('bom_id') and r['bom_id'][0])})",
        "quantite": r['product_qty'],
        "etat":     r['state']
    } for r in raws]

# Composants d’un OF
def list_components(of_name: str) -> List[str]:
    uid, models = _connect()
    recs = models.execute_kw(
        ODOO_DB, uid, ODOO_PASS,
        'mrp.production', 'search_read',
        [[['name', '=', of_name]]],
        {'fields': ['move_raw_ids'], 'limit': 1}
    )
    if not recs:
        return [f"OF '{of_name}' introuvable"]

    move_ids = recs[0]['move_raw_ids']
    if not move_ids:
        return ["Aucun composant"]

    moves = models.execute_kw(
        ODOO_DB, uid, ODOO_PASS,
        'stock.move', 'read', [move_ids],
        {'fields': ['product_id', 'product_uom_qty']}
    )
    return [f"{m['product_id'][1]} x{m['product_uom_qty']}" for m in moves]