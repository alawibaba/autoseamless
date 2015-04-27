import datetime
import grablunch
import pdb
import re
import requests
from urlobject import URLObject
from flask import Flask, request, url_for
app = Flask(__name__)
app.debug = True

message_buf = []
def log(msg):
    message_buf.append(msg)
sb = grablunch.SeamlessBrowser(log)

@app.route("/")
def list_restaurants():
    login_credentials = open("piotr").readlines()[0].strip()
    sb.login(login_credentials)
    wk = datetime.datetime.now().strftime("%A")
    restaurant_list = sb.list_restaurants(wk)
    if not restaurant_list:
      return "Looks like we don't order today or it's too late to do so!"
    buf = []
    for restaurant in restaurant_list:
        vlid = URLObject(restaurant['href']).query.dict['vendorLocationId']
        buf.append("<a href='%s'>%s</a>" % (url_for("select_restaurants", id=vlid), restaurant.text))
    return "<br/>".join(buf)

def show_menu():
    buf = []
    for item in sb.menu:
        item_url_re = re.compile("MealsMenuSelectionPopup.m[^']*'")
        match = item_url_re.search(item['href'])
        if match is None:
            continue
        qdict = URLObject(match.group()).query.dict
        pid = qdict['ProductId']
        cid = qdict['CategoryId']
        price = float(qdict['Price'])
        buf.append((cid, "<tr><td><a href='%s'>%s</a></td><td align=right>$%.2f</td></tr>" % (url_for("get_item_options", id=pid), item.text, price)))
    buf.sort()
    return "<table>" + "".join(map(lambda x: x[1], buf)) + "</table>" + "<br/><br/><a href='%s'>Checkout</a>" % url_for("checkout")

@app.route("/select_restaurant")
def select_restaurants():
    def r_selector(restaurants):
        return [restaurant for restaurant in restaurants if URLObject(restaurant['href']).query.dict['vendorLocationId'] == request.args['id']]
    wk = datetime.datetime.now().strftime("%A")
    if not sb.select_restaurant(wk, r_selector):
        return "Something went wrong with selecting that restaurant. Sorry!"
    return show_menu()

@app.route("/get_item_options")
def get_item_options():
    desired_item = [i for i in sb.menu if i['href'].find("ProductId=%s" % request.args['id']) >= 0][0]
    item_page, parsed_item_page, form_defaults, all_options, radio_buttons, check_boxes = sb.fetch_item_page_options(desired_item)
    buf = []
    for optid in all_options:
        option = all_options[optid]
        if option['type'] == "hidden":
            continue
        if not "label" in option:
            continue
        checked = ""
        try:
            if form_defaults[option['name']] == option['value']:
                checked = "checked"
        except KeyError:
            pass
        buf.append((option['name'], "%s <input type=%s name=%s value=%s %s />" % (option['label'], option['type'], option['name'], option['value'], checked)))
    buf.sort()
    buf = map(lambda x: x[1], buf)
    buf.append("<input type=submit value='submit'/>")
    return "<form method=POST action=%s>" % url_for("add_item_to_order", id=request.args['id']) + "<br/>".join(buf) + "</form>"

@app.route("/add_item_to_order", methods=['POST'])
def add_item_to_order():
    desired_item = [i for i in sb.menu if i['href'].find("ProductId=%s" % request.args['id']) >= 0][0]
    message = ""
    if sb.add_item_to_order(desired_item, lambda x: request.form.to_dict(True)):
        message = "Successfully added that item to the order."
    else:
        message = "Failed to add that item to the order."
    return message + "<br/><br/>" + show_menu()

@app.route("/checkout")
def checkout():
    global message_buf
    sb.checkout(None)
    rvalue = "<br/>".join(message_buf) ; message_buf = []
    return rvalue

if __name__ == "__main__":
    app.run()
