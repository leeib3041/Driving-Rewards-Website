import os
import secrets
import werkzeug
from PIL import Image
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import and_, or_
from wtforms.validators import ValidationError
from website import app, bcrypt, db
from website.email import send_account_removed_email, send_new_driver_email, send_new_points_email, send_order_cancel_email, send_order_summary_email, send_reset_email
from website.forms import AddressForm, AddSponsorForm, AddUserForm, CatalogCategoriesForm, CatalogRulesForm, CatalogSettingsForm, DriverApplicationForm, RequestResetForm, ResetPasswordForm, SearchForm, SignInForm, SponsorApplicationForm, SupportForm, UpdateAccountForm, UpdateSponsorForm
from website.models import get_sorted_page, has_account_access, Address, Catalog, Category, CatalogTypes, Item, Order, Sponsor, Sponsorship, Status, SupportTicket, User, UserTypes
from website.tables import ApproveDriversTable, OrdersTable, ItemTableItem, ItemTable, DriverCatalogsTable, DriverSponsorshipsTable, ManageDriversTable, ManageSponsorsTable, ManageUsersTable, SponsorCartsTable, SupportTicketsTable, ViewSponsorsTable
from ebaysdk.finding import Connection as Finding
from ebaysdk.shopping import Connection as Shopping

app.add_template_global(UserTypes, 'UserTypes')
app.add_template_global(CatalogTypes, 'CatalogTypes')

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    id = request.args.get("id", current_user.id, type=int)
    user = User.query.get(id)
    if not has_account_access(user, current_user):
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    if not user:
        flash("User does not exist.", "danger")
        return redirect(url_for("home"))
    form = UpdateAccountForm()
    picture = url_for("static", filename=f"profile_pictures/{user.picture}")
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.issue_alert = form.issue_alert.data
        user.order_alert = form.order_alert.data
        user.points_alert = form.points_alert.data
        if user.email != form.email.data and User.query.filter_by(email=form.email.data).first():
            form.email.errors.append(ValidationError("Email already used. Try again."))
            return render_template("account.html", title=f"{user.first_name}'s Account", user=user, picture=picture, form=form)
        else:
            user.email = form.email.data
        if form.employer.data:
            user.employer = Sponsor.query.get(form.employer.data)
        if form.picture.data:
            random_name = secrets.token_hex(8)
            _, extension = os.path.splitext(form.picture.data.filename)
            file_name = random_name + extension
            path = os.path.join(app.root_path, "static/profile_pictures", file_name)
            size = 500, 500
            picture = Image.open(form.picture.data)
            picture.thumbnail(size)
            picture.save(path)
            path = os.path.join(app.root_path, "static/profile_pictures", user.picture)
            if user.picture != "default_user.jpg" and os.path.exists(path):
                os.remove(path)
            user.picture = file_name
        db.session.commit()
        flash("Account information has been updated", "success")
        return redirect(url_for("account", id=id))
    elif request.method == "GET":
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.issue_alert.data = user.issue_alert
        form.order_alert.data = user.order_alert
        form.points_alert.data = user.points_alert
        form.email.data = user.email
        if user.user_type == UserTypes.STORE_MANAGER and user.employer:
            form.employer.data = user.employer.id
    return render_template("account.html", title=f"{user.first_name}'s Account", user=user, picture=picture, form=form)

@app.route("/add_sponsor", methods=["GET", "POST"])
@login_required
def add_sponsor():
    if current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    form = AddSponsorForm()
    if form.validate_on_submit():
        sponsor = Sponsor(name=form.name.data)
        catalog = Catalog(sponsor=sponsor)
        db.session.add(sponsor)
        db.session.add(catalog)
        db.session.commit()
        flash(f"Sponsor account created for: {sponsor}", "success")
    return render_template("add_sponsor.html", title="Add Sponsor", form=form)

@app.route("/add_to_cart", methods=["GET", "POST"])
@login_required
def add_to_cart():
    sponsorship_id = request.args.get("sponsorship", type=int)
    item_id = request.args.get("item", type=str)
    if not sponsorship_id or not item_id:
        flash("Unable to add to cart.", "info")
        return redirect(url_for("home"))
    sponsorship = Sponsorship.query.get(sponsorship_id)
    if current_user != sponsorship.driver:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    item = Item.query.filter_by(ebay_id=item_id).first()
    if not item:
        item = Item(ebay_id=item_id)
    sponsorship.cart.append(item)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for("cart", id=sponsorship_id))

@app.route("/add_to_catalog", methods=["GET", "POST"])
@login_required
def add_to_catalog():
    sponsor_id = request.args.get("sponsor", type=int)
    item_id = request.args.get("item", type=str)
    if not sponsor_id or not item_id:
        flash("Unable to add to catalog.", "info")
        return redirect(url_for("home"))
    sponsor = Sponsor.query.get(sponsor_id)
    if current_user.employer != sponsor:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    item = Item.query.filter_by(ebay_id=item_id).first()
    if not item:
        item = Item(ebay_id=item_id)
        db.session.add(item)
    sponsor.catalog.items.append(item)
    db.session.commit()
    return redirect(url_for("manage_catalog"))

@app.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    form = AddUserForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(user_type=form.user_type.data, first_name=form.first_name.data, last_name=form.last_name.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f"User account created for: {user}", "success")
    return render_template("add_user.html", title="Add User", form=form)

@app.route("/apply_sponsor", methods=["POST"])
@login_required
def apply_sponsor():
    if current_user.user_type != UserTypes.DRIVER:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    id = request.args.get("id", type=int)
    sponsor = Sponsor.query.get(id)
    if sponsor not in current_user.all_sponsors():
        sponsorship = Sponsorship()
        sponsorship.driver = current_user
        sponsorship.sponsor = sponsor
        db.session.add(sponsorship)
        db.session.commit()
        flash(f"Successfully applied to {sponsor}.", "success")
    else:
        flash(f"Not able to apply to {sponsor}", "danger")
    return redirect(request.referrer)

@app.route("/approve_driver", methods=["POST"])
@login_required
def approve_driver():
    id = request.args.get("id", type=int)
    user = User.query.get(id)
    if current_user.user_type != UserTypes.STORE_MANAGER or current_user.employer not in user.applied_sponsors():
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    for sponsorship in user.sponsorships:
        if current_user.employer == sponsorship.sponsor:
            sponsorship.active = True
            db.session.commit()
            send_new_driver_email(sponsorship)
            flash(f"Successfully approved {user}.", "success")
    return redirect(request.referrer)

@app.route("/approve_drivers")
@login_required
def approve_drivers():
    filters = []
    filters.append(User.user_type.is_(UserTypes.DRIVER))
    if current_user.user_type == UserTypes.STORE_MANAGER and current_user.employer:
        filters.append(User.sponsorships.any(sponsor=current_user.employer, active=False))
    else:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    drivers = get_sorted_page(User, filters, page_args, sort_by, sort_reverse)
    if drivers.items:
        table = ApproveDriversTable(drivers.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = drivers.iter_pages()
        return render_template("approve_drivers.html", title="Approve Drivers", table=table, pages=pages, current_page=page_args["page"], num_pages=drivers.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No drivers to approve.", "info")
        return redirect(url_for("home"))

@app.route("/award_points", methods=["POST"])
@login_required
def award_points():
    id = request.args.get("id", type=int)
    points = int(request.form["points"])
    user = User.query.get(id)
    if current_user.user_type != UserTypes.STORE_MANAGER or current_user.employer not in user.active_sponsors():
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    for sponsorship in user.sponsorships:
        if current_user.employer == sponsorship.sponsor:
            sponsorship.points += points
            db.session.commit()
            if (user.points_alert):
                send_new_points_email(sponsorship)
            flash(f"Successfully awarded {points} points to {user}.", "success")
    return redirect(request.referrer)

@app.route("/cancel_order", methods=["POST"])
@login_required
def cancel_order():
    id = request.args.get("id", type=int)
    order = Order.query.get(id)
    if not order:
        return redirect(request.referrer)
    order.status = Status.CANCELED
    db.session.commit()
    if order.sponsorship.driver.issue_alert:
        send_order_cancel_email(order)
    flash(f"Successfully canceled order {order.id}.", "success")
    return redirect(request.referrer)

@app.route("/cart")
@login_required
def cart():
    id = request.args.get("id", type=int)
    sponsorship = Sponsorship.query.get(id)
    if not sponsorship:
        flash("Cannot access cart.", "danger")
        return redirect(url_for("home"))
    if not sponsorship.cart:
        flash("Cart is empty.", "info")
        return redirect(url_for("catalog", id=id))
    items = []
    subtotal = 0
    api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
    for item in sponsorship.cart:
        call = {
        'keywords': item.ebay_id
        }
        response = api.execute('findItemsByKeywords', call)
        name = response.reply.searchResult.item[0].title
        points = int(float(response.reply.searchResult.item[0].sellingStatus.currentPrice.value)*100)
        cart_item = ItemTableItem(name=name, points=points, item_id=item.id, sponsorship_id=id)
        items.append(cart_item)
        subtotal += points
    table = ItemTable(items)
    title = f"{sponsorship.sponsor} Cart"
    return render_template("cart.html", title=title, table=table, subtotal=subtotal, sponsorship=sponsorship)

@app.route("/carts")
@login_required
def carts():
    if current_user.user_type != UserTypes.STORE_MANAGER:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    user = current_user
    filters = [Sponsorship.sponsor_id.is_(current_user.employer_id), Sponsorship.active.is_(True), Sponsorship.cart]
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    sponsorship_list = get_sorted_page(Sponsorship, filters, page_args, sort_by, sort_reverse)
    if sponsorship_list.items:
        title = "Driver Carts"
        table = SponsorCartsTable(sponsorship_list.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = sponsorship_list.iter_pages()
        return render_template("carts.html", title=title, table=table, pages=pages, current_page=page_args["page"], num_pages=sponsorship_list.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No open carts.", "info")
        return redirect(url_for("home"))

@app.route("/catalog", methods=["GET", "POST"])
@login_required
def catalog():
    if current_user.user_type == UserTypes.STORE_MANAGER:
        sponsor = current_user.employer
        sponsorship = Sponsorship()
    elif current_user.user_type == UserTypes.DRIVER:
        id = request.args.get("id", type=int)
        if not id:
            return redirect(url_for("catalogs"))
        sponsorship = Sponsorship.query.get(id)
        sponsor = sponsorship.sponsor
    else:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    title = f"{sponsor} Catalog"
    if sponsor.catalog.catalog_type == CatalogTypes.CATEGORIES:
        search_form = SearchForm()
        search = search_form.search.data
        api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
        call = {
        'keywords': search,
        'itemFilter': [
            {'name': 'Condition', 'value': 'New'},
            {'name': 'FreeShippingOnly', 'value': 'True'}
        ],
        'paginationInput': {
            'entriesPerPage': 30,
            'pageNumber': 1
        },
        #'sortOrder': 'PricePlusShippingLowest'
        }
        response = api.execute('findItemsByKeywords', call)
        item_list = []
        if response.reply.ack == "Failure" or response.reply.searchResult._count == "0":
            flash("No results.", "info")
            return render_template("catalog.html", title=title, item_list=item_list, search_form=search_form, sponsorship=sponsorship, sponsor=sponsor)
        for item in response.reply.searchResult.item:
            point_conversion = str(round(float(item.sellingStatus.currentPrice.value)/(sponsor.catalog.point_value/100), 2))
            item.sellingStatus.currentPrice.value = point_conversion
            item_list.append(item)
        return render_template("catalog.html", title=title, item_list=item_list, search_form=search_form, sponsorship=sponsorship, sponsor=sponsor)
    elif sponsor.catalog.catalog_type == CatalogTypes.ITEMS:
        api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
        item_list = []
        for item in sponsor.catalog.items:
            call = {
            'keywords': item.ebay_id
            }
            response = api.execute('findItemsByKeywords', call)
            if response.reply.ack == "Failure" or response.reply.searchResult._count == "0":
                continue
            result = response.reply.searchResult.item[0]
            point_conversion = str(round(float(result.sellingStatus.currentPrice.value)/(sponsor.catalog.point_value/100), 2))
            result.sellingStatus.currentPrice.value = point_conversion
            item_list.append(result)
        if not item_list:
            flash("No results.", "info")
            return render_template("catalog.html", title=title, item_list=item_list, sponsorship=sponsorship, sponsor=sponsor)
        return render_template("catalog.html", title=title, item_list=item_list, sponsorship=sponsorship, sponsor=sponsor)
    elif sponsor.catalog.catalog_type == CatalogTypes.RULES:
        search_form = SearchForm()
        search = search_form.search.data
        api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
        call = {
        'keywords': search,
        'itemFilter': [
            {'name': 'Condition', 'value': 'New'},
            {'name': 'FreeShippingOnly', 'value': 'True'}
        ],
        'paginationInput': {
            'entriesPerPage': 30,
            'pageNumber': 1
        },
        #'sortOrder': 'PricePlusShippingLowest'
        }
        response = api.execute('findItemsByKeywords', call)
        item_list = []
        if response.reply.ack == "Failure" or response.reply.searchResult._count == "0":
            flash("No results.", "info")
            return render_template("catalog.html", title=title, item_list=item_list, search_form=search_form, sponsorship=sponsorship, sponsor=sponsor)
        for item in response.reply.searchResult.item:
            point_conversion = str(round(float(item.sellingStatus.currentPrice.value)/(sponsor.catalog.point_value/100), 2))
            item.sellingStatus.currentPrice.value = point_conversion
            item_list.append(item)
        return render_template("catalog.html", title=title, item_list=item_list, search_form=search_form, sponsorship=sponsorship, sponsor=sponsor)
    else:
        flash("No catalog type.", "danger")
        return redirect(url_for("home"))

@app.route("/catalogs")
@login_required
def catalogs():
    if current_user.user_type != UserTypes.DRIVER:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    user = current_user
    filters = [Sponsorship.user_id.is_(user.id), Sponsorship.active.is_(True)]
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    sponsorship_list = get_sorted_page(Sponsorship, filters, page_args, sort_by, sort_reverse)
    if sponsorship_list.items:
        title = "Sponsor Catalogs"
        table = DriverCatalogsTable(sponsorship_list.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = sponsorship_list.iter_pages()
        return render_template("catalogs.html", title=title, table=table, pages=pages, current_page=page_args["page"], num_pages=sponsorship_list.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("You don't have any sponsorships.", "info")
        return redirect(url_for("home"))

@app.route("/catalog_settings", methods=["POST"])
@login_required
def catalog_settings():
    if current_user.user_type != UserTypes.STORE_MANAGER:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    form = CatalogSettingsForm()
    if form.validate_on_submit():
        catalog = current_user.employer.catalog
        catalog.catalog_type = form.catalog_type.data
        catalog.point_value = form.point_value.data
        db.session.commit()
        flash(f"Successfully updated catalog settings.", "success")
        return redirect(request.referrer)
    else:
        flash(f"Unable to update catalog settings.", "danger")
        return redirect(request.referrer)


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    id = request.args.get("id", type=int)
    sponsorship = Sponsorship.query.get(id)
    if not sponsorship:
        flash("Cannot access checkout.", "danger")
        return redirect(url_for("home"))
    if not sponsorship.cart:
        flash("Cart is empty.", "info")
        return redirect(url_for("catalog", id=id))
    if current_user != sponsorship.driver and current_user.employer != sponsorship.sponsor:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    items = []
    subtotal = 0
    api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
    for item in sponsorship.cart:
        call = {
        'keywords': item.ebay_id
        }
        response = api.execute('findItemsByKeywords', call)
        name = response.reply.searchResult.item[0].title
        points = int(float(response.reply.searchResult.item[0].sellingStatus.currentPrice.value)*100)
        cart_item = ItemTableItem(name=name, points=points, item_id=item.id, sponsorship_id=id)
        items.append(cart_item)
        subtotal += points
    form = AddressForm()
    if form.validate_on_submit():
        address = Address(street_1=form.street_1.data,
                          city=form.city.data,
                          state=form.state.data,
                          zip_code=form.zip_code.data)
        sponsorship.driver.address = address
        order = Order(sponsorship_id=id, address=address, items=sponsorship.cart)
        sponsorship.cart.clear()
        sponsorship.points -= subtotal
        db.session.add(order)
        db.session.commit()
        db.session.refresh(order)
        if sponsorship.driver.order_alert:
            send_order_summary_email(order, items, subtotal)
        return redirect(url_for("order", id=order.id))
    elif request.method == "GET":
        if sponsorship.driver.address:
            form.street_1.data = sponsorship.driver.address.street_1
            form.city.data = sponsorship.driver.address.city
            form.state.data = sponsorship.driver.address.state
            form.zip_code.data = sponsorship.driver.address.zip_code
        table = ItemTable(items)
        title = f"{sponsorship.sponsor} Checkout"
        rewards = min(subtotal, sponsorship.points)
        total = subtotal - rewards
        left = sponsorship.points - subtotal
        return render_template("checkout.html", form=form, left=left, rewards=rewards, sponsorship=sponsorship, subtotal=subtotal, title=title, total=total)
    else:
        flash("Unable to check out.", "danger")
        return redirect(url_for("home"))

@app.route("/driver_application", methods=["GET", "POST"])
def driver_application():
    if current_user.is_authenticated:
        return redirect(url_for("profile", id=current_user.id))
    form = DriverApplicationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(user_type=UserTypes.DRIVER, first_name=form.first_name.data, last_name=form.last_name.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f"{user.first_name}, Your account was created. Please sign in.", "success")
        return redirect(url_for("sign_in"))
    return render_template("driver_application.html", title="Driver Application", form=form)

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", title="Home")

@app.route("/issue")
@login_required
def issue():
    id = request.args.get("id", type=int)
    if id:
        support_ticket = SupportTicket.query.get(id)
    else:
        flash("Invalid support ticket number.", "danger")
        return redirect(url_for("issues"))
    title = f"Ticket #{support_ticket.id}"
    return render_template("issue.html", title=title, support_ticket=support_ticket)

@app.route("/issues", methods=["GET", "POST"])
@login_required
def issues():
    if current_user.user_type == UserTypes.ADMIN:
        title = "All Issues"
        filters = []
    else:
        title = "My Issues"
        filters = [SupportTicket.user_id.is_(current_user.id)]
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    search_list = []
    form = SearchForm()
    if request.method == "POST":
        search_query = form.search.data
        if search_query:
            search_list = search_query.split(" ")
            search_query = search_query.replace(" ", "+")
    elif request.method == "GET":
        search_query = request.args.get("search_query")
        if search_query:
            search_list = search_query.split("+")
            form.search.data = search_query.replace("+", " ")
    if search_list:
        append_list = []
        for word in search_list:
            append_list.append(SupportTicket.id.like("%" + word + "%"))
            append_list.append(SupportTicket.title.like("%" + word + "%"))
            append_list.append(SupportTicket.description.like("%" + word + "%"))
            append_list.append(and_(SupportTicket.user_id.is_(User.id), User.first_name.like("%" + word + "%")))
            append_list.append(and_(SupportTicket.user_id.is_(User.id), User.last_name.like("%" + word + "%")))
            append_list.append(and_(SupportTicket.user_id.is_(User.id), User.email.like("%" + word + "%")))
            append_list.append(and_(SupportTicket.user_id.is_(User.id), User.user_type.like("%" + word + "%")))
        filters.append(or_(*append_list))
    tickets = get_sorted_page(SupportTicket, filters, page_args, sort_by, sort_reverse)
    if tickets and tickets.items:
        table = SupportTicketsTable(tickets.items, sort_by=sort_by, sort_reverse=sort_reverse)
        if current_user.user_type == UserTypes.ADMIN:
            table.user.show = True
        else:
            table.user.show = False
        pages = tickets.iter_pages()
        return render_template("issues.html", form=form, title=title, table=table,
                pages=pages, current_page=page_args["page"], num_pages=tickets.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No results.", "info")
        return redirect(request.referrer)

@app.route("/manage_catalog", methods=["GET", "POST"])
@login_required
def manage_catalog():
    if current_user.user_type != UserTypes.STORE_MANAGER:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    sponsor = current_user.employer
    settings_form = CatalogSettingsForm()
    settings_form.point_value.data = sponsor.catalog.point_value
    settings_form.catalog_type.data = sponsor.catalog.catalog_type.name
    if sponsor.catalog.catalog_type == CatalogTypes.CATEGORIES:
        category_form = CatalogCategoriesForm()
        return render_template("manage_catalog.html", category_form=category_form, settings_form=settings_form, sponsor=sponsor, title="Manage Catalog")
    elif sponsor.catalog.catalog_type == CatalogTypes.ITEMS:
        search_form = SearchForm()
        search = search_form.search.data
        api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
        call = {
        'keywords': search,
        'itemFilter': [
            {'name': 'Condition', 'value': 'New'},
            {'name': 'FreeShippingOnly', 'value': 'True'}
        ],
        'paginationInput': {
            'entriesPerPage': 30,
            'pageNumber': 1
        },
        #'sortOrder': 'PricePlusShippingLowest'
        }
        response = api.execute('findItemsByKeywords', call)
        item_list = []
        if response.reply.ack == "Failure" or response.reply.searchResult._count == "0":
            flash("No results.", "info")
            return render_template("manage_catalog.html", item_list=item_list, search_form=search_form, settings_form=settings_form, sponsor=sponsor, title="Manage Catalog")
        for item in response.reply.searchResult.item:
            point_conversion = str(round(float(item.sellingStatus.currentPrice.value)/(sponsor.catalog.point_value/100), 2))
            item.sellingStatus.currentPrice.value = point_conversion
            item_list.append(item)
        return render_template("manage_catalog.html", item_list=item_list, search_form=search_form, settings_form=settings_form, sponsor=sponsor, title="Manage Catalog")
    elif sponsor.catalog.catalog_type == CatalogTypes.RULES:
        rules_form = CatalogRulesForm()
        return render_template("manage_catalog.html", rules_form=rules_form, settings_form=settings_form, sponsor=sponsor, title="Manage Catalog")
    else:
        flash("No catalog type.", "danger")
        return redirect(url_for("home"))

@app.route("/manage_sponsors", methods=["GET", "POST"])
@login_required
def manage_sponsors():
    if current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    filters = []
    search_list = []
    form = SearchForm()
    if request.method == "POST":
        search_query = form.search.data
        if search_query:
            search_list = search_query.split(" ")
            search_query = search_query.replace(" ", "+")
    elif request.method == "GET":
        search_query = request.args.get("search_query")
        if search_query:
            search_list = search_query.split("+")
            form.search.data = search_query.replace("+", " ")
    if search_list:
        append_list = []
        for word in search_list:
            append_list.append(Sponsor.name.like("%" + word + "%"))
        filters.append(or_(*append_list))
    sponsors = get_sorted_page(Sponsor, filters, page_args, sort_by, sort_reverse)
    if sponsors and sponsors.items:
        title = "Manage Sponsors"
        table = ManageSponsorsTable(sponsors.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = sponsors.iter_pages()
        return render_template("manage_sponsors.html", form=form, title=title, table=table, pages=pages, current_page=page_args["page"], num_pages=sponsors.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No results.", "info")
        return redirect(request.referrer)

@app.route("/manage_users", methods=["GET", "POST"])
@login_required
def manage_users():
    if current_user.user_type == UserTypes.ADMIN:
        filters = []
    elif current_user.user_type == UserTypes.STORE_MANAGER and current_user.employer:
        filters = [User.sponsorships.any(sponsor=current_user.employer, active=True)]
    else:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    search_list = []
    form = SearchForm()
    if request.method == "POST":
        search_query = form.search.data
        if search_query:
            search_list = search_query.split(" ")
            search_query = search_query.replace(" ", "+")
    elif request.method == "GET":
        search_query = request.args.get("search_query")
        if search_query:
            search_list = search_query.split("+")
            form.search.data = search_query.replace("+", " ")
    if search_list:
        append_list = []
        for word in search_list:
            append_list.append(User.first_name.like("%" + word + "%"))
            append_list.append(User.last_name.like("%" + word + "%"))
            append_list.append(User.email.like("%" + word + "%"))
            append_list.append(User.user_type.like("%" + word + "%"))
        filters.append(or_(*append_list))
    users = get_sorted_page(User, filters, page_args, sort_by, sort_reverse)
    if users.items:
        if current_user.user_type == UserTypes.ADMIN:
            title = "Manage Users"
            table = ManageUsersTable(users.items, sort_by=sort_by, sort_reverse=sort_reverse)
        elif current_user.user_type == UserTypes.STORE_MANAGER:
            title = "Manage Drivers"
            table = ManageDriversTable(users.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = users.iter_pages()
        return render_template("manage_users.html", current_page=page_args["page"], form=form, num_pages=users.pages, pages=pages, search_query=search_query, sort_by=sort_by, sort_reverse=sort_reverse_string, table=table, title=title)
    else:
        flash("No results.", "info")
        return redirect(request.referrer)

@app.route("/order")
@login_required
def order():
    id = request.args.get("id", type=int)
    order = Order.query.get(id)
    if not order:
        flash("Invalid order ID.", "danger")
        return redirect(url_for("home"))
    if current_user != order.sponsorship.driver and current_user.employer != order.sponsorship.sponsor and current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    items = []
    subtotal = 0
    api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
    for item in order.items:
        call = {
        'keywords': item.ebay_id
        }
        response = api.execute('findItemsByKeywords', call)
        name = response.reply.searchResult.item[0].title
        points = int(float(response.reply.searchResult.item[0].sellingStatus.currentPrice.value)*100)
        cart_item = ItemTableItem(name=name, points=points, item_id=item.id, sponsorship_id=id)
        items.append(cart_item)
        subtotal += points
    table = ItemTable(items)
    table.remove.show = False
    if order.status == Status.CANCELED:
        canceled = True
    else:
        canceled = False
    return render_template("order.html", canceled=canceled, order=order, subtotal=subtotal, table=table)

@app.route("/orders", methods=["GET","POST"])
@login_required
def orders():
    if current_user.user_type == UserTypes.DRIVER:
        title = "My Orders"
        filters = [and_(Order.sponsorship_id.is_(Sponsorship.id), Sponsorship.user_id.is_(current_user.id))]
    elif current_user.user_type == UserTypes.STORE_MANAGER:
        title = f"{current_user.employer} Orders"
        filters = [and_(Order.sponsorship_id.is_(Sponsorship.id), Sponsorship.sponsor_id.is_(current_user.employer.id))]
    else:
        title = "All Orders"
        filters = []
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "date")
    sort_reverse_string = request.args.get("sort_reverse", "desc")
    sort_reverse = sort_reverse_string == "desc"
    search_list = []
    form = SearchForm()
    if request.method == "POST":
        search_query = form.search.data
        if search_query:
            search_list = search_query.split(" ")
            search_query = search_query.replace(" ", "+")
    elif request.method == "GET":
        search_query = request.args.get("search_query")
        if search_query:
            search_list = search_query.split("+")
            form.search.data = search_query.replace("+", " ")
    if search_list:
        append_list = []
        for word in search_list:
            append_list.append(Order.id.like("%" + word + "%"))
            append_list.append(and_(Order.sponsorship_id.is_(Sponsorship.id), 
                               Sponsorship.sponsor_id.is_(Sponsor.id), 
                               Sponsor.name.like("%" + word + "%")))
        filters.append(or_(*append_list))
    orders = get_sorted_page(Order, filters, page_args, sort_by, sort_reverse)
    if orders and orders.items:
        table = OrdersTable(orders.items, sort_by=sort_by, sort_reverse=sort_reverse)
        if current_user.user_type == UserTypes.DRIVER:
            table.driver.show = False
            table.sponsor.show = True
        elif current_user.user_type == UserTypes.STORE_MANAGER:
            table.driver.show = True
            table.sponsor.show = False
        else:
            table.driver.show = True
            table.sponsor.show = True
        pages = orders.iter_pages()
        return render_template("orders.html", form=form, title=title, table=table,
                pages=pages, current_page=page_args["page"], num_pages=orders.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No results.", "info")
        return redirect(request.referrer)

@app.route("/profile")
@login_required
def profile():
    id = request.args.get("id", current_user.id, type=int)
    user = User.query.get(id)
    picture = url_for("static", filename=f"profile_pictures/{user.picture}")
    return render_template("profile.html", title=f"{user.first_name}'s Profile", user=user, picture=picture)

@app.route("/reject_driver", methods=["POST"])
@login_required
def reject_driver():
    id = request.args.get("id", type=int)
    user = User.query.get(id)
    if current_user.user_type != UserTypes.STORE_MANAGER or current_user.employer not in user.applied_sponsors():
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    for sponsorship in user.sponsorships:
        if current_user.employer == sponsorship.sponsor:
            sponsorship.driver = None
            sponsorship.sponsor = None
            db.session.delete(sponsorship)
            db.session.commit()
            flash(f"Successfully rejected {user}.", "success")
    return redirect(request.referrer)

@app.route("/remove_from_cart", methods=["GET", "POST"])
@login_required
def remove_from_cart():
    sponsorship_id = request.args.get("sponsorship", type=int)
    item_id = request.args.get("item", type=str)
    if not sponsorship_id or not item_id:
        flash("Unable to remove from cart.", "info")
        return redirect(url_for("home"))
    sponsorship = Sponsorship.query.get(sponsorship_id)
    if current_user != sponsorship.driver:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(url_for("home"))
    item = Item.query.get(item_id)
    if not item or item not in sponsorship.cart:
        return redirect(url_for("cart", id=sponsorship_id))
    sponsorship.cart.remove(item)
    if not item.catalogs and not item.carts and not item.orders:
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for("cart", id=sponsorship_id))

@app.route("/remove_sponsor", methods=["POST"])
@login_required
def remove_sponsor():
    id = request.args.get("id", type=int)
    sponsor = Sponsor.query.get(id)
    if current_user not in sponsor.managers and current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    for sponsorship in sponsor.sponsorships:
        db.session.delete(sponsorship)
    for manager in sponsor.managers:
        for support_ticket in manager.support_tickets:
            db.session.delete(support_ticket)
        db.session.delete(manager)
    db.session.delete(sponsor)
    db.session.commit()
    flash(f"Successfully removed {sponsor}.", "success")
    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    else:
        return redirect(request.referrer)

@app.route("/remove_user", methods=["POST"])
@login_required
def remove_user():
    if current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    id = request.args.get("id", type=int)
    user = User.query.get(id)
    user.employer = None
    for sponsorship in user.sponsorships:
        for order in sponsorship.orders:
            db.session.delete(order)
        db.session.delete(sponsorship)
    for support_ticket in user.support_tickets:
        db.session.delete(support_ticket)
    db.session.delete(user)
    db.session.commit()
    send_account_removed_email(user)
    flash(f"Successfully removed {user}.", "success")
    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    else:
        return redirect(request.referrer)

@app.route("/report_issue", methods=["GET", "POST"])
@login_required
def report_issue():
    form = SupportForm()
    if form.validate_on_submit():
        support_ticket = SupportTicket(title=form.title.data, description=form.description.data)
        support_ticket.user = current_user
        db.session.add(support_ticket)
        db.session.commit()
        form.title.data = ""
        form.description.data = ""
        flash(f"Ticket #{support_ticket.id} submitted", "success")
        return render_template("report_issue.html", title="Report Issue", form=form)
    elif request.method == "GET" and current_user.is_authenticated:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    return render_template("report_issue.html", title="Report Issue", form=form)

@app.route("/reports")
@login_required
def reports():
    if current_user.user_type != UserTypes.ADMIN:
        flash("Sorry, you are not allowed to access this page.", "danger")
        return redirect(request.referrer)
    api = Finding(config_file='website/ebay.yaml', debug=True, siteid="EBAY-US")
    total_sales = 0
    orders = Order.query.all()
    for order in orders:
        for item in order.items:
            call = {
            'keywords': item.ebay_id
            }
            response = api.execute('findItemsByKeywords', call)
            if response.reply.ack != "Failure" and response.reply.searchResult._count != "0":
                total_sales += float(response.reply.searchResult.item[0].sellingStatus.currentPrice.value)
    total_sales = round(total_sales, 2)
    admin_fee = round((total_sales / 100), 2)
    return render_template("reports.html", title="Reports", total_sales=total_sales, admin_fee=admin_fee)

@app.route("/request_reset", methods=["GET", "POST"])
def request_reset():
    if current_user.is_authenticated:
        return redirect(url_for("profile", id=current_user.id))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash("A reset link has been sent to your email", "info")
        return redirect(url_for("sign_in"))
    return render_template("reset_request.html", title="Reset Password", form=form)

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token")
    if current_user.is_authenticated:
        return redirect(url_for("profile", id=current_user.id))
    user = User.verify_reset_token(token)
    if user is None:
        flash("Reset link is invalid or expired", "warning")
        return redirect(url_for("request_reset"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user.password = hashed_password
        db.session.commit()
        flash(f"{user.first_name}, Your password was reset. Please sign in.", "success")
        return redirect(url_for("sign_in"))
    return render_template("reset_password.html", title="Reset Password", form=form)

@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("profile", id=current_user.id))
    form = SignInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for("profile", id=current_user.id))
        else:
            flash("Login unsuccessful. Email or password incorrect. Please try again.", "danger")
    return render_template("sign_in.html", title="Sign In", form=form)

@app.route("/sign_out")
@login_required
def sign_out():
    logout_user()
    return redirect(url_for("home"))

@app.route("/sponsor", methods=["GET", "POST"])
def sponsor():
    id = request.args.get("id", type=int)
    if id:
        sponsor_account = Sponsor.query.get(id)
    else:
        flash("Invalid sponsor ID.", "danger")
        return redirect(url_for("sponsors"))
    form = UpdateSponsorForm()
    picture = url_for("static", filename=f"profile_pictures/{sponsor_account.picture}")
    if form.validate_on_submit():
        if sponsor_account.name != form.name.data and Sponsor.query.filter_by(name=form.name.data).first():
            form.name.errors.append(ValidationError("Name already used. Try again."))
            return render_template("sponsor.html", title=sponsor_account, sponsor=sponsor_account, picture=picture, form=form)
        else:
            sponsor_account.name = form.name.data
        if form.picture.data:
            random_name = secrets.token_hex(8)
            _, extension = os.path.splitext(form.picture.data.filename)
            file_name = random_name + extension
            path = os.path.join(app.root_path, "static/profile_pictures", file_name)
            size = 500, 500
            picture = Image.open(form.picture.data)
            picture.thumbnail(size)
            picture.save(path)
            path = os.path.join(app.root_path, "static/profile_pictures", sponsor_account.picture)
            if sponsor_account.picture != "default_sponsor.jpg" and os.path.exists(path):
                os.remove(path)
            sponsor_account.picture = file_name
        db.session.commit()
        flash("Sponsor information has been updated", "success")
        return redirect(url_for("sponsor", id=id))
    elif request.method == "GET":
        form.name.data = sponsor_account.name
    return render_template("sponsor.html", title=sponsor_account, sponsor=sponsor_account, picture=picture, form=form)

@app.route("/sponsors")
def sponsors():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    filters = []
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    sponsor_list = get_sorted_page(Sponsor, filters, page_args, sort_by, sort_reverse)
    if sponsor_list.items:
        table = ViewSponsorsTable(sponsor_list.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = sponsor_list.iter_pages()
        return render_template("sponsors.html", title="Sponsors", table=table, pages=pages, current_page=page_args["page"], num_pages=sponsor_list.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No sponsors enrolled.", "info")
        return redirect(url_for("home"))

@app.route("/sponsor_application", methods=["GET", "POST"])
def sponsor_application():
    if current_user.is_authenticated:
        return redirect(url_for("profile", id=current_user.id))
    form = SponsorApplicationForm()
    if form.validate_on_submit():
        sponsor = Sponsor(name=form.name.data)
        db.session.add(sponsor)
        db.session.commit()
        flash(f"{sponsor.name}, Your application has been submitted.", "success")
        return redirect(url_for("home"))
    return render_template("sponsor_application.html", title="Sponsor Application", form=form)

@app.route("/sponsorships")
@login_required
def sponsorships():
    if current_user.user_type == UserTypes.STORE_MANAGER:
        filters = [Sponsorship.sponsor_id.is_(current_user.employer_id), Sponsorship.active.is_(True)]
    else:
        id = request.args.get("id", current_user.id, type=int)
        user = User.query.get(id)
        if current_user.user_type == UserTypes.DRIVER and current_user != user:
            flash("Sorry, you are not allowed to access this page.", "danger")
            return redirect(request.referrer)
        if user.user_type != UserTypes.DRIVER or not user.active_sponsors():
            flash("User has no active sponsorships.", "danger")
            return redirect(request.referrer)
        filters = [Sponsorship.user_id.is_(user.id), Sponsorship.active.is_(True)]
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    page_args = {"page": page, "per_page": per_page}
    sort_by = request.args.get("sort_by", "id")
    sort_reverse_string = request.args.get("sort_reverse", "asc")
    sort_reverse = sort_reverse_string == "desc"
    sponsorship_list = get_sorted_page(Sponsorship, filters, page_args, sort_by, sort_reverse)
    if sponsorship_list.items:
        if current_user.user_type == UserTypes.STORE_MANAGER:
            title = "Manage Drivers"
            table = ManageDriversTable(sponsorship_list.items, sort_by=sort_by, sort_reverse=sort_reverse)
        else:
            title = "Sponsorships"
            table = DriverSponsorshipsTable(sponsorship_list.items, sort_by=sort_by, sort_reverse=sort_reverse)
        pages = sponsorship_list.iter_pages()
        return render_template("sponsorships.html", title=title, table=table, pages=pages, current_page=page_args["page"], num_pages=sponsorship_list.pages, sort_by=sort_by, sort_reverse=sort_reverse_string)
    else:
        flash("No sponsorships established.", "info")
        return redirect(url_for("home"))
