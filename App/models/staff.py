from .user import User
from .listing import Listing
from .rental import Rental
from .rental_payment import RentalPayment
from App.database import db
 
class Staff(User):
 
    __mapper_args__ = {
      'polymorphic_identity': 'staff',
    }
 
    def __init__(self, username, password):
        self.username = username
        self.set_password(password)
        self.user_type = "staff"
 
    def list_game(self, owner, game, condition, price):
        try:
            listing = Listing(owner.id, game.gameId, condition, price)
            db.session.add(listing)
            db.session.commit()
            return listing
        except Exception as e:
            print('error creating listing', e)
            db.session.rollback()
            return None
    
    def delist_game(self, listing):
        try:
            listing.status = 'delisted'
            db.session.add(listing)
            db.session.commit()
            return True
        except:
            db.session.rollback()
        return False
    
    def confirm_rental(self, renter, listing):
        try:
            if listing.status != 'available':
                raise Exception(f'listing {listing.listingId} is not available')
            rental = Rental(renter.id, listing.listingId)
            db.session.add(rental)
            db.session.flush()
            payment = RentalPayment(rental)
            listing.status = 'rented'
            db.session.add(payment)
            db.session.add(listing)
            db.session.commit()
            return rental
        except Exception as e:
            print(e)
            db.session.rollback()
            return None
    
    def confirm_return(self, rental):
        try:
            if rental.return_date != None:
                raise Exception(f'rental {rental.rentalId} has already been returned')
            fees = rental.return_rental()
            rental_payment = RentalPayment(rental)
            listing = Listing.query.get(rental.listingId)
            listing.status = 'available'
            db.session.add(listing)
            db.session.add(rental_payment)
            db.session.commit()
            return fees
        except:
            return None
    
    def toJSON(self):
        return{
            'id': self.id,
            'username': self.username,
            'type': 'staff'
        }