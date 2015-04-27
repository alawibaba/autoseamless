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
        self.cookieJar = cookielib.CookieJar()
        self.urlOpener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(
                self.cookieJar))
        self.lastUrl = ""
        self.log = log

    def request(
            self,
            url,
            headers=[],
            postdata=None,
            sendReferer=True,
            updateURL=True):
        if self.lastUrl:
            url = urlparse.urljoin(self.lastUrl, url)
        if sendReferer and self.lastUrl and self.lastUrl != "":
            headers = [('referer', self.lastUrl)] + headers
        self.urlOpener.addheaders = [('User-agent', self.ua)] + headers
        if updateURL:
            self.lastUrl = url
        return self.urlOpener.open(url, postdata).read()

    def login(self, loginCredentials):
        self.request(SEAMLESS_LOGIN_URL)
        groupOrder = self.request(
            SEAMLESS_LOGIN_URL,
            postdata="ReturnUrl=%2Ffood-delivery%2Faddress.m&" +
            loginCredentials)
        parsedGroupOrder = BeautifulSoup.BeautifulSoup(groupOrder)
        if parsedGroupOrder.title.text.startswith("Bad Login"):
            self.log("Login incorrect.")
            return False
        self.parsedGroupOrder = parsedGroupOrder
        return True

    def listRestaurants(self, wk):
        todaysTag = self.parsedGroupOrder.find('h3', text=re.compile(wk))
        if todaysTag is None:
            self.log(
                "It looks like we either don't order today or it's too late to do so.\nSorry about that!")
            return False
        todaysTag = todaysTag.parent
        return todaysTag.findNextSibling("ul").findChildren("a")

    def selectRestaurant(self, wk, restaurantSelector):
        todaysRestaurants = self.listRestaurants(wk)
        desiredRestaurant = restaurantSelector.restaurantMatch(todaysRestaurants)

        if len(desiredRestaurant) == 0:
            self.log("Restaurant not found.")
            return False
        if len(desiredRestaurant) > 1:
            self.log(
                "Warning: multiple restaurants matched -- taking the first one!")
        desiredRestaurant = desiredRestaurant[0]['href']

        self.lastUrl = SEAMLESS_GROUP_ORDER_URL
        restaurantPage = self.request(desiredRestaurant)
        parsedRestaurantPage = BeautifulSoup.BeautifulSoup(restaurantPage)

        userIdFind = parsedRestaurantPage('input', id='tagUserId')
        if len(userIdFind) == 0:
            self.log("Couldn't find your user ID, giving up.")
            return False
        self.userID = userIdFind[0]['value']

        orderIdFind = parsedRestaurantPage(
            'input',
            id='InfoPopupfavorite_orderId')
        if len(orderIdFind) == 0:
            self.log("Couldn't find your order ID, giving up.")
            return False
        self.orderID = orderIdFind[0]['value']

        allItems = parsedRestaurantPage(
            'a',
            href=re.compile('MealsMenuSelectionPopup.m'))

        # sometimes items will be duplicated, e.g. because the item is
        # one of the most popular for this restaurant
        itemCandidates = {}
        productIdRE = re.compile("ProductId=([0-9]+)&")
        for item in allItems:
            match = productIdRE.search(item['href'])
            if match is None:
                continue
            itemCandidates[match.group(1)] = item
        self.menu = itemCandidates.values()

        self.totalPrice = 0

        return True

    def fetchItemPageOptions(self, desiredItem):
        itemUrlRE = re.compile("MealsMenuSelectionPopup.m[^']*'")
        match = itemUrlRE.search(desiredItem['href'])
        if match is None:
            log("We ran into trouble parsing the item URL. Giving up!")
            return False
        itemUrl = match.group()

        itemPage = self.request(itemUrl)
        parsedItemPage = BeautifulSoup.BeautifulSoup(itemPage)

        formDefaults = {} ; allOptions = {}
        radioButtons = [] ; checkBoxes = []
        for inp in parsedItemPage.find(id='popup')('input'):
            if not inp.has_key('type'): continue
            inpType = inp['type']
            if not inp.has_key('name'):
                continue
            inpName = inp['name']
            inpValue = ""
            if inp.has_key('value'):
                inpValue = inp['value']
            inpID = "%s_%s" % (inpName, inpValue)
            if inp.has_key('id'):
                inpID = inp['id']
            inpPrice = 0. ; inpMaxIncluded = 0
            if inp.has_key("price"):
                inpPrice, inpMaxIncluded = (lambda x: (float(x[0]), int(x[1])))(inp['price'].split("_"))
            inpLabel = ""
            allOptions[inpID] = {"name": inpName, "value": inpValue, "type": inpType, "price": inpPrice, "maxIncluded": inpMaxIncluded}
            if inpType in ["hidden", "text"]:
                formDefaults[inpName] = inpValue
            elif inpType == "radio":
                radioButtons.append(inpName)
                if inp.has_key('checked'):
                    formDefaults[inpName] = inpValue
            elif inpType == "checkbox":
                checkBoxes.append(inpName)
                if inp.has_key('checked'):
                    formDefaults[inpName] = inpValue
        for label in parsedItemPage('label'):
            if label.has_key('for'):
                try:
                    allOptions[label['for']]["label"] = label.text
                except KeyError:
                    # TODO is this worth a warning message?
                    pass

        return itemPage, parsedItemPage, formDefaults, allOptions, radioButtons, checkBoxes

    def addItemToOrder(self, desiredItem, updateOptions=None):
        itemPage, parsedItemPage, formDefaults, allOptions, radioButtons, checkBoxes = self.fetchItemPageOptions(desiredItem)

        originalPriceMatch = re.compile("originalPrice = '([.0-9]*)';").search(itemPage)
        if originalPriceMatch is None:
            self.log("Couldn't find the price of this item.")
            return False
        originalPrice = float(originalPriceMatch.group(1))

        # decisions
        options = {}
        options.update(formDefaults)
        if updateOptions:
            options.update(updateOptions(allOptions))

        # compute the price
        extras = 0. ; priceControlArrayCount = {}
        for k in options.keys():
            v = options[k]
            groupName = k.split("_")[0]
            try:
                priceControlArrayCount[groupName] += 1
            except KeyError:
                priceControlArrayCount[groupName] = 1
            try:
                ao = allOptions["%s_%s" % (k, v)]
                if ao['maxIncluded'] < priceControlArrayCount[groupName]:
                    extras += ao['price']
            except KeyError:
                pass

        itemPrice = (originalPrice + extras) * float(options['quantity'])
        options["price"] = "$%.2f" % itemPrice
        options["selectedRadioButtons"] = "".join(["%s|%s|" % (k,options[k]) for k in radioButtons if k in options.keys()])
        options["selectedCheckBoxes"] = "".join(["%s|%s|" % (k,options[k]) for k in checkBoxes if k in options.keys()])

        pdata = (
            "ajaxCommand=29~0&29~0action=Save&29~0orderId=%s&" %
            self.orderID) + "&".join(
            ["29~0%s=%s" % (key, options[key]) for key in options.keys()])

        addItemResponse = self.request(
            SEAMLESS_AJAX_URL,
            postdata=pdata,
            updateURL=False)
        if addItemResponse.find("Successful") < 0:
            self.log("Failed to add the item; not sure why.")
            return False

        self.totalPrice += itemPrice
        self.log("Successfully added " + desiredItem.text)
        self.log("total price = %f" % self.totalPrice)
        return True

    def selectItems(self, itemSelector):
        desiredItemCandidates = itemSelector.itemMatch(self.menu)
        if len(desiredItemCandidates) == 0:
            self.log("No items selected!")
            return False
        for desiredItem, optionSelector in desiredItemCandidates:
            if not self.addItemToOrder(desiredItem, optionSelector):
                return False
        return True

    def checkout(self, phoneNumber=DEFAULT_PHONE):
        # checkout
        alloc = "%.2f" % (self.totalPrice * TIP)
        year = datetime.datetime.now().year

        pdata = "goToCheckout=NO&TotalAlloc=%s00&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=%s&EcoToGoUserId=%s&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=%s&AllocationAmt1=%s&FirstName=&LastName=&NewAllocationAmt=&allocCount=1&totalAllocated=$%s&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=%d&creditCardZipCode=&CreditCardCVV=&saveCreditCardInfo=&ccClicked=no&ccTextChange=no&savedCCNumber=&savedCCType=&currentType=&OrderIdClicked=%s&FloorRoom=9&phoneNumber=%s&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals" % (
            alloc, self.orderID, self.userID, self.orderID, alloc, alloc, year, self.orderID, phoneNumber)

        checkoutResponse = self.request(
            SEAMLESS_CHECKOUT_URL,
            postdata=pdata,
            updateURL=False)
        parsedCheckoutResponse = BeautifulSoup.BeautifulSoup(checkoutResponse)

        thanksMessage = [x for x in parsedCheckoutResponse(
            'div') if x.has_key('class') and "ThanksForOrder" in x['class']]
        if len(thanksMessage) < 1:
            self.log(
                "Looks like the order failed for some reason -- probably exceeded the meal allowance.")
	    alertMessage = [x.text for x in parsedCheckoutResponse('div') if x.has_key('class') and "warningNote" in x['class']]
            self.log("\n".join(alertMessage))
            return False

        thanksMessage = thanksMessage[0]
        self.log("I think we successfully ordered lunch.")
        self.log("Here's the message from Seamless:")
        self.log(
            re.sub('[ \t\n\r]+', ' ', "\n".join(map(lambda x: x.text, thanksMessage('h3')))))
        return True

    def order(
            self,
            loginCredentials,
            phoneNumber,
            selector,
            dryRun=False,
            wk=None):
        wk = wk or datetime.datetime.now().strftime("%A")
        #
        self.log("Today is %s. Let's see if we need to order anything..." % wk)
        # login, grab group page
        if not self.login(loginCredentials):
            return 1

        # select restaurant, grab menu, user ID, and order ID
        if not self.selectRestaurant(wk, selector):
            return 2

        # select items, add them to the cart
        if not self.selectItems(selector):
            return 3

        if not dryRun:
            if not self.checkout(phoneNumber):
                return 4

        return 0
