from flask import render_template, url_for
from flask_mail import Message
from website import mail
from website.tables import ItemTable

def send_account_removed_email(user):
    message = Message("Account Removed | Driving Rewards", sender="drivingrewardsportal@gmail.com", recipients=[user.email])
    message.body = f"""{user.first_name},
Your account has been removed."""
    mail.send(message)

def send_new_driver_email(sponsorship):
    user = sponsorship.driver
    sponsor = sponsorship.sponsor
    message = Message("New Sponsorship | Driving Rewards", sender="drivingrewardsportal@gmail.com", recipients=[user.email])
    message.body = f"""{user.first_name},
You were approved for a sponsorship with {sponsor}!
To check out their catalog, visit {url_for("catalog", id=sponsorship.id, _external=True)}"""
    mail.send(message)

def send_new_points_email(sponsorship):
    user = sponsorship.driver
    sponsor = sponsorship.sponsor
    message = Message("New Rewards Balance | Driving Rewards", sender="drivingrewardsportal@gmail.com", recipients=[user.email])
    message.body = f"""{user.first_name},
Your new rewards balance with {sponsor} is {sponsorship.points} points.
To check out their catalog, visit {url_for("catalog", id=sponsorship.id, _external=True)}"""
    mail.send(message)

def send_order_cancel_email(order):
    sponsorship = order.sponsorship
    user = sponsorship.driver
    sponsor = sponsorship.sponsor
    message = Message(f"Your Order from {sponsor} Was Canceled | Driving Rewards", sender="drivingrewardsportal@gmail.com", recipients=[user.email])
    message.body = f"""Order #{order.id} from {sponsor} was canceled.
To view your orders, visit {url_for("orders", _external=True)}"""
    mail.send(message)

def send_order_summary_email(order, items, subtotal):
    sponsorship = order.sponsorship
    user = sponsorship.driver
    sponsor = sponsorship.sponsor
    table = ItemTable(items)
    table.remove.show = False
    message = Message(f"Your Order from {sponsor} | Driving Rewards", sender="drivingrewardsportal@gmail.com", recipients=[user.email])
    message.html = render_template("order_info.html", order=order, table=table, subtotal=subtotal)
    mail.send(message)

def send_reset_email(user):
    token = user.get_reset_token()
    message = Message("Password Reset Link | Driving Rewards", sender="drivingrewardsportal@gmail.com", recipients=[user.email])
    message.body = f"""To reset your Driving Rewards Portal password, follow this link:
{url_for("reset_password", token=token, _external=True)}

If you did not request a password reset, please ignore this email."""
    mail.send(message)
