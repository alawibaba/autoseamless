#!/bin/bash

restaurant="Tossed (Post Office Sq)"
item="Cayenne Shrimp Salad"

loginCredentials=`cat loginCredentials`

BASEURL="https://www.seamless.com/"
#
wk=`date +"%A"`
year=`date +"%Y"`
#
echo "Today is $wk. Let's see if we need to order anything..."

ua='User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'
wgetcmd=$'wget -U "$ua" --save-cookies cookies --load-cookies cookies --keep-session-cookies'

rm -rf cookies tmpfiles
mkdir tmpfiles
touch cookies
$wgetcmd -O/dev/null -q 'https://www.seamless.com/food-delivery/login.m'
$wgetcmd -Otmpfiles/grouporder -q --post-data="ReturnUrl=%2Ffood-delivery%2Faddress.m&$loginCredentials" 'https://www.seamless.com/food-delivery/login.m'
#
resturl=`cat tmpfiles/grouporder | awk "/<h3>/ { dop = 0 } ; /END: main column/ { dop = 0 } ; /<h3>$wk/ { dop = 1 } ; dop" | grep "$restaurant" | sed -e 's/^.*href="//' -e 's/".*$//'`
if [ -z "$resturl" ] ; then 
  echo "It looks like we either don't order today or it's too late to do so. Sorry about that!"
  exit 0
fi
resturl="$BASEURL$resturl"
echo "Fetching $resturl"
$wgetcmd --referer="https://www.seamless.com/grouporder.m?SubVendorTypeId=1" -q -Otmpfiles/menu "$resturl"

itemurl="$BASEURL"`cat tmpfiles/menu | grep "$item" | sed -e "s/^.*\(MealsMenuSelectionPopup.m[^']*\)'.*$/\1/" | head -n 1`

$wgetcmd -q -Otmpfiles/item "$itemurl"

orderID=`cat tmpfiles/menu | sed -ne 's/^.*Order Number:[^0-9]*\([0-9]*\)<\/td>.*$/\1/p'`
userID=`cat tmpfiles/menu | sed -ne 's/^.*<input type="hidden" id="tagUserId" name="tagUserId" value="\([0-9]*\)".*$/\1/p'`
echo $userID "" $orderID

pdata="ajaxCommand=29~0&29~0action=Save&29~0orderId=$orderID&"`cat tmpfiles/item | awk '/<form/ { ps = 1 } ; ps ; /<\/form/ { ps = 0 }' | grep "<input" | sed -ne 's/^.* name="\([^"]*\)".* value="\([^"]*\)".*$/29~0\1=\2/p' | tr '\n' '&' | sed -e 's/&$//' -e 's/\$//g'`
$wgetcmd -q -Otmpfiles/ajaxout --post-data="$pdata" --referer="$itemurl" "https://www.seamless.com/Ajax.m"

pdata="goToCheckout=NO&TotalAlloc=10.9900&LineId=&saveFavoriteCommand=Checkout.m&WhichPage=Meals&favoriteNameOriginal=&firstCheckOut=Y&acceptedBudgetWarning=N&AcceptedWarnings=N&acceptedFavoriteWarning=N&FavoriteSaved=N&UserSearchType=&ShowAddUser=N&deliveryType=Delivery&EcoToGoOrderId=$orderID&EcoToGoUserId=$userID&OverageAllocationAmt=0&InfoPopupfavorite_name=&InfoPopupfavorite_saveType=&InfoPopupfavorite_orderId=$orderID&AllocationAmt1=10.99&FirstName=&LastName=&NewAllocationAmt=&totalAllocated=$10.99&AllocationComment=&typeOfCreditCard=&creditCardNumber=&CCExpireMonth=1&CCExpireYear=$year&creditCardZipCode=&CreditCardCVV=&OrderIdClicked=$orderID&FloorRoom=9&phoneNumber=(857)600-6533&DeliveryComment=&EcoToGoOrder=Y&InfoPopup_name=Namethisfavorite&favoriteSaveMode=successWithOrderingMeals"
$wgetcmd -q -Otmpfiles/ajaxout --post-data="$pdata" --referer="$itemurl" "https://www.seamless.com/Checkout.m"

if [ `cat tmpfiles/ajaxout | grep "exceeded the meal allowance designated by your firm." | wc -l` -ge 1 ] ; then
  echo "You have exceeded the meal allowance; I hope you already ordered lunch because this failed."
else
  echo "I think we successfully ordered lunch."
fi

cat tmpfiles/ajaxout | awk '/<p/ { pr = 0 } ; pr ; /ThanksForOrder/ { pr = 1 }'
