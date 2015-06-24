import datetime
import seamless_browser
import pdb
import re
import requests
import random
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

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String())
    created_at = db.Column(db.DateTime())

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
</form> <a href="%s">logout</a> <br/><br/>Messages:<br/>%s''' % (escape(user.username), url_for('update_settings'), user.favorites, user.minute/60, user.minute%60, {True: "checked", False: ""}[user.disabled], url_for('logout'), ("<hr/>").join(map(lambda x: "%s <pre style='white-space: pre-wrap;'>%s</pre>" % (x.created_at.strftime("%m/%d/%Y %H:%M %p"), x.message), Message.query.filter_by(user_id=user.id).order_by(Message.created_at.desc()).limit(5))))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        sb = seamless_browser.SeamlessBrowser(log)
        if sb.login("username=%s&password=%s" % (username, password)):
            user = User.query.filter_by(username=username).first()
            if user is None:
#                return "Sorry, no new autoseamless accounts right now."
                if 'aftoken' in request.form and sb.delete_saved_cc(request.form['aftoken']):
                    # great, deleted their CC info. whoopdeedo.
                    pass
                aftoken, saved_cc = sb.profile_has_saved_cc()
                if saved_cc:
                    return "It looks like your profile has a credit card number associated with it. With great power comes great responsibility, and that's too much responsibility for me to handle.<br/>If you wouldn't mind deleting your credit card from your seamless profile, I'm sure we could work something out.<br/><br/>Alternatively, if this is a risk you really want to take, please go ahead and <a href='http://www.github.com/alawibaba/autoseamless'>grab autoseamless from github</a> and feel free to run your own instance.<br/><br/><form method=post><input type=submit value='Delete it for me!' /><input type=hidden name=username value=\"%s\"/><input type=hidden name=password value=\"%s\"/><input type=hidden name=aftoken value=\"%s\"></form>" % (username, password, aftoken)
                user = User(username=username, password=password, favorites=\
"""#sample favorites file
# each block is a restaurant -- they start with [Restaurant Name]
# other lines are comments (like this one), empty, or are meals
# each meal is a comma-separated list of items, {with options optionally between braces}
# Feel free to add, subtract, etc. from this to get what you like.
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
Lunch Duck Fried Rice

[Cafe 472]
Triple Grilled Cheese Panini, Garlic Bread with Cheese

[Thelonious Monkfish]
Monkfish Fried Rice {Shrimp}, Sticky Rice

[Bailey & Sage]
Grilled Caprese Sandwich

[B. Good]
SW19 El Guapo Chicken Sandwich, SD01 Real Fries
""", minute=random.randint(540, 595), disabled=False)
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
    <!-- <img src="http://autoseamless.com/autoseamless.png" height=100 /><br/> -->
    I know this is the sketchy alley equivalent of a website, but you're in a good place.<br/><br/>
        <form action="" method="post">
            <p>Seamless Username: <input type=text name=username />
            <p>Seamless Password: <input type=password name=password />
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
