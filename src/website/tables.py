from flask import request, url_for
from flask_table import BoolCol, ButtonCol, Col, create_table, LinkCol, OptCol, Table
from website.models import Status, User, UserTypes

class ApproveDriversTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    first_name = Col("First Name")
    last_name = Col("Last Name")
    email = Col("Email")
    approve = ButtonCol("", "approve_driver", text_fallback="Approve", url_kwargs=dict(id="id"), button_attrs={"class": "btn btn-success btn-sm"}, allow_sort=False)
    reject = ButtonCol("", "reject_driver", text_fallback="Reject", url_kwargs=dict(id="id"), button_attrs={"class": "btn btn-danger btn-sm"}, allow_sort=False)
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("approve_drivers", sort_by=col_key, sort_reverse=direction)

class ItemTableItem():
    def __init__(self, name, points, item_id, sponsorship_id):
        self.name = name
        self.points = points
        self.item_id = item_id
        self.sponsorship_id = sponsorship_id

class ItemTable(Table):
    classes = ["table"]
    thead_classes = ["table-dark"]
    name = Col("")
    remove = ButtonCol("", "remove_from_cart", url_kwargs=dict(sponsorship="sponsorship_id", item="item_id"), text_fallback="Remove", button_attrs={"class": "btn btn-danger btn-sm"})
    points = Col("Points")
    allow_sort = False

class DriverCatalogsTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    sponsor = Col("Sponsor", allow_sort=False)
    points = Col("Points")
    select = LinkCol("", "catalog", url_kwargs=dict(id="id"), allow_sort=False, text_fallback="Select")
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for(request.url_rule.rule[1:], sort_by=col_key, sort_reverse=direction)

class OrdersTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    date = Col("Date")
    status = OptCol("Status", choices=dict((choice, choice.value) for choice in Status))
    driver = Col("Driver", attr="sponsorship.driver", allow_sort=False)
    sponsor = Col("Sponsor", attr="sponsorship.sponsor", allow_sort=False)
    view = LinkCol("", "order", url_kwargs=dict(id="id"), allow_sort=False, text_fallback="View")

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("orders", sort_by=col_key, sort_reverse=direction)

class DriverSponsorshipsTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    sponsor = Col("Sponsor", allow_sort=False)
    points = Col("Points")
    view = LinkCol("", "sponsor", url_kwargs=dict(id="sponsor.id"), allow_sort=False, text_fallback="View")
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("sponsorships", sort_by=col_key, sort_reverse=direction)

class ManageDriversTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    driver = Col("Driver", allow_sort=False)
    email = Col("Email", attr="driver.email", allow_sort=False)
    points = Col("Current Points")
    account = LinkCol("", "account", url_kwargs=dict(id="driver.id"), allow_sort=False, text_fallback="Edit")
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("sponsorships", sort_by=col_key, sort_reverse=direction)

class ManageSponsorsTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    name = Col("Name")
    profile = LinkCol("", "sponsor", url_kwargs=dict(id="id"), allow_sort=False, text_fallback="Edit")
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("manage_sponsors", sort_by=col_key, sort_reverse=direction)

class ManageUsersTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    user_type = OptCol("User Type", choices=dict((choice, choice.value) for choice in UserTypes))
    first_name = Col("First Name")
    last_name = Col("Last Name")
    email = Col("Email")
    account = LinkCol("", "account", url_kwargs=dict(id="id"), allow_sort=False, text_fallback="Edit")
    delete = ButtonCol("", "remove_user", text_fallback="Remove", url_kwargs=dict(id="id"), button_attrs={"class": "btn btn-danger btn-sm"}, allow_sort=False)
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("manage_users", sort_by=col_key, sort_reverse=direction)
    
class CartItemsCol(Col):
    def td_contents(self, item, attr_list):
        cart = getattr(item, "cart")
        return self.td_format(len(cart))

class SponsorCartsTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    driver = Col("Driver", allow_sort=False)
    points = Col("Points")
    items = CartItemsCol("Items in Cart", allow_sort=False)
    checkout = LinkCol("", "checkout", url_kwargs=dict(id="id"), allow_sort=False, text_fallback="Check Out", anchor_attrs={"class": "btn btn-primary btn-sm"})
    allow_sort = False

class SupportTicketsTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    id = Col("Ticket ID")
    date = Col("Date")
    user = Col("User", allow_sort=False, show=False)
    title = Col("Title")
    view = LinkCol("", "issue", url_kwargs=dict(id="id"), allow_sort=False, text_fallback="View")
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("issues", sort_by=col_key, sort_reverse=direction)

class ViewSponsorsTable(Table):
    classes = ["table", "table-hover"]
    thead_classes = ["table-dark"]
    name = Col("Name")
    profile = LinkCol("", "sponsor", url_kwargs=dict(id="id"),
            allow_sort=False, text_fallback="View")
    allow_sort = True

    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = "desc"
        else:
            direction = "asc"
        return url_for("sponsors", sort_by=col_key, sort_reverse=direction)
