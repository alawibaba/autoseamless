#!/usr/bin/python

import datetime
import favorites
import seamless_browser

from flask_frontend import *

thismin = (lambda x: x.hour * 60 + x.minute)(datetime.datetime.now())
wk = None
dry_run=False

for user in User.query.filter_by(minute = thismin):
    print "User %s" % user.username
    if user.disabled:
        print "Disabled."
        user.disabled = False
        db.session.commit()
        continue
    try:
        def log(msg):
            global msgbuf
            msgbuf += msg + "\n"
        print "Ordering lunch."
        selector = favorites.FavoritesSelector(user.favorites.split("\n"), log=log)
        login_credentials = "username=%s&password=%s" % (user.username, user.password)
        msgbuf = ""
        sb = seamless_browser.SeamlessBrowser(log).order(login_credentials, seamless_browser.DEFAULT_PHONE, selector, wk=wk, dry_run=dry_run)
        print "Success."
    except Exception as e:
        msgbuf += "\n%s\n" % repr(e)
    report = Message(user_id=user.id, message=msgbuf, created_at=datetime.datetime.now())
    db.session.add(report)
db.session.commit()
