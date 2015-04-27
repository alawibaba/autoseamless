#!/usr/bin/python

import BeautifulSoup
import cookielib
import datetime
import re
import urllib2
import urlparse

USER_AGENT = "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36"

SEAMLESS_LOGIN_URL = "https://www.seamless.com/food-delivery/login.m"
SEAMLESS_GROUP_ORDER_URL = "https://www.seamless.com/grouporder.m?SubVendorTypeId=1"
SEAMLESS_AJAX_URL = "https://www.seamless.com/Ajax.m"
SEAMLESS_CHECKOUT_URL = "https://www.seamless.com/Checkout.m"

DEFAULT_PHONE = "(617)555-3000"
TIP = 1.15

class SeamlessBrowser:

    def __init__(self, log):
        self.ua = USER_AGENT
        self.cookie_jar = cookielib.CookieJar()
        self.url_opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(
                self.cookie_jar))
        self.last_url = ""
        self.log = log

    def request(
            self,
            url,
            headers=[],
            postdata=None,
            send_referer=True,
            update_url=True):
        if self.last_url:
            url = urlparse.urljoin(self.last_url, url)
        if send_referer and self.last_url and self.last_url != "":
            headers = [('referer', self.last_url)] + headers
        self.url_opener.addheaders = [('User-agent', self.ua)] + headers
        if update_url:
            self.last_url = url
        return self.url_opener.open(url, postdata).read()

    def login(self, login_credentials):
        self.request(SEAMLESS_LOGIN_URL)
        group_order = self.request(
            SEAMLESS_LOGIN_URL,
            postdata="ReturnUrl=%2Ffood-delivery%2Faddress.m&" +
            login_credentials)
        parsed_group_order = BeautifulSoup.BeautifulSoup(group_order)
        if parsed_group_order.title.text.startswith("Bad Login"):
            self.log("Login incorrect.")
            return False
        self.parsed_group_order = parsed_group_order
        return True

    def list_restaurants(self, wk):
        todays_tag = self.parsed_group_order.find('h3', text=re.compile(wk))
        if todays_tag is None:
            self.log(
                "It looks like we either don't order today or it's too late to do so.\nSorry about that!")
            return False
        todays_tag = todays_tag.parent
        return todays_tag.findNextSibling("ul").findChildren("a")

    def select_restaurant(self, wk, restaurant_selector):
        todays_restaurants = self.list_restaurants(wk)
        desired_restaurant = restaurant_selector.restaurant_match(todays_restaurants)

        if len(desired_restaurant) == 0:
            self.log("Restaurant not found.")
            return False
        if len(desired_restaurant) > 1:
            self.log(
                "Warning: multiple restaurants matched -- taking the first one!")
        desired_restaurant = desired_restaurant[0]['href']

        self.last_url = SEAMLESS_GROUP_ORDER_URL
        restaurant_page = self.request(desired_restaurant)
        parsed_restaurant_page = BeautifulSoup.BeautifulSoup(restaurant_page)

        user_id_find = parsed_restaurant_page('input', id='tagUserId')
        if len(user_id_find) == 0:
            self.log("Couldn't find your user ID, giving up.")
            return False
        self.user_id = user_id_find[0]['value']

        order_id_find = parsed_restaurant_page(
            'input',
            id='InfoPopupfavorite_orderId')
        if len(order_id_find) == 0:
            self.log("Couldn't find your order ID, giving up.")
            return False
        self.order_id = order_id_find[0]['value']

        all_items = parsed_restaurant_page(
            'a',
            href=re.compile('MealsMenuSelectionPopup.m'))

        # sometimes items will be duplicated, e.g. because the item is
        # one of the most popular for this restaurant
        item_candidates = {}
        product_id_re = re.compile("ProductId=([0-9]+)&")
        for item in all_items:
            match = product_id_re.search(item['href'])
            if match is None:
                continue
            item_candidates[match.group(1)] = item
        self.menu = item_candidates.values()

        self.total_price = 0

        return True

    def fetch_item_page_options(self, desired_item):
        item_url_re = re.compile("MealsMenuSelectionPopup.m[^']*'")
        match = item_url_re.search(desired_item['href'])
        if match is None:
            log("We ran into trouble parsing the item URL. Giving up!")
            return False
        item_url = match.group()

        item_page = self.request(item_url)
        parsed_item_page = BeautifulSoup.BeautifulSoup(item_page)

        form_defaults = {} ; all_options = {}
        radio_buttons = [] ; check_boxes = []
        for inp in parsed_item_page.find(id='popup')('input'):
            if not inp.has_key('type'): continue
            inp_type = inp['type']
            if not inp.has_key('name'):
                continue
            inp_name = inp['name']
            inp_value = ""
            if inp.has_key('value'):
                inp_value = inp['value']
            inp_id = "%s_%s" % (inp_name, inp_value)
            if inp.has_key('id'):
                inp_id = inp['id']
            inp_price = 0. ; inp_max_included = 0
            if inp.has_key("price"):
                inp_price, inp_max_included = (lambda x: (float(x[0]), int(x[1])))(inp['price'].split("_"))
            inp_label = ""
            all_options[inp_id] = {"name": inp_name, "value": inp_value, "type": inp_type, "price": inp_price, "max_included": inp_max_included}
            if inp_type in ["hidden", "text"]:
                form_defaults[inp_name] = inp_value
            elif inp_type == "radio":
                radio_buttons.append(inp_name)
                if inp.has_key('checked'):
                    form_defaults[inp_name] = inp_value
            elif inp_type == "checkbox":
                check_boxes.append(inp_name)
                if inp.has_key('checked'):
                    form_defaults[inp_name] = inp_value
        for label in parsed_item_page('label'):
            if label.has_key('for'):
                try:
                    all_options[label['for']]["label"] = label.text
                except KeyError:
                    # TODO is this worth a warning message?
                    pass

        return item_page, parsed_item_page, form_defaults, all_options, radio_buttons, check_boxes

    def add_item_to_order(self, desired_item, update_options=None):
        item_page, parsed_item_page, form_defaults, all_options, radio_buttons, check_boxes = self.fetch_item_page_options(desired_item)

        original_price_match = re.compile("originalPrice = '([.0-9]*)';").search(item_page)
        if original_price_match is None:
            self.log("Couldn't find the price of this item.")
            return False
        original_price = float(original_price_match.group(1))

        # decisions
        options = {}
        options.update(form_defaults)
        if update_options:
            options.update(update_options(all_options))

        # compute the price
        extras = 0. ; price_control_array_count = {}
        for k in options.keys():
            v = options[k]
            group_name = k.split("_")[0]
            try:
                price_control_array_count[group_name] += 1
            except KeyError:
                price_control_array_count[group_name] = 1
            try:
                ao = all_options["%s_%s" % (k, v)]
                if ao['max_included'] < price_control_array_count[group_name]:
                    extras += ao['price']
            except KeyError:
                pass

        item_price = (original_price + extras) * float(options['quantity'])
        options["price"] = "$%.2f" % item_price
        options["selectedRadioButtons"] = "".join(["%s|%s|" % (k,options[k]) for k in radio_buttons if k in options.keys()])
        options["selectedCheckBoxes"] = "".join(["%s|%s|" % (k,options[k]) for k in check_boxes if k in options.keys()])

        pdata = (
            "ajaxCommand=29~0&29~0action=Save&29~0orderId=%s&" %
            self.order_id) + "&".join(
            ["29~0%s=%s" % (key, options[key]) for key in options.keys()])

        add_item_response = self.request(
            SEAMLESS_AJAX_URL,
            postdata=pdata,
            update_url=False)
        if add_item_response.find("Successful") < 0:
            self.log("Failed to add the item; not sure why.")
            return False

        self.total_price += item_price
        self.log("Successfully added " + desired_item.text)
        self.log("total price = %f" % self.total_price)
        return True

    def select_items(self, item_selector):
        desired_item_candidates = item_selector.item_match(self.menu)
        if len(desired_item_candidates) == 0:
            self.log("No items selected!")
            return False
        for desired_item, option_selector in desired_item_candidates:
            if not self.add_item_to_order(desired_item, option_selector):
                return False
        return True

    def checkout(self, phone_number=DEFAULT_PHONE):
        # checkout
        alloc = "%.2f" % (self.total_price * TIP)
        year = datetime.datetime.now().year

        pdata = "goToCheckout=NO&TotalAlloc=%s00&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=%s&EcoToGoUserId=%s&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=%s&AllocationAmt1=%s&FirstName=&LastName=&NewAllocationAmt=&allocCount=1&totalAllocated=$%s&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=%d&creditCardZipCode=&CreditCardCVV=&saveCreditCardInfo=&ccClicked=no&ccTextChange=no&savedCCNumber=&savedCCType=&currentType=&OrderIdClicked=%s&FloorRoom=9&phone_number=%s&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals" % (
            alloc, self.order_id, self.user_id, self.order_id, alloc, alloc, year, self.order_id, phone_number)

        checkout_response = self.request(
            SEAMLESS_CHECKOUT_URL,
            postdata=pdata,
            update_url=False)
        parsed_checkout_response = BeautifulSoup.BeautifulSoup(checkout_response)

        thanks_message = [x for x in parsed_checkout_response(
            'div') if x.has_key('class') and "ThanksForOrder" in x['class']]
        if len(thanks_message) < 1:
            self.log(
                "Looks like the order failed for some reason -- probably exceeded the meal allowance.")
	    alert_message = [x.text for x in parsed_checkout_response('div') if x.has_key('class') and "warningNote" in x['class']]
            self.log("\n".join(alert_message))
            return False

        thanks_message = thanks_message[0]
        self.log("I think we successfully ordered lunch.")
        self.log("Here's the message from Seamless:")
        self.log(
            re.sub('[ \t\n\r]+', ' ', "\n".join(map(lambda x: x.text, thanks_message('h3')))))
        return True

    def order(
            self,
            login_credentials,
            phone_number,
            selector,
            dry_run=False,
            wk=None):
        wk = wk or datetime.datetime.now().strftime("%A")
        #
        self.log("Today is %s. Let's see if we need to order anything..." % wk)
        # login, grab group page
        if not self.login(login_credentials):
            return 1

        # select restaurant, grab menu, user ID, and order ID
        if not self.select_restaurant(wk, selector):
            return 2

        # select items, add them to the cart
        if not self.select_items(selector):
            return 3

        if not dry_run:
            if not self.checkout(phone_number):
                return 4

        return 0
