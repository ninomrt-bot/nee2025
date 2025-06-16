from flask import Blueprint, jsonify, request
import datetime
import odoo_client as oc
from opcua_client import start_order as opcua_start, get_states, send_order_details

api_routes = Blueprint("api_routes", __name__)

@api_routes.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "Hello from the NEE-202504 API REST!"})

@api_routes.route("/orders", methods=["GET"])
def list_orders():
    """
    Retourne la liste des ordres de fabrication depuis Odoo.
    """
    try:
        orders = oc.list_orders()
        return jsonify({"orders": orders})
    except Exception as e:
        return jsonify({"error": f"Impossible de lister les OF : {e}"}), 500

@api_routes.route("/orders/components", methods=["GET"])
def list_components():
    """
    Retourne les composants pour un OF donné.
    Paramètre query: of_name
    """
    of_name = request.args.get("of_name")
    if not of_name:
        return jsonify({"error": "paramètre of_name manquant"}), 400
    try:
        components = oc.list_components(of_name)
        return jsonify({"components": components})
    except Exception as e:
        return jsonify({"error": f"Erreur récupération composants : {e}"}), 500

@api_routes.route("/orders/<path:of_num>/start", methods=["POST"])
def start_order_route(of_num):
    data = request.get_json() or {}
    ilot    = data.get("ilot")
    code    = data.get("code")
    qty     = data.get("quantity")
    # si pas de date fournie, on prend maintenant
    date_str = data.get("date") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # validation rapide
    if not all([ilot, code, qty]):
        return jsonify({"error":"ilot, code et quantity sont obligatoires"}), 400

    if send_order_details(ilot, of_num, code, qty, date_str):
        return jsonify({"status":"started","ilot":ilot,"order":of_num}), 200
    else:
        return jsonify({"error":f"Échec envoi OF {of_num} sur {ilot}"}), 500

@api_routes.route("/status", methods=["GET"])
def status_route():
    """
    Retourne l'état courant des îlots via OPC-UA.
    """
    try:
        states = get_states()
        ilots = [{"ilot": k, "etat": v} for k, v in states.items()]
        return jsonify({"ilots": ilots})
    except Exception as e:
        return jsonify({"error": f"Impossible de récupérer le statut : {e}"}), 500
