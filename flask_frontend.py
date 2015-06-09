import datetime
import seamless_browser
import pdb
import re
import requests
import os
from urlobject import URLObject
from flask import Flask, request, session, redirect, escape, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.json import JSONEncoder
from functools import wraps

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)
app.debug = True

def log(x):
    print x

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String())
    password = db.Column(db.String())
    favorites = db.Column(db.String())
    minute = db.Column(db.Integer())
    disabled = db.Column(db.Boolean())

@app.route("/")
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    return '''Welcome %s.<br/><br/>
<form action=%s method=post>
Your favorites:<br/><textarea name=favorites cols=80 rows=20>%s</textarea><br/>
Order time:<br/><input name=minute type=text value=%d:%02d /><br/>
Don't order tomorrow: <input type=checkbox name=disabled value=True %s /><br/>
<input type=submit name=save /> <br/>
</form> <a href="%s">logout</a>''' % (escape(user.username), url_for('update_settings'), user.favorites, user.minute/60, user.minute%60, {True: "checked", False: ""}[user.disabled], url_for('logout'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        sb = seamless_browser.SeamlessBrowser(log)
        if sb.login("username=%s&password=%s" % (username, password)):
            user = User.query.filter_by(username=username).first()
            if user is None:
                user = User(username=username, password=password, favorites=\
"""#sample favorites file
[Tossed]
Design Your Own Salad {Romaine Hearts, Iceberg Lettuce, Corn, Cucumbers, Fresh Peppers, Chopped Tomatoes, Gluten-Free Balsamic Vinaigrette Dressing, Dressing Mixed In, Lobster Bisque}

[Sugar & Spice]
Fish Story

[India Palace]
Lamb Rogan Josh - Lunch, Raita

[Beijing Tokyo]
Shrimp with Black Bean Sauce Lunch Special

[Alfredo's Italian Kitchen]
Homemade Eggplant Parmigiana Sub, Garlic Bread

[Viva Burrito]
Plain Quesadilla with Salsa Fresca, Chips with Salsa

[Eat at Jumbos]
Vegetarian Sandwich, French Fries

[Curry Thai]
Lunch Crab Fried Rice

[Cafe 472]
Triple Grilled Cheese Panini, Garlic Bread with Cheese

[Thelonious Monkfish]
Monkfish Fried Rice {Shrimp}, Sticky Rice

[Bailey & Sage]
Grilled Caprese Sandwich

[B. Good]
SW19 El Guapo Chicken Sandwich, SD01 Real Fries
""", minute=595, disabled=False)
                db.session.add(user)
                db.session.commit()
            if user.password != password:
                user.password = password
                db.session.commit()
            session['username'] = username
            session['password'] = password
            session.modified = True
        return redirect(url_for('index'))
    return '''
        <form action="" method="post">
            <p><input type=text name=username />
            <p><input type=password name=password />
            <p><input type=submit value=Login />
        </form>
    '''

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/update_settings", methods=['POST'])
def update_settings():
    if 'username' not in session:
        #redirect(url_for('login'))
        abort(401)
    user = User.query.filter_by(username=session['username']).first()
    user.favorites = request.form['favorites']
    user.minute = (lambda x: 60*x[0] + x[1])(map(int, request.form['minute'].split(":")))
    user.disabled = 'disabled' in request.form
    db.session.commit()
    return redirect(url_for('index'))

app.secret_key = "SUPER SECRET" # os.urandom(24)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
