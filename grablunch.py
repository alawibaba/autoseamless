#!/usr/bin/python

import favorites
import random
import seamless_browser
import sys

if __name__ == "__main__":
    def log(msg):
        print msg

    loginCredentials = open("loginCredentials").readlines()[0].strip()
    sys.exit(
        seamless_browser.SeamlessBrowser(log).order(
            loginCredentials,
            "(617)555-3000",
	    favorites.FavoritesSelector("favorites.txt"),
            wk="Thursday"))

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
