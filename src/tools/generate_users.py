import os
import requests
import secrets
from essential_generators import DocumentGenerator
from io import BytesIO
from PIL import Image
from random import getrandbits, randint
from randomuser import RandomUser
from website import app, bcrypt, db
from website.models import Catalog, Sponsor, Sponsorship, SupportTicket, User, UserTypes


GEN_DRIVERS = True
GEN_SPONSORS = True
GEN_STORE_MANAGERS = True
GEN_SUPPORT_TICKETS = True
MAX_POINTS = 10000
MAX_SPONSORSHIPS = 10
NUM_DRIVERS = 100
NUM_SPONSORS = 25
NUM_STORE_MANAGERS = 50
NUM_SUPPORT_TICKETS = 200
REMOVE_EXISTING = True


text_generator = DocumentGenerator()


def generate_sponsor(i):
    exists = True
    while exists:
        print(f"Generating Random Sponsor {i}")
        random_user = RandomUser({'nat': 'us','gender': 'male'}) 
        name = " ".join(random_user.get_street().split()[1:-1])
        name += " Auto Parts"
        exists = Sponsor.query.filter_by(name=name).first()
    random_picture = requests.get(random_user.get_picture())
    random_name = secrets.token_hex(8)
    _, extension = os.path.splitext(random_user.get_picture())
    file_name = random_name + extension
    path = os.path.join(app.root_path, "static/profile_pictures", file_name)
    size = 500, 500
    picture = Image.open(BytesIO(random_picture.content))
    picture.thumbnail(size)
    picture.save(path)
    sponsor = Sponsor(name=name, picture=file_name)
    catalog = Catalog(sponsor=sponsor)
    db.session.add(sponsor)
    db.session.add(catalog)


def generate_user(i, user_type):
    exists = True
    while exists:
        print(f"Generating Random {user_type} {i}")
        random_user = RandomUser({'nat': 'us','gender': 'male'})
        exists = User.query.filter_by(email=random_user.get_email()).first()
    random_picture = requests.get(random_user.get_picture())
    random_name = secrets.token_hex(8)
    _, extension = os.path.splitext(random_user.get_picture())
    file_name = random_name + extension
    path = os.path.join(app.root_path, "static/profile_pictures", file_name)
    size = 500, 500
    picture = Image.open(BytesIO(random_picture.content))
    picture.thumbnail(size)
    picture.save(path)
    password = bcrypt.generate_password_hash("password").decode("utf-8")
    user = User(user_type=user_type, 
                first_name=random_user.get_first_name(),
                last_name=random_user.get_last_name(),
                email=random_user.get_email(),
                password=password,
                picture=file_name)
    if user_type == UserTypes.DRIVER:
        for j in range(0, randint(0, MAX_SPONSORSHIPS)):
            exists = True
            while exists:
                print(f"Generating Random Sponsorship {j} for Random User {i}")
                sponsor_id = randint(1, Sponsor.query.count())
                sponsor = Sponsor.query.get(sponsor_id)
                exists = sponsor in user.all_sponsors()
            sponsorship = Sponsorship()
            sponsorship.driver = user
            sponsorship.sponsor = sponsor
            sponsorship.active = bool(getrandbits(1))
            if sponsorship.active:
                sponsorship.points = randint(0, MAX_POINTS)
            db.session.add(sponsorship)
    elif user_type == UserTypes.STORE_MANAGER:
        sponsor_id = randint(1, Sponsor.query.count())
        user.employer = Sponsor.query.get(sponsor_id)
    db.session.add(user)


def generate_support_ticket(i):
        print(f"Generating Random Support Ticket {i}")
        num_users = User.query.count()
        user_id = randint(1, num_users)
        title=text_generator.gen_sentence(max_words=10)
        description=text_generator.paragraph()
        support_ticket = SupportTicket(title=title, description=description, user_id=user_id)
        db.session.add(support_ticket)

def main():
    if REMOVE_EXISTING:
        db.drop_all()
        db.create_all()
        print(f"Removing All Existing Database Entries")
        User.query.filter(User.user_type.isnot(UserTypes.ADMIN)).delete()
        Sponsor.query.delete()
        Sponsorship.query.delete()
        print(f"Generating Admin Accounts")
        password = bcrypt.generate_password_hash("password").decode("utf-8")
        chase = User(user_type=UserTypes.ADMIN, first_name="Chase", last_name="Autry", email="cautry@clemson.edu", password=password)
        jake = User(user_type=UserTypes.ADMIN, first_name="Jake", last_name="Ammons", email="jlammon@clemson.edu", password=password)
        lee = User(user_type=UserTypes.ADMIN, first_name="Hyeop", last_name="Lee", email="hyeopl@clemson.edu", password=password)
        db.session.add_all([chase,jake,lee])
    if GEN_SPONSORS:
        for i in range(0, NUM_SPONSORS):
            generate_sponsor(i)
    if GEN_DRIVERS:
        for i in range(0, NUM_DRIVERS):
            generate_user(i, UserTypes.DRIVER)
    if GEN_STORE_MANAGERS:
        for i in range(0, NUM_STORE_MANAGERS):
            generate_user(i, UserTypes.STORE_MANAGER)
    if GEN_SUPPORT_TICKETS:
        for i in range(0, NUM_SUPPORT_TICKETS):
            generate_support_ticket(i)
    db.session.commit()


if __name__ == '__main__':
    main()
