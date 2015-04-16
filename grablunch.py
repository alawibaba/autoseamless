#!/usr/bin/python

import BeautifulSoup
import cookielib
import datetime
import re
import random
import sys
import urllib2
import urlparse


class SeamlessBrowser:

    def __init__(self, log):
        self.ua = 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'
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
        self.request('https://www.seamless.com/food-delivery/login.m')
        groupOrder = self.request(
            'https://www.seamless.com/food-delivery/login.m',
            postdata="ReturnUrl=%2Ffood-delivery%2Faddress.m&" +
            loginCredentials)
        parsedGroupOrder = BeautifulSoup.BeautifulSoup(groupOrder)
        if parsedGroupOrder.title.text.startswith("Bad Login"):
            self.log("Login incorrect.")
            return False
        self.parsedGroupOrder = parsedGroupOrder
        return True

    def selectRestaurant(self, wk, restaurantSelector):
        todaysTag = self.parsedGroupOrder.find('h3', text=re.compile(wk))
        if todaysTag is None:
            self.log(
                "It looks like we either don't order today or it's too late to do so.\nSorry about that!")
            return False
        todaysTag = todaysTag.parent
        todaysRestaurants = todaysTag.findNextSibling("ul").findChildren("a")
        desiredRestaurant = restaurantSelector(todaysRestaurants)

        if len(desiredRestaurant) == 0:
            self.log("Restaurant not found.")
            return False
        if len(desiredRestaurant) > 1:
            self.log(
                "Warning: multiple restaurants matched -- taking the first one!")
        desiredRestaurant = desiredRestaurant[0]['href']

        self.lastUrl = "https://www.seamless.com/grouporder.m?SubVendorTypeId=1"
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

    def addItemToOrder(self, desiredItem):
        itemUrlRE = re.compile("MealsMenuSelectionPopup.m[^']*'")
        match = itemUrlRE.search(desiredItem['href'])
        if match is None:
            log("We ran into trouble parsing the item URL. Giving up!")
            return False
        itemUrl = match.group()

        itemPage = self.request(itemUrl)
        parsedItemPage = BeautifulSoup.BeautifulSoup(itemPage)

        # TODO make it possible to change options
        pdata = (
            "ajaxCommand=29~0&29~0action=Save&29~0orderId=%s&" %
            self.orderID) + "&".join(
            [
                x for x in map(
                    lambda x: x.has_key('name') and x.has_key('value') and "29~0%s=%s" %
                    (x['name'], x['value']), parsedItemPage.find('form')('input')) if x])

        addItemResponse = self.request(
            "https://www.seamless.com/Ajax.m",
            postdata=pdata,
            updateURL=False)
        if addItemResponse.find("Successful") < 0:
            self.log("Failed to add the item; not sure why.")
            return False

        itemPrice = float(
            "".join(
                parsedItemPage.find(
                    'input',
                    id='price')['value'].split("$")))
        self.totalPrice += itemPrice
        self.log("Successfully added " + desiredItem.text)
        return True

    def selectItems(self, itemSelector):
        desiredItemCandidates = itemSelector(self.menu)
        if len(desiredItemCandidates) == 0:
            self.log("No items selected!")
            return False
        for desiredItem in desiredItemCandidates:
            if not self.addItemToOrder(desiredItem):
                return False
        return True

    def checkout(self, phoneNumber="(617)555-3000"):
        # checkout
        alloc = "%.2f" % (self.totalPrice * 1.1)
        year = datetime.datetime.now().year

        pdata = "goToCheckout=NO&TotalAlloc=%s00&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=%s&EcoToGoUserId=%s&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=%s&AllocationAmt1=%s&FirstName=&LastName=&NewAllocationAmt=&allocCount=1&totalAllocated=$%s&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=%d&creditCardZipCode=&CreditCardCVV=&saveCreditCardInfo=&ccClicked=no&ccTextChange=no&savedCCNumber=&savedCCType=&currentType=&OrderIdClicked=%s&FloorRoom=9&phoneNumber=%s&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals" % (
            alloc, self.orderID, self.userID, self.orderID, alloc, alloc, year, self.orderID, phoneNumber)

        checkoutResponse = self.request(
            "https://www.seamless.com/Checkout.m",
            postdata=pdata,
            updateURL=False)
        parsedCheckoutResponse = BeautifulSoup.BeautifulSoup(checkoutResponse)

        thanksMessage = [x for x in parsedCheckoutResponse(
            'div') if x.has_key('class') and "ThanksForOrder" in x['class']]
        if len(thanksMessage) < 1:
            self.log(
                "Looks like the order failed for some reason -- probably exceeded the meal allowance.")
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
            restaurantSelector,
            itemSelector,
            dryRun=False,
            wk=None):
        wk = wk or datetime.datetime.now().strftime("%A")
        #
        self.log("Today is %s. Let's see if we need to order anything..." % wk)
        # login, grab group page
        if not self.login(loginCredentials):
            return 1

        # select restaurant, grab menu, user ID, and order ID
        if not self.selectRestaurant(wk, restaurantSelector):
            return 2

        # select items, add them to the cart
        if not self.selectItems(itemSelector):
            return 3

        if not dryRun:
            if not self.checkout(phoneNumber):
                return 4

        return 0

def iSelect(choices):
    for idx, choice in zip(range(len(choices)), choices):
        print idx, choice.text
    idx = -1
    while idx < 0 or idx >= len(choices):
        print "Please enter an integer between 0 and %d (inclusive)." % (len(choices) - 1)
        try:
            idx = int(raw_input("Select> "))
        except ValueError:
            idx = -1
    return [choices[idx]]

def niSelect(itemRE):
    def currySelect(choices):
        rvalue = []
        for choice in choices:
            if itemRE.search(choice.text):
                rvalue.append(choice)
        return rvalue
    return currySelect

rvalue = None
if __name__ == "__main__":
    def log(msg):
        print msg

    loginCredentials = open("alawi").readlines()[0].strip()
    sys.exit(
        SeamlessBrowser(log).order(
            loginCredentials,
            "(617)555-3000",
            niSelect(
                re.compile("Viva Burrito")),
            niSelect(
                re.compile("Plain Quesadilla with Salsa Fresca|Chips with Salsa$")),
            dryRun=False,
            wk="Thursday"))
