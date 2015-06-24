#!/usr/bin/python

import BeautifulSoup
import cookielib
import datetime
import re
import urllib2
import urlparse
import xml.etree.ElementTree

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36"

SEAMLESS_LOGIN_URL = "https://www.seamless.com/food-delivery/login.m"
SEAMLESS_GROUP_ORDER_URL = "https://www.seamless.com/grouporder.m?SubVendorTypeId=1"
SEAMLESS_AJAX_URL = "https://www.seamless.com/Ajax.m"
SEAMLESS_CHECKOUT_URL = "https://www.seamless.com/Checkout.m"
SEAMLESS_CCINFO_URL = "https://www.seamless.com/MyAccount.m?myAccountView=CreditCardInfo"
SEAMLESS_HISTORY_URL = "https://www.seamless.com/OrderHistory.m"
SEAMLESS_UPDATE_ACCOUNT_URL = "https://www.seamless.com/UpdateMyAccount.m"

REQUEST_LOG = None

DEFAULT_PHONE = "(617)555-3000"
DEFAULT_TIP = 1.1

class SeamlessBrowser:
    """The interface between python and the seamless website. (This is the seam,
    if you will.) This was not written, but emerged fully-formed from the head
    of Zeus."""

    def __init__(self, log):
        """Constructor.

        Arguments:
        log -- A method that takes strings for input and does whatever it wants
               with them, like printing them out, writing them to a file, or
               broadcasting them to all and sundry.
        """
        self.ua = USER_AGENT
        self.cookie_jar = cookielib.CookieJar()
        self.url_opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(
                self.cookie_jar))
        self.last_url = ""
        self.log = log

    def _request(
            self,
            url,
            headers=[],
            postdata=None,
            send_referer=True,
            update_url=True):
        """Issue a low-level request (called an HTTP request) to seamless via
        its undocumented API. Never do this.

        Arguments:
        url -- The URL to request.
        headers -- A list of tuples (keyword, value pairs) to include as HTTP
                   headers.
        postdata -- A URL-encoded string of post data (default: None, indicating
                    a GET request).
        send_referer -- Include the last URL requested via the HTTP-Referer
                        header (default: True).
        update_url -- Record this URL as the last URL -- you should set this to
                      False for AJAX-like requests (default: True).

        Returns the response (as a string).
        """
        if self.last_url:
            url = urlparse.urljoin(self.last_url, url)
        if send_referer and self.last_url and self.last_url != "":
            headers = [('referer', self.last_url)] + headers
        headers = [('User-Agent', self.ua)] + headers
        self.url_opener.addheaders = headers
        if update_url:
            self.last_url = url
        response = self.url_opener.open(url, postdata).read()
        if REQUEST_LOG:
            REQUEST_LOG.write("url = %s\n" % url)
            REQUEST_LOG.write("headers = %s\n" % str(headers))
            REQUEST_LOG.write("postdata = %s\n" % str(postdata))
            REQUEST_LOG.write("send_referer = %s\n" % str(send_referer))
            REQUEST_LOG.write("update_url = %s\n" % str(update_url))
            REQUEST_LOG.write("response:\n%s\n\n" % str(response))
        return response

    def login(self, login_credentials):
        """Attempt to login to seamless.

        Arguments:
        login_credentials -- Seamless login credentials (as a post string), like:
                             username=OttoLunch&password=OttosStupidPassword

        Returns True if the login was successful, and False otherwise.
        """
        self._request(SEAMLESS_LOGIN_URL)
        group_order = self._request(
            SEAMLESS_LOGIN_URL,
            postdata="ReturnUrl=%2Ffood-delivery%2Faddress.m&" +
            login_credentials)
        dbg = open("/tmp/group_order", "w") ; dbg.write(group_order) ; dbg.close()
        parsed_group_order = BeautifulSoup.BeautifulSoup(group_order)
        if parsed_group_order.title.text.startswith("Bad Login"):
            self.log("Login incorrect.")
            return False
        self.parsed_group_order = parsed_group_order
        return True

    def list_restaurants(self, wk):
        """Return a list of restaurants for the given day.

        Arguments:
        wk -- The day of the week, as a string (e.g., "Wednesday").

        Returns a list of restaurants, or False if there aren't any.
        """
        todays_tag = self.parsed_group_order.find('h3', text=re.compile(wk))
        if todays_tag is None:
            self.log(
                "It looks like we either don't order today or it's too late to do so.\nSorry about that!")
            return False
        todays_tag = todays_tag.parent
        return todays_tag.findNextSibling("ul").findChildren("a")

    def select_restaurant(self, wk, restaurant_selector):
        """Select the restaurant you'd like to order from.

        Arguments:
        wk -- The day of the week, as a string (e.g., "Wednesday").
        restaurant_selector -- A method that takes a list of restaurants
                               as a parameter, and returns a list.

        Returns True if the restaurant was chosen successfully, and
        False otherwise.
        """

        todays_restaurants = self.list_restaurants(wk)
        if todays_restaurants is False:
            return False
        desired_restaurant = restaurant_selector.restaurant_match(todays_restaurants)

        if len(desired_restaurant) == 0:
            self.log("Restaurant not found.")
            return False
        if len(desired_restaurant) > 1:
            self.log(
                "Warning: multiple restaurants matched -- taking the first one!")
        desired_restaurant = desired_restaurant[0]['href']

        self.last_url = SEAMLESS_GROUP_ORDER_URL
        restaurant_page = self._request(desired_restaurant)
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
        """Requests the item description page for the desired item.

        Arguments:
        desired_item -- The item you'd like, as a BeautifulSoup object.

        Returns item_page, parsed_item_page, form_defaults, all_options,
        radio_buttons, and check_boxes, where:
          item_page -- The item description page, as a string.
          parsed_item_page -- The item description page, as a BeautifulSoup
                              object.
          form_defaults -- The default options as a dictionary.
          all_options -- A list of all possible options.
          radio_buttons -- List of options that are radio buttons.
          check_boxes -- List of options that are check boxes.
        """

        item_url_re = re.compile("MealsMenuSelectionPopup.m[^']*'")
        match = item_url_re.search(desired_item['href'])
        if match is None:
            log("We ran into trouble parsing the item URL. Giving up!")
            return False
        item_url = match.group()

        item_page = self._request(item_url)
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
        """Add an item to your order.

        Arguments:
        desired_item -- The item you'd like.
        update_options -- A method for selecting the options you'd like
                          (default: None, meaning just use the
                          defaults).

        Returns True if the item was added successfully, and False otherwise.
        """

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
            # clear unselected check_boxes
            for k in check_boxes:
                if k in options:
                    del options[k]
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

        add_item_response = self._request(
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
        """Select the items you'd like.

        Arguments:
        restaurant_selector -- A method that takes a list of items
                               as a parameter, and returns a list.

        Returns True if the item(s) were added successfully, and
        False otherwise.
        """

        desired_item_candidates = item_selector.item_match(self.menu)
        if len(desired_item_candidates) == 0:
            self.log("No items selected!")
            return False
        for desired_item, option_selector in desired_item_candidates:
            if not self.add_item_to_order(desired_item, option_selector):
                return False
        return True

    def get_order_summary(self):
        """Requests the current order total from seamless.

        Returns the current total if possible, None if the request
        fails for any reason.
        """

        pdata = "ajaxCommand=74~1&74~1CssClass=OrderStep3&74~1orderId=%s&74~1action=Save" % self.order_id
        summary_response = self._request(
            SEAMLESS_AJAX_URL,
            postdata=pdata,
            update_url=False)
        match = re.compile('GrandTotal=\'\$([^\']*)\'').search(summary_response)
        if match:
            return match.group(1)
        return None

    def checkout(self, phone_number=DEFAULT_PHONE):
        """Attempt to complete the current order.

        Arguments:
        phone_number -- Who do you want Seamless to call if they need help?
                        (default: seamless_browser.DEFAULT_PHONE)

        Returns True if the order was placed successfully, and False otherwise.
        """

        # checkout
        alloc = self.get_order_summary()
        if alloc is None:
            alloc = "%.2f" % (self.total_price * DEFAULT_TIP)  # just guess!
        year = datetime.datetime.now().year

        pdata = "goToCheckout=NO&TotalAlloc=%s00&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=%s&EcoToGoUserId=%s&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=%s&AllocationAmt1=%s&FirstName=&LastName=&NewAllocationAmt=&allocCount=1&totalAllocated=$%s&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=%d&creditCardZipCode=&CreditCardCVV=&saveCreditCardInfo=&ccClicked=no&ccTextChange=no&savedCCNumber=&savedCCType=&currentType=&OrderIdClicked=%s&FloorRoom=9&phone_number=%s&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals" % (
            alloc, self.order_id, self.user_id, self.order_id, alloc, alloc, year, self.order_id, phone_number)

        checkout_response = self._request(
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
        """Login to Seamless, select restaurant, add items, select options,
        and complete the order.

        Arguments:
        login_credentials -- Seamless login credentials (as a post string), like:
                             username=OttoLunch&password=OttosStupidPassword
        phone_number -- Who do you want Seamless to call if they need help?
        selector -- A selector.Selector instance.
        dry_run -- Create the order, but don't actually place it (default: False).
        wk -- The day of the week, as a string (default: today).

        Return value:
        0 - Successful order.
        1 - Login incorrect.
        2 - Restaurant selection failed.
        3 - Item selection failed.
        4 - Checkout failed.
        """

        wk = wk or datetime.datetime.now().strftime("%A")
        #
        self.log("Selected day is %s. Let's see if we need to order anything..." % wk)
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

    def to_json(self):
        """Emits json-compatible object (a dict, to be precise) that contains the state.
        It can be loaded again (to restore the seamless_browser to a previous state)
        via the from_json method.

        This is not well-tested and probably shouldn't be used."""
        rvalue = {"last_url": self.last_url, \
                  "cookie_jar": [(c.version, c.name, c.value, c.port, c.port_specified, c.domain, c.domain_specified, c.domain_initial_dot, c.path, c.path_specified, c.secure, c.expires, c.discard, c.comment, c.comment_url, c.rfc2109) for c in self.cookie_jar], \
                }
        for attr in ["user_id", "total_price", "order_id"]:
            try:
                rvalue[attr] = getattr(self, attr)
            except AttributeError:
                pass
        try:
            rvalue['group_order_page'] = str(self.parsed_group_order)
        except AttributeError:
            pass
        try:
            rvalue["menu"] = [(item.text, item['href']) for item in self.menu]
        except AttributeError:
            pass
        return rvalue

    def from_json(self, json):
        """Absorbs json-compatible object (a dict, to be precise) that contains the state.
        The argument should have been the output of the to_json method.

        This is not well-tested and probably shouldn't be used.

        Arguments:
        json -- A dict, output of SeamlessBrowser.to_json, containing the state that you
                would like to restore.
        """
        class MenuItem:
            def __init__(self, text, href):
                self.text = text
                self.href = href
            def __getitem__(self, key):
                if key == "href":
                    return self.href
                raise KeyError(key)
        self.last_url = json["last_url"]
        for c in json["cookie_jar"]:
            cookie = cookielib.Cookie(*c)
            self.cookie_jar.set_cookie(cookie)
        for attr in ["user_id", "total_price", "order_id"]:
            if attr in json:
                setattr(self, attr, json[attr])
        if 'group_order_page' in json:
            self.parsed_group_order = BeautifulSoup.BeautifulSoup(json['group_order_page'])
        if 'menu' in json:
            self.menu = [MenuItem(text, href) for (text, href) in json['menu']]

    def profile_has_saved_cc(self):
        """Does the current user have a credit card saved in his/her seamless account?
        Returns a tuple of len 2. The first memeber of the tuple is a boolean indicating
        whether or not xe has CC info saved (True if so). The second is the anti-forgery
        token to update the information (e.g. to delete it).  Call after you've logged
        in via the 'login' method.
        """
        profile_response = self._request(
            SEAMLESS_CCINFO_URL)
        parsed_response = BeautifulSoup.BeautifulSoup(profile_response)
        try:
            aftoken = parsed_response.findAll("input", attrs={"name": "antiForgeryToken"})[0]['value']
        except KeyError:
            return "", False
        try:
            return aftoken, len(parsed_response.find(id="OverageCCNumber")['value'].strip()) > 0
        except KeyError:
            return aftoken, False

    def delete_saved_cc(self, aftoken):
        """Deletes saved credit card number (if the user has one).

        Returns True on success, False on failure.
        """
        profile_response = self._request(
            SEAMLESS_UPDATE_ACCOUNT_URL,
            postdata="antiForgeryToken=%s&myAccountView=CreditCardInfo&CreditCardSecurityCode=&OverageCreditCardSecurityCode=&PrimaryCCNewUsage=0&PrimaryCCType=&PrimaryCCNumber=&PrimaryCCExpMonth=&PrimaryCCExpYear=&CreditCardZipCode=&OverageCCNewUsage=1&OverageCCType=&OverageCCNumber=&OverageCCExpMonth=&OverageCCExpYear=&OverageCreditCardZipCode=" % aftoken)
        parsed_response = BeautifulSoup.BeautifulSoup(profile_response)
        try:
            return parsed_response.find(id="AlertMessage").text.lower().find("success") >= 0
        except AttributeError:
            return False
