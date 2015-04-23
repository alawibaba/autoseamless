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
          sys.exit(0)
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
            "https://www.seamless.com/Ajax.m",
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
        desiredItemCandidates = itemSelector(self.menu, True)
        if len(desiredItemCandidates) == 0:
            self.log("No items selected!")
            return False
        for desiredItem, optionSelector in desiredItemCandidates:
            if not self.addItemToOrder(desiredItem, optionSelector):
                return False
        return True

    def checkout(self, phoneNumber="(617)555-3000"):
        # checkout
        alloc = "%.2f" % (self.totalPrice * 1.15)
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

def iSelectBasic(choices, labels):
    for idx in xrange(len(choices)):
        print idx, labels[idx]
    idx = -1
    while idx < 0 or idx >= len(choices):
        print "Please enter an integer between 0 and %d (inclusive)." % (len(choices) - 1)
        try:
            idx = int(raw_input("Select> "))
        except ValueError:
            idx = -1
    return choices[idx]

def iSelectMulti(choices, labels):
    for idx in xrange(len(choices)):
        print idx, labels[idx]
    idx = []
    while True:
        print "Please enter a list of integers between 0 and %d (inclusive)." % (len(choices) - 1)
        idxList = raw_input("Select> ")
        if idxList.strip() == "":
            return []
        try:
            return map(lambda k: choices[k], map(int, idxList.split(",")))
        except ValueError:
            pass
        except KeyError:
            pass

def iSelect(choices, optionSelector=False):
    def iOptions(allOptions):
      rvalue = {}
      optionGroups = {}
      for optId in allOptions.keys():
        groupId = optId.split("_")[0]
        try:
          optionGroups[groupId][1].append(optId)
        except KeyError:
          optionGroups[groupId] = (allOptions[optId]['type'], [optId])
      optionGroupKeys = optionGroups.keys()
      optionGroupKeys.sort()
      for optionGroupKey in optionGroupKeys:
        inpType, inpIds = optionGroups[optionGroupKey]
        if inpType == "hidden":
          continue
        elif inpType == "text":
          for inpId in inpIds:
            try:
              print allOptions[inpIds[0]]['label']
              val = raw_input("> ")
              rvalue[inpId] = val
            except KeyError:
              continue
        elif inpType == "radio":
          print "Please select one."
          choices = [] ; labels = []
          for idx, inpId in zip(range(len(inpIds)), inpIds):
            try:
              labels.append(allOptions[inpId]['label'])
              choices.append(inpId)
            except KeyError:
              continue
          inpId = iSelectBasic(choices, labels)
          rvalue[allOptions[inpId]['name']] = allOptions[inpId]['value']
        elif inpType == "checkbox":
          print "Please select as many as you like (separate by commas)."
          choices = [] ; labels = []
          for idx, inpId in zip(range(len(inpIds)), inpIds):
            try:
              labels.append(allOptions[inpId]['label'])
              choices.append(inpId)
            except KeyError:
              continue
          selectedInpIds = iSelectMulti(choices, labels)
          for inpId in selectedInpIds:
            rvalue[allOptions[inpId]['name']] = allOptions[inpId]['value']
      return rvalue
    choice = iSelectBasic(choices, map(lambda x: x.text, choices))
    if optionSelector:
      return [(choice, iOptions)]
    return [choice]

def niSelect(itemRE, optionSelector=None):
    def currySelect(choices, itemSelector=False):
        rvalue = []
        for choice in choices:
            if itemRE.search(choice.text):
                rvalue.append(choice)
        if itemSelector:
            return rvalue, optionSelector
        return rvalue
    return currySelect

def nioSelect(optionList):
    reOptionsList = [re.compile(x) for x in optionList]
    def currySelect(allOptions):
        rvalue = {}
        for inpID in allOptions.keys():
            for reOption in reOptionsList:
                try:
                    if reOption.search(allOptions[inpID]["label"]):
                        rvalue[allOptions[inpID]["name"]] = allOptions[inpID]["value"]
                except KeyError:
                    pass
        return rvalue
    return currySelect

def loadFavorites(fname):
  selections = {}
  currentRestaurant = None
  for line in open(fname):
    x = line.strip()
    if x == "":
      continue
    elif x[0] == "#":
      continue
    elif x[0] == "[":
      currentRestaurant = x.strip()[1:-1]
      selections[currentRestaurant] = []
      continue
    # this line is a meal
    state = 0
    a = [""]
    for c in x:
      if state == 0:
        if c == ",":
          a.append("")
        elif c == "{":
          a[-1] = [a[-1], ""]
          state = 1
        elif c == "\\":
          state = 2
        else:
          a[-1] += c
      elif state == 1:
        if c == ",":
          a[-1].append("")
        elif c == "}":
          state = 0
        elif c == "\\":
          state = 3
        else:
          a[-1][-1] += c
      elif state == 2:
        a[-1] += c
        state = 0
      elif state == 3:
        a[-1][-1] += c
        state = 1
    for idx in xrange(len(a)):
      if type(a[idx]) == str:
        a[idx] = a[idx].strip()
      else:
        for idx2 in xrange(len(a[idx])):
          a[idx][idx2] = a[idx][idx2].strip()
    selections[currentRestaurant].append(a)
  return selections

def favoritesSelector(favorites):
  def restaurantSelector(restaurants):
    restaurantChoices = [] ; numOptions = 0
    for x in favorites.keys():
      for choice in restaurants:
        if choice.text.find(x) >= 0:
          restaurantChoices.append((choice, favorites[x]))
          numOptions += len(favorites[x])
          break
    idx = int(random.uniform(0, numOptions))
    if idx == numOptions: idx -= 1
    for c, l in restaurantChoices:
      if idx < len(l):
        restaurantSelector.choice = l[idx]
        print "Selected %s" % c.text ; sys.stdout.flush()
        return [c]
      idx -= len(l)
  restaurantSelector.choice = None
  def optionSelector(options):
    if len(options) == 0:
      return None
    def rvalue(fullOptionsList):
      optDict = {}
      order = [x for x in fullOptionsList.keys() if 'label' in fullOptionsList[x]]
      order.sort(lambda x,y: len(fullOptionsList[x]['label']) - len(fullOptionsList[y]['label']))
      for opt in options:
        for o in order:
          if fullOptionsList[o]['label'].find(opt) >= 0:
            print "-- %s" % fullOptionsList[o]['label']
            optDict[fullOptionsList[o]['name']] = fullOptionsList[o]['value']
            break
      return optDict
    return rvalue
  def itemSelector(items, includeOptionSelector):
    rvalue = []
    items.sort(lambda x, y: len(x.text)-len(y.text))
    for item in restaurantSelector.choice:
      itemName = item ; options = []
      if type(item) == list:
        itemName = item[0] ; options = item[1:]
      for x in items:
        if x.text.find(itemName) >= 0:
          print "Selected %s" % x.text
          rvalue.append((x, optionSelector(options)))
          break
    return rvalue
  return restaurantSelector, itemSelector

rvalue = None
if __name__ == "__main__":
    def log(msg):
        print msg

    loginCredentials = open("loginCredentials").readlines()[0].strip()
    r, i = favoritesSelector(loadFavorites("favorites.txt"))
    sys.exit(
        SeamlessBrowser(log).order(
            loginCredentials,
            "(617)555-3000",
            r, i))

#    sys.exit(
#        SeamlessBrowser(log).order(
#            loginCredentials,
#            "(617)555-3000",
#            niSelect(
#                re.compile("Sugar \& Spice")),
#            niSelect(
#                re.compile("Three Friends")),
#            wk="Tuesday"))
#    sys.exit(
#        SeamlessBrowser(log).order(
#            loginCredentials,
#            "(617)555-3000",
#            niSelect(
#                re.compile("Tossed")),
#            niSelect(
#                re.compile("Design Your Own Salad")),
#            nioSelect(["^Romaine Hearts", "^Iceberg Lettuce", "^Corn *\(", "^Cucumbers", "^Fresh Peppers", "^Chopped Tomatoes", "Gluten-Free Balsamic Vinaigrette Dressing", "Dressing Mixed In", "Lobster Bisque"]),
#            wk="Tuesday"))
