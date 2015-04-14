#!/usr/bin/python

import BeautifulSoup
import cookielib
import datetime
import re
import random
import sys
import urllib2
import urlparse

#restaurant="Tossed \(Post Office Sq\)"
#item="Cayenne Shrimp Salad"
restaurant = "Cafe 472"
item = "Grilled Chicken Sandwich"
phoneNumber = "(857)600-6533"

loginCredentials=open("loginCredentials").readlines()[0].strip()

BASEURL="https://www.seamless.com/"
#
wk=datetime.datetime.now().strftime("%A")
year=datetime.datetime.now().year
#
print "Today is %s. Let's see if we need to order anything..." % wk

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

browser = Browser()

browser.request('https://www.seamless.com/food-delivery/login.m')
groupOrder = browser.request('https://www.seamless.com/food-delivery/login.m',\
                postdata="ReturnUrl=%2Ffood-delivery%2Faddress.m&" + loginCredentials)

parsedGroupOrder = BeautifulSoup.BeautifulSoup(groupOrder)
todaysTag = parsedGroupOrder.find('h3', text=re.compile(wk))
if todaysTag is None:
  print "It looks like we either don't order today or it's too late to do so. Sorry about that!"
  sys.exit(0)
todaysTag = todaysTag.parent

todaysRestaurants = todaysTag.findNextSibling("ul").findChildren("a")

# TODO insert hook here :)
desiredRestaurant = todaysTag.findNextSibling("ul").findChildren("a", text=re.compile(restaurant))

if len(desiredRestaurant) == 0:
  print "Restaurant not found."
  sys.exit(0)
if len(desiredRestaurant) > 1:
  print "Warning: multiple restaurants matched -- taking the first one!"
desiredRestaurant = desiredRestaurant[0].parent['href']

browser.lastUrl = "https://www.seamless.com/grouporder.m?SubVendorTypeId=1"
restaurantPage = browser.request(desiredRestaurant)
parsedRestaurantPage = BeautifulSoup.BeautifulSoup(restaurantPage)

userIdFind = parsedRestaurantPage('input', id='tagUserId')
if len(userIdFind) == 0:
  print "Couldn't find your user ID, giving up."
  sys.exit(0)
userID = userIdFind[0]['value']

orderIdFind = parsedRestaurantPage('input', id='InfoPopupfavorite_orderId')
if len(orderIdFind) == 0:
  print "Couldn't find your order ID, giving up."
  sys.exit(0)
orderID = orderIdFind[0]['value']

allItems = parsedRestaurantPage('a', href=re.compile('MealsMenuSelectionPopup.m'))

# TODO insert hook here :)
desiredItems = parsedRestaurantPage('a', href=re.compile('MealsMenuSelectionPopup.m'), text=re.compile(item))

# sometimes items will be duplicated, e.g. because the item is
# one of the most popular for this restaurant
desiredItemCandidates = {}
productIdRE = re.compile("ProductId=([0-9]+)&")
for item in desiredItems:
  match = productIdRE.search(item.parent['href'])
  if match is None:
    continue
  desiredItemCandidates[match.group(1)] = item

if len(desiredItemCandidates.keys()) == 0:
  print "Item not found."
  sys.exit(0)

if len(desiredItemCandidates.keys()) > 1:
  print "Warning: multiple matching items found -- taking a random one!"

desiredItem = random.sample(desiredItemCandidates.values(), 1)[0].parent['href']
itemUrlRE = re.compile("MealsMenuSelectionPopup.m[^']*'")
match = itemUrlRE.search(desiredItem)
if match is None:
  print "We ran into trouble parsing the item URL. Giving up!"
  sys.exit(0)
itemUrl = match.group()

itemPage = browser.request(itemUrl)
parsedItemPage = BeautifulSoup.BeautifulSoup(itemPage)

pdata = ("ajaxCommand=29~0&29~0action=Save&29~0orderId=%s&" % orderID) + "&".join([x for x in map(lambda x: x.has_key('name') and x.has_key('value') and "29~0%s=%s" % (x['name'], x['value']), parsedItemPage.find('form')('input')) if x])

addItemResponse = browser.request("https://www.seamless.com/Ajax.m", postdata=pdata, updateURL=False)
if addItemResponse.find("Successful") < 0:
  print "Failed to add the item; not sure why."
  sys.exit(0)

# checkout

itemPrice = float("".join(parsedItemPage.find('input', id='price')['value'].split("$")))

alloc = "%.2f" % (itemPrice * 1.1)

pdata="goToCheckout=NO&TotalAlloc=%s00&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=%s&EcoToGoUserId=%s&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=%s&AllocationAmt1=%s&FirstName=&LastName=&NewAllocationAmt=&totalAllocated=$%s&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=%d&creditCardZipCode=&CreditCardCVV=&OrderIdClicked=%s&FloorRoom=9&phoneNumber=%s&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals" % (alloc, orderID, userID, orderID, alloc, alloc, year, orderID, phoneNumber)

checkoutResponse = browser.request("https://www.seamless.com/Checkout.m", postdata=pdata, updateURL=False)
parsedCheckoutResponse = BeautifulSoup.BeautifulSoup(checkoutResponse)

thanksMessage = [x for x in parsedCheckoutResponse('div') if x.has_key('class') and "ThanksForOrder" in x['class']]
if len(thanksMessage) < 1:
  print "Looks like the order failed for some reason -- probably exceeded the meal allowance."
  sys.exit(0)

thanksMessage = thanksMessage[0]
print "I think we successfully ordered lunch."
print "Here's the message from Seamless:"
print re.sub('[ \t\n\r]+', ' ', "\n".join(map(lambda x: x.text, thanksMessage('h3'))))

#if [ `cat tmpfiles/ajaxout | grep "exceeded the meal allowance designated by your firm." | wc -l` -ge 1 ] ; then
