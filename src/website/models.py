from datetime import datetime
from enum import Enum, unique
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from math import ceil
from website import db, login_manager, app
from flask_login import UserMixin

catalog_category = db.Table("catalog_category",
                            db.Column("catalog_id", db.Integer, db.ForeignKey("catalog.id"), primary_key=True),
                            db.Column("category_id", db.Integer, db.ForeignKey("category.id"), primary_key=True))

catalog_item = db.Table("catalog_item",
                        db.Column("catalog_id", db.Integer, db.ForeignKey("catalog.id"), primary_key=True),
                        db.Column("item_id", db.Integer, db.ForeignKey("item.id"), primary_key=True))

catalog_rule = db.Table("catalog_rule",
                        db.Column("catalog_id", db.Integer, db.ForeignKey("catalog.id"), primary_key=True),
                        db.Column("rule_id", db.Integer, db.ForeignKey("rule.id"), primary_key=True))

in_cart = db.Table("in_cart",
                   db.Column("sponsorship_id", db.Integer, db.ForeignKey("sponsorship.id"), primary_key=True),
                   db.Column("item_id", db.Integer, db.ForeignKey("item.id"), primary_key=True))

order_item = db.Table("order_item",
                      db.Column("order_id", db.Integer, db.ForeignKey("order.id"), primary_key=True),
                      db.Column("item_id", db.Integer, db.ForeignKey("item.id"), primary_key=True))

def get_sorted_page(cls, filters, page_args, sort_by, sort_reverse):
    if cls.query.count() == 0:
        return None
    num_pages = ceil(len(cls.query.all()) / page_args["per_page"])
    page_args["page"] = num_pages if page_args["page"] > num_pages else page_args["page"]
    if sort_reverse:
        return cls.query.filter(*filters).order_by(getattr(cls, sort_by).desc()).paginate(**page_args)
    else:
        return cls.query.filter(*filters).order_by(getattr(cls, sort_by)).paginate(**page_args)

def has_account_access(user, current_user):
    if user == current_user:
        return True
    if current_user.user_type == UserTypes.ADMIN:
        return True
    elif current_user.user_type == UserTypes.STORE_MANAGER and user.user_type == UserTypes.DRIVER and user.active_sponsors() and current_user.employer in user.active_sponsors():
        return True
    else:
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    street_1 = db.Column(db.String(40), nullable=False)
    city = db.Column(db.String(40), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zip_code = db.Column(db.String(5), nullable=False)

    def __repr__(self):
        address = f"{self.street_1},\n"
        address += f"{self.city},\n"
        address += f"{self.state},\n"
        address += f"{self.zip_code}"
        return address

@unique
class CatalogTypes(Enum):
    CATEGORIES = "Categories"
    ITEMS = "Items"
    RULES = "Rules"

    def __str__(self):
        return self.value

class Catalog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    catalog_type = db.Column(db.Enum(CatalogTypes), default=CatalogTypes.RULES)
    point_value = db.Column(db.Integer, default=1)
    sponsor_id = db.Column(db.Integer, db.ForeignKey("sponsor.id"))
    sponsor = db.relationship("Sponsor", back_populates="catalog")
    categories = db.relationship("Category", secondary=catalog_category, lazy="subquery", backref=db.backref("catalogs", lazy=True))
    items = db.relationship("Item", secondary=catalog_item, lazy="subquery", backref=db.backref("catalogs", lazy=True))
    rules = db.relationship("Rule", secondary=catalog_rule, lazy="subquery", backref=db.backref("catalogs", lazy=True))

@unique
class Categories(Enum):
    AUTOMOTIVE = "Automotive"
    CLOTHING = "Clothing"
    ELECTRONICS = "Electronics"

    def __str__(self):
        return self.value

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Enum(Categories), default=Categories.AUTOMOTIVE)

    def __repr__(self):
        return f"{self.category}"

@unique
class Filter_By_Category(Enum):
    CAR = "Auto"
    BOOK = "Books"
    ELECTRONIC = "Electronics"
    FASHION = "Fashion"
    HEALTH = "Heath & Beauty"

    def __str__(self):
        return self.value

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ebay_id = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"{self.ebay_id}"

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"{self.rule}"

@unique
class Status(Enum):
    ORDERED = "Ordered"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELED = "Canceled"

    def __str__(self):
        return self.value

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(Status), default=Status.ORDERED)
    sponsorship_id = db.Column(db.Integer, db.ForeignKey("sponsorship.id"), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    address = db.relationship("Address", backref=db.backref("order", uselist=False), lazy=True)
    items = db.relationship("Item", secondary=order_item, lazy="subquery", backref=db.backref("orders", lazy=True))

    def __repr__(self):
        return f"Order {self.id}"

class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    picture = db.Column(db.String(120), default="default_sponsor.jpg")
    managers = db.relationship("User", backref="employer", lazy=True)
    sponsorships = db.relationship("Sponsorship", backref="sponsor", lazy=True)
    catalog = db.relationship("Catalog", uselist=False, back_populates="sponsor")


    def __repr__(self):
        return f"{self.name}"

    def active_drivers(self):
        return list(sponsorship.driver for sponsorship in self.sponsorships if sponsorship.active)

    def applied_drivers(self):
        return list(sponsorship.driver for sponsorship in self.sponsorships if not sponsorship.active)

    def all_drivers(self):
        return list(sponsorship.driver for sponsorship in self.sponsorships)

    @classmethod
    def sponsor_choices(cls):
        sponsors = Sponsor.query.all()

class Sponsorship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    points = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sponsor_id = db.Column(db.Integer, db.ForeignKey("sponsor.id"), nullable=False)
    cart = db.relationship("Item", secondary=in_cart, lazy="subquery", backref=db.backref("carts", lazy=True))
    orders = db.relationship("Order", backref="sponsorship", lazy=True)

    def __repr__(self):
        return f"{self.driver} and {self.sponsor}"

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"Ticket {self.id}"

@unique
class UserTypes(Enum):
    DRIVER = "Driver"
    STORE_MANAGER = "Store Manager"
    ADMIN = "Admin"

    def __str__(self):
        return self.value

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.Enum(UserTypes), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    picture = db.Column(db.String(120), default="default_user.jpg")
    employer_id = db.Column(db.Integer, db.ForeignKey("sponsor.id"), nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=True)
    issue_alert = db.Column(db.Boolean, default=True)
    order_alert = db.Column(db.Boolean, default=True)
    points_alert = db.Column(db.Boolean, default=True)
    address = db.relationship("Address", backref=db.backref("user", uselist=False), lazy=True)
    sponsorships = db.relationship("Sponsorship", backref="driver", lazy=True)
    support_tickets = db.relationship("SupportTicket", backref="user", lazy=True)

    def __repr__(self):
        return f"{self.first_name} {self.last_name}"

    def active_sponsors(self):
        return list(sponsorship.sponsor for sponsorship in self.sponsorships if sponsorship.active)

    def applied_sponsors(self):
        return list(sponsorship.sponsor for sponsorship in self.sponsorships if not sponsorship.active)

    def all_sponsors(self):
        return list(sponsorship.sponsor for sponsorship in self.sponsorships)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": self.id}).decode("utf-8")

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token)["user_id"]
        except:
            return None
        return User.query.get(user_id)
