import datetime
import grablunch
import pdb
import re
import requests
from urlobject import URLObject
from flask import Flask, request, url_for
app = Flask(__name__)
app.debug = True

messageBuf = []
def log(msg):
    messageBuf.append(msg)
sb = grablunch.SeamlessBrowser(log)

@app.route("/")
def listRestaurants():
    loginCredentials = open("piotr").readlines()[0].strip()
    sb.login(loginCredentials)
    wk = datetime.datetime.now().strftime("%A")
    restaurantList = sb.listRestaurants(wk)
    if not restaurantList:
      return "Looks like we don't order today or it's too late to do so!"
    buf = []
    for restaurant in restaurantList:
        vlid = URLObject(restaurant['href']).query.dict['vendorLocationId']
        buf.append("<a href='%s'>%s</a>" % (url_for("selectRestaurants", id=vlid), restaurant.text))
    return "<br/>".join(buf)

def showMenu():
    buf = []
    for item in sb.menu:
        itemUrlRE = re.compile("MealsMenuSelectionPopup.m[^']*'")
        match = itemUrlRE.search(item['href'])
        if match is None:
            continue
        qdict = URLObject(match.group()).query.dict
        pid = qdict['ProductId']
        cid = qdict['CategoryId']
        price = float(qdict['Price'])
        buf.append((cid, "<tr><td><a href='%s'>%s</a></td><td align=right>$%.2f</td></tr>" % (url_for("getItemOptions", id=pid), item.text, price)))
    buf.sort()
    return "<table>" + "".join(map(lambda x: x[1], buf)) + "</table>" + "<br/><br/><a href='%s'>Checkout</a>" % url_for("checkout")

@app.route("/selectRestaurant")
def selectRestaurants():
    def rSelector(restaurants):
        return [restaurant for restaurant in restaurants if URLObject(restaurant['href']).query.dict['vendorLocationId'] == request.args['id']]
    wk = datetime.datetime.now().strftime("%A")
    if not sb.selectRestaurant(wk, rSelector):
        return "Something went wrong with selecting that restaurant. Sorry!"
    return showMenu()

@app.route("/getItemOptions")
def getItemOptions():
    desiredItem = [i for i in sb.menu if i['href'].find("ProductId=%s" % request.args['id']) >= 0][0]
    itemPage, parsedItemPage, formDefaults, allOptions, radioButtons, checkBoxes = sb.fetchItemPageOptions(desiredItem)
    buf = []
    for optid in allOptions:
        option = allOptions[optid]
        if option['type'] == "hidden":
            continue
        if not "label" in option:
            continue
        checked = ""
        try:
            if formDefaults[option['name']] == option['value']:
                checked = "checked"
        except KeyError:
            pass
        buf.append((option['name'], "%s <input type=%s name=%s value=%s %s />" % (option['label'], option['type'], option['name'], option['value'], checked)))
    buf.sort()
    buf = map(lambda x: x[1], buf)
    buf.append("<input type=submit value='submit'/>")
    return "<form method=POST action=%s>" % url_for("addItemToOrder", id=request.args['id']) + "<br/>".join(buf) + "</form>"

@app.route("/addItemToOrder", methods=['POST'])
def addItemToOrder():
    desiredItem = [i for i in sb.menu if i['href'].find("ProductId=%s" % request.args['id']) >= 0][0]
    message = ""
    if sb.addItemToOrder(desiredItem, lambda x: request.form.to_dict(True)):
        message = "Successfully added that item to the order."
    else:
        message = "Failed to add that item to the order."
    return message + "<br/><br/>" + showMenu()

@app.route("/checkout")
def checkout():
    global messageBuf
    sb.checkout(None)
    rvalue = "<br/>".join(messageBuf) ; messageBuf = []
    return rvalue

if __name__ == "__main__":
    app.run()
