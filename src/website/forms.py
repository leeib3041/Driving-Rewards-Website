from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from flask_login import current_user
from wtforms import BooleanField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError
from website.models import CatalogTypes, Categories, Filter_By_Category, Sponsor, User, UserTypes
from website.states import states

class AddressForm(FlaskForm):
    street_1 = StringField("Street 1", validators=[DataRequired(), Length(min=1, max=40)])
    city = StringField("City", validators=[DataRequired(), Length(min=1, max=40)])
    state = SelectField("State", 
                        choices=[state for state in states.items()],
                        validators=[DataRequired()])
    zip_code = IntegerField("Zip Code", validators=[DataRequired(), NumberRange(min=1000, max=99999)])
    submit = SubmitField("Save Address")

class AddSponsorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=1, max=40)])
    submit = SubmitField("Add Sponsor")

    def validate_name(self, name):
        sponsor = Sponsor.query.filter_by(name=name.data).first()
        if sponsor:
            raise ValidationError("Sponsor already exists. Try again.")

class AddUserForm(FlaskForm):
    user_type = SelectField("User Type", choices=[(choice.name, choice.value) for choice in UserTypes])
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=1, max=20)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=1, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Add User")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already used. Try again.")

class CatalogCategoriesForm(FlaskForm):
    category = SelectField("Catalog Category", choices=[(choice.name, choice.value) for choice in Categories])
    submit = SubmitField("Update Catalog")

class CatalogRulesForm(FlaskForm):
    search = StringField("Search")
    price = SelectField("Max", choices=[(200, "Under 200 Points"), (500, "Under 500 Points"), (750, "Under 750 Points"), (1000, "Under 1000 Points")])
    condition = SelectField("Select", choices=[(1000, "New"), (3000, "Used"), (1500, "Open Box"), (2000, "Manufacturer Refurbished")])
    submit = SubmitField("Update Catalog")

class CatalogSettingsForm(FlaskForm):
    point_value = IntegerField("Point Value", validators=[DataRequired(), NumberRange(min=1)])
    catalog_type = SelectField("Catalog Type", choices=[(choice.name, choice.value) for choice in CatalogTypes])
    submit = SubmitField("Update Settings")

class DriverApplicationForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=1, max=20)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=1, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Apply")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already used. Try signing in or resetting your password.")

class RequestResetForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError("No account with that email. Try again.")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Reset Password")

class SearchForm(FlaskForm):
    search = StringField("Search")
    submit = SubmitField("Submit")

class SignInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64)])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

class SponsorApplicationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=1, max=40)])
    submit = SubmitField("Apply")

    def validate_name(self, name):
        sponsor = Sponsor.query.filter_by(name=name.data).first()
        if sponsor:
            raise ValidationError("Sponsor name already in use. Try again.")

class SupportForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=1, max=20)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=1, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=40)])
    description = TextAreaField("Please describe your issue.", validators=[DataRequired()])
    submit = SubmitField("Submit Ticket")

class UpdateAccountForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=1, max=20)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=1, max=20)])
    employer = SelectField("Employer", 
                            choices=[(sponsor.id, sponsor.name) for sponsor in Sponsor.query.all()], 
                            coerce=int, 
                            validators=[Optional()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    picture = FileField("Update Profile Picture", validators=[FileAllowed(["jpg","png"])])
    issue_alert = BooleanField("Alert me when there is an issue with my order")
    order_alert = BooleanField("Alert me when an order is placed")
    points_alert = BooleanField("Alert me when points are added or removed from my account")
    submit = SubmitField("Update")

class UpdateSponsorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=1, max=40)])
    picture = FileField("Update Profile Picture", validators=[FileAllowed(["jpg","png"])])
    submit = SubmitField("Update")

