import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["MAIL_SERVER"] = "smtp.googlemail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "drivingrewardsportal@gmail.com"
app.config["MAIL_PASSWORD"] = "(y5/(_qk6}$DxW9S"
app.config["SECRET_KEY"] = "f4dcb5e609d25b11773398c7b9569939"
#app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://Team1:CPSC4910???@rds-mysql-4910.cgwq765aahby.us-east-1.rds.amazonaws.com:3306/Good_Driver"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False 
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view= "sign_in"
login_manager.login_message_category = "info"
mail = Mail(app)

from website import routes
