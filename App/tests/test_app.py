import os, tempfile, pytest, logging, unittest
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

from App.main import create_app
from App.database import create_db, db
from App.models import User, Staff, Customer, Listing, Rental, RentalPayment
from App.controllers import (
    create_customer,
    create_game,
    get_customer,
    create_staff,
    get_all_users_json,
    authenticate,
    get_staff,
    get_user,
    get_game,
    get_rental,
    get_listing,
    update_staff,
    create_rental_payment,
    jwt_authenticate
)

app = create_app({"SQLALCHEMY_DATABASE_URI":'sqlite:///test_database.db', "TESTING":True, "DEBUG":True})


LOGGER = logging.getLogger(__name__)

'''
   Unit Tests
'''
class UserUnitTests(unittest.TestCase):

    def test_new_user(self):
        user = Staff("bob", "bobpass")
        assert user.username == "bob"

    def test_toJSON(self):
        user = Staff("bob", "bobpass")
        user_json = user.toJSON()
        self.assertDictEqual(user_json, {"id":None, "username":"bob", "type": 'staff'})
    
    # def test_hashed_password(self):

    # def test_check_password(self):
        

'''
    Integration Tests
'''

# This fixture creates an empty database for the test and deletes it after the test
@pytest.fixture(autouse=True, scope="module")
def empty_db():
    create_db(app)
    yield app.test_client()
    db.session.remove()
    db.drop_all()


# def test_authenticate():
def test_authenticate():
    create_customer("auth_user", "authpass")
    assert authenticate("auth_user", "authpass")
    assert authenticate("auth_user", "wrongpass") is None
    assert authenticate("nobody", "authpass") is None
    assert jwt_authenticate("auth_user", "authpass") is not None
    
def make_listing(tag, price=20.0):
    staff = create_staff(f"staff_{tag}", "staffpass")
    owner = create_customer(f"owner_{tag}", "ownerpass")
    game = create_game(f"Game {tag}", rawgId=1000 + hash(tag) % 1000)
    listing = staff.list_game(owner, game, "good", price)
    return staff, owner, game, listing

# def test_create_game():
def test_create_game():
    game = create_game("Halo", rawgId=1, rating="Teen", platform="XBOX", genre="shooter")
    saved = get_game(game.gameId)
    assert saved.title == "Halo"
    assert saved.platform == "XBOX"
    
# def test_create_user():
def test_create_user():
    customer = create_customer("rick", "rickpass")
    assert customer is not None
    saved = get_user(customer.id)
    assert saved.username == "rick"
    assert saved.user_type == "customer"
    assert saved.password != "rickpass"
    
# def test_create_staff():
def test_create_staff():
    staff = create_staff("sally", "sallypass")
    saved = get_staff(staff.id)
    assert saved.username == "sally"
    assert saved.user_type == "staff"

# def test_staff_create_listing():
def test_staff_create_listing():
    staff, owner, game, listing = make_listing("create_listing")
    assert listing is not None
    saved = get_listing(listing.listingId)
    assert saved.ownerId == owner.id
    assert saved.gameId == game.gameId
    assert saved.condition == "good"
    assert saved.price == 20.0
    assert saved.status == "available"
    
# def test_staff_confirm_rental():
def test_staff_confirm_rental():
    staff, owner, game, listing = make_listing("confirm_rental")
    renter = create_customer("renter_confirm", "renterpass")
 
    rental = staff.confirm_rental(renter, get_listing(listing.listingId))
 
    assert rental is not None
    saved_rental = get_rental(rental.rentalId)
    assert saved_rental.renterId == renter.id
    assert saved_rental.listingId == listing.listingId
    assert saved_rental.return_date is None
    payment = RentalPayment.query.filter_by(rentalId=rental.rentalId).first()
    assert payment is not None
    assert payment.customerId == renter.id
    assert payment.amount == listing.price
    assert get_listing(listing.listingId).status == "rented"
    other = create_customer("renter_confirm_2", "renterpass")
    assert staff.confirm_rental(other, get_listing(listing.listingId)) is None
    
# def test_staff_confirm_return():
def test_staff_confirm_return():
    staff, owner, game, listing = make_listing("confirm_return", price=50.0)
    renter = create_customer("renter_return", "renterpass")
    rental = staff.confirm_rental(renter, get_listing(listing.listingId))
 
    fees = staff.confirm_return(get_rental(rental.rentalId))
 
    assert fees == 0                
    returned = get_rental(rental.rentalId)
    assert returned.return_date is not None
    assert get_listing(listing.listingId).status == "available"
    payments = RentalPayment.query.filter_by(rentalId=rental.rentalId).all()
    assert len(payments) >= 1
    assert staff.confirm_return(get_rental(rental.rentalId)) is None

# class UsersIntegrationTests(unittest.TestCase):

# tests staff's ability to create rentals in system

# def test_staff_confirm_rental(self):

# def test_staff_confirm_return(self):

def test_get_all_users_json():
    staff = create_staff("json_staff", "pass")
    customer = create_customer("json_customer", "pass")
    users = get_all_users_json()
    assert {"id": staff.id, "username": "json_staff", "type": "staff"} in users
    assert {"id": customer.id, "username": "json_customer",
            "type": "customer", "status": "active"} in users
  
def test_update_user():
    staff = create_staff("old_name", "pass")
    update_staff(staff.id, "new_name")
    updated = get_staff(staff.id)
    assert updated.username == "new_name"  

def test_staff_confirm_return_late():
    staff, owner, game, listing = make_listing("late_return", price=50.0)
    renter = create_customer("renter_late", "renterpass")
    rental = staff.confirm_rental(renter, get_listing(listing.listingId))
    rental.rental_date = datetime.utcnow() - timedelta(days=24)
    db.session.commit()
 
    fees = staff.confirm_return(get_rental(rental.rentalId))
 
    assert fees == pytest.approx(0.10 * 50.0 * 10)
    assert get_listing(listing.listingId).status == "available"     

def auth_header(client, username, password):
    res = client.post("/auth", json={"username": username, "password": password})
    return {"Authorization": f"JWT {res.json['access_token']}"}   


def test_api_create_listing():
    client = app.test_client()
    staff = create_staff("api_staff", "staffpass")
    owner = create_customer("api_owner", "ownerpass")
    game = create_game("API Game", rawgId=777)
    headers = auth_header(client, "api_staff", "staffpass")
 
    res = client.post("/listings", headers=headers, json={
        "gameid": game.gameId, "owner": owner.id, "condition": "good", "price": 25.5})
    assert res.status_code == 201
    assert res.json == {"message": "listing created"}
    res = client.post("/listings", json={
        "gameid": game.gameId, "owner": owner.id, "condition": "good", "price": 25.5})
    assert res.status_code == 401
    assert res.json == {"error": "not authenticated"}
    res = client.post("/listings", headers=headers, json={
        "gameid": 99999, "owner": owner.id, "condition": "good", "price": 25.5})
    assert res.status_code == 404
    assert res.json == {"error": "game id 99999 not found"}
    res = client.post("/listings", headers=headers, json={
        "gameid": game.gameId, "owner": owner.id, "condition": "mint", "price": 25.5})
    assert res.status_code == 400
    assert res.json == {"error": "mint not a valid condition"}
    headers = auth_header(client, "api_owner", "ownerpass")
    res = client.post("/listings", headers=headers, json={
        "gameid": game.gameId, "owner": owner.id, "condition": "good", "price": 25.5})
    assert res.status_code == 403     

        

