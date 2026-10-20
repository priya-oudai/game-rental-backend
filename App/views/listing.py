from flask import Blueprint, render_template, jsonify, request, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
 
from App.controllers import (
    get_avaiable_listings_json,
    list_game,
    is_staff,
    get_staff,
    get_game,
    get_customer,
    get_listing
)
 
listing_views = Blueprint('listing_views', __name__, template_folder='../templates')
 
@listing_views.route('/listings', methods=['GET'])
def get_listings_action():
    platform = request.args.get('platform')
    listings = get_avaiable_listings_json(platform)
    return jsonify(listings)
 
VALID_CONDITIONS = ('good', 'fair', 'bad')
 
@listing_views.route('/listings', methods=['POST'])
@jwt_required()
def create_listing_action():
    data = request.get_json(silent=True) or {}
    staff = get_staff(get_jwt_identity())
    if not staff:
        return jsonify({"error": "User not authorized to perform this action"}), 403
    gameid = data.get('gameid', data.get('gameId'))
    owner_id = data.get('owner')
    condition = data.get('condition')
    price = data.get('price')
    if condition not in VALID_CONDITIONS:
        return jsonify({"error": f"{condition} not a valid condition"}), 400
    if not isinstance(price, (int, float)) or isinstance(price, bool) or price < 0:
        return jsonify({"error": f"{price} not a valid price"}), 400
    game = get_game(gameid) if gameid is not None else None
    if not game:
        return jsonify({"error": f"game id {gameid} not found"}), 404
    owner = get_customer(owner_id) if owner_id is not None else None
    if not owner:
        return jsonify({"error": f"owner id {owner_id} not found"}), 404
 
    listing = staff.list_game(owner, game, condition, price)
    if not listing:
        return jsonify({"error": "listing not created"}), 400
    return jsonify({"message": "listing created"}), 201
 
@listing_views.route('/listings/<listingId>', methods=['PUT'])
@jwt_required()
def delist_action(listingId):
    staff = get_staff(get_jwt_identity())
    if staff:
        listing = get_listing(listingId)
        if listing:
            staff.delist_game(listing)
            return jsonify({"message": f"listing - {listing.listingId} delisted"})
        return jsonify({"error": "listing not created bad id"}), 400
    return jsonify({"error": "User not authorized to perform this action"}), 403