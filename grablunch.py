#!/usr/bin/python

import favorites
import random
import seamless_browser
import sys

if __name__ == "__main__":
    def log(msg):
        print msg

    login_credentials = open("loginCredentials").readlines()[0].strip()
    sys.exit(
        seamless_browser.SeamlessBrowser(log).order(
            login_credentials,
            "(617)555-3000",
	    favorites.FavoritesSelector("favorites.txt"),
            wk="Thursday"))

#    sys.exit(
#        SeamlessBrowser(log).order(
#            login_credentials,
#            "(617)555-3000",
#            ni_select(
#                re.compile("Sugar \& Spice")),
#            ni_select(
#                re.compile("Three Friends")),
#            wk="Tuesday"))
#    sys.exit(
#        SeamlessBrowser(log).order(
#            login_credentials,
#            "(617)555-3000",
#            ni_select(
#                re.compile("Tossed")),
#            ni_select(
#                re.compile("Design Your Own Salad")),
#            nio_select(["^Romaine Hearts", "^Iceberg Lettuce", "^Corn *\(", "^Cucumbers", "^Fresh Peppers", "^Chopped Tomatoes", "Gluten-Free Balsamic Vinaigrette Dressing", "Dressing Mixed In", "Lobster Bisque"]),
#            wk="Tuesday"))
