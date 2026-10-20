from App.main import create_app
from App.database import create_db
from App.controllers import create_staff, create_customer, create_game

app = create_app()
create_db(app)
create_staff("bob", "bobpass")
create_customer("rob", "robpass")
create_game("Halo", 1, "Teen", "XBOX", "https://image.com/pic.png", "shooter")
print("seeded")