#!/usr/bin/python

import BeautifulSoup
import cookielib
import datetime
import re
import random
import sys
import urllib2
import urlparse

#restaurant = "Cafe 472"
#item = "Grilled Chicken Sandwich"
restaurant="Tossed \(Post Office Sq\)"
item="Cayenne Shrimp Salad"
phoneNumber = "(857)600-6533"

class Browser:
  def __init__(self):
    self.ua = 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'
    self.cookieJar = cookielib.CookieJar()
    self.urlOpener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar))
    self.lastUrl = ""
  def request(self, url, headers=[], postdata=None, sendReferer=True, updateURL=True):
    if self.lastUrl:
      url = urlparse.urljoin(self.lastUrl, url)
    if sendReferer and self.lastUrl and self.lastUrl != "":
      headers = [('referer', self.lastUrl)] + headers
    self.urlOpener.addheaders = [('User-agent', self.ua)] + headers
    if updateURL:
      self.lastUrl = url
    return self.urlOpener.open(url, postdata).read()

def order(log, loginCredentials, phoneNumber, selectRestaurant, selectItem, dryRun=False, wk=None):
  wk=wk or datetime.datetime.now().strftime("%A")
  year=datetime.datetime.now().year
  #
  log("Today is %s. Let's see if we need to order anything..." % wk)
  
  browser = Browser()
  
  browser.request('https://www.seamless.com/food-delivery/login.m')
  groupOrder = browser.request('https://www.seamless.com/food-delivery/login.m',\
                  postdata="ReturnUrl=%2Ffood-delivery%2Faddress.m&" + loginCredentials)
  
  parsedGroupOrder = BeautifulSoup.BeautifulSoup(groupOrder)
  if parsedGroupOrder.title.text.startswith("Bad Login"):
    log("Login incorrect.")
    return -1
  todaysTag = parsedGroupOrder.find('h3', text=re.compile(wk))
  if todaysTag is None:
    log("It looks like we either don't order today or it's too late to do so.\nSorry about that!")
    return -1
  todaysTag = todaysTag.parent
  
  todaysRestaurants = todaysTag.findNextSibling("ul").findChildren("a")
  desiredRestaurant = selectRestaurant(todaysRestaurants)

  if len(desiredRestaurant) == 0:
    log("Restaurant not found.")
    return -1
  if len(desiredRestaurant) > 1:
    log("Warning: multiple restaurants matched -- taking the first one!")
  desiredRestaurant = desiredRestaurant[0]['href']
  
  browser.lastUrl = "https://www.seamless.com/grouporder.m?SubVendorTypeId=1"
  restaurantPage = browser.request(desiredRestaurant)
  parsedRestaurantPage = BeautifulSoup.BeautifulSoup(restaurantPage)
  
  userIdFind = parsedRestaurantPage('input', id='tagUserId')
  if len(userIdFind) == 0:
    log("Couldn't find your user ID, giving up.")
    return -1
  userID = userIdFind[0]['value']
  
  orderIdFind = parsedRestaurantPage('input', id='InfoPopupfavorite_orderId')
  if len(orderIdFind) == 0:
    log("Couldn't find your order ID, giving up.")
    return -1
  orderID = orderIdFind[0]['value']
  
  allItems = parsedRestaurantPage('a', href=re.compile('MealsMenuSelectionPopup.m'))
  
  # sometimes items will be duplicated, e.g. because the item is
  # one of the most popular for this restaurant
  itemCandidates = {}
  productIdRE = re.compile("ProductId=([0-9]+)&")
  for item in allItems:
    match = productIdRE.search(item['href'])
    if match is None:
      continue
    itemCandidates[match.group(1)] = item
  desiredItemCandidates = selectItem(itemCandidates.values())
  
  if len(desiredItemCandidates) == 0:
    log("Item not found.")
    return -1
  
  if len(desiredItemCandidates) > 1:
    log("Warning: multiple matching items found -- taking a random one!")
  
  desiredItem = random.sample(desiredItemCandidates, 1)[0]['href']
  itemUrlRE = re.compile("MealsMenuSelectionPopup.m[^']*'")
  match = itemUrlRE.search(desiredItem)
  if match is None:
    log("We ran into trouble parsing the item URL. Giving up!")
    return -1
  itemUrl = match.group()
  
  itemPage = browser.request(itemUrl)
  parsedItemPage = BeautifulSoup.BeautifulSoup(itemPage)
  
  pdata = ("ajaxCommand=29~0&29~0action=Save&29~0orderId=%s&" % orderID) + "&".join([x for x in map(lambda x: x.has_key('name') and x.has_key('value') and "29~0%s=%s" % (x['name'], x['value']), parsedItemPage.find('form')('input')) if x])
  
  addItemResponse = browser.request("https://www.seamless.com/Ajax.m", postdata=pdata, updateURL=False)
  if addItemResponse.find("Successful") < 0:
    log("Failed to add the item; not sure why.")
    return -1
  
  # checkout
  itemPrice = float("".join(parsedItemPage.find('input', id='price')['value'].split("$")))
  
  alloc = "%.2f" % (itemPrice * 1.1)
  
  pdata="goToCheckout=NO&TotalAlloc=%s00&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=%s&EcoToGoUserId=%s&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=%s&AllocationAmt1=%s&FirstName=&LastName=&NewAllocationAmt=&totalAllocated=$%s&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=%d&creditCardZipCode=&CreditCardCVV=&OrderIdClicked=%s&FloorRoom=9&phoneNumber=%s&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals" % (alloc, orderID, userID, orderID, alloc, alloc, year, orderID, phoneNumber)
  
  if dryRun:
    log("At this point, we would place the order, but this is a dry run, so we exit.")
    return 0
  checkoutResponse = browser.request("https://www.seamless.com/Checkout.m", postdata=pdata, updateURL=False)
  parsedCheckoutResponse = BeautifulSoup.BeautifulSoup(checkoutResponse)
  
  thanksMessage = [x for x in parsedCheckoutResponse('div') if x.has_key('class') and "ThanksForOrder" in x['class']]
  if len(thanksMessage) < 1:
    log("Looks like the order failed for some reason -- probably exceeded the meal allowance.")
    return -1
  
  thanksMessage = thanksMessage[0]
  log("I think we successfully ordered lunch.")
  log("Here's the message from Seamless:")
  log(re.sub('[ \t\n\r]+', ' ', "\n".join(map(lambda x: x.text, thanksMessage('h3')))))
  return 0

rvalue = None
if __name__ == "__main__":
  def log(msg):
    print msg

  def iSelect(choices):
    for idx, choice in zip(range(len(choices)), choices):
      print idx, choice.text
    idx = -1
    while idx < 0 or idx >= len(choices):
      print "Please enter an integer between 0 and %d (inclusive)." % (len(choices)-1)
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
  loginCredentials=open("loginCredentials").readlines()[0].strip()
  rvalue = order(log,
                 loginCredentials,
                 phoneNumber,
                 niSelect(re.compile(restaurant)),
                 niSelect(re.compile(item)))
