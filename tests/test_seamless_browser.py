#!/usr/bin/python

import mock
import re
import sys
import unittest

import favorites
import seamless_browser
import selector

class MockUrlOpener:
    class MockResponse:
        def __init__(self, response):
            self.response = response
        def read(self):
            return self.response
    def __init__(self, test_case, fname):
        self.test_case = test_case
        url_map = []
        for reqresp in \
              ("".join(open(fname).readlines()))[6:].split("\nurl = "):
          rr_lines = reqresp.split("\n")
          url = rr_lines[0]
          headers = eval(rr_lines[1][10:])
          post_data = rr_lines[2][11:]
          if post_data == "None":
              post_data = None
          url_map.append([url,
                          headers,
                          post_data,
                          "\n".join(rr_lines[6:])])
        self.url_map = url_map
        self.index = 0
        self.addheaders = []
    def open(self, url, postdata):
        reqresp = self.url_map[self.index]
        self.test_case.assertEqual(url, reqresp[0])
        self.test_case.assertEqual(self.addheaders, reqresp[1])
        self.test_case.assertEqual(postdata, reqresp[2])
        self.index += 1
        return MockUrlOpener.MockResponse(reqresp[3])

class Logger:
    def __init__(self):
        self.log = []
    def __call__(self, mesg):
        self.log.append(mesg)

class TestSeamlessBrowser(unittest.TestCase):
    def test_login_incorrect(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/loginIncorrect")
        errorCode = seamless_browser_i.order(
            "username=OttoLunch&password=OttosStupidPassword",
            "",
            None,
            wk="Sunday")
        self.assertEquals(errorCode, 1)
        self.assertEquals(log.log,
            ["Selected day is Sunday. Let's see if we need to order anything...",
             'Login incorrect.'])
    def test_too_late(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/tooLateToOrder")
        errorCode = seamless_browser_i.order(
            "username=OttoLunch&password=OttosStupidPassword",
            "",
            None,
            wk="Sunday")
        self.assertEquals(errorCode, 2)
        self.assertEquals(log.log,
            ["Selected day is Sunday. Let's see if we need to order anything...",
             "It looks like we either don't order today or it's too late to do so.\nSorry about that!"])
    def test_single_item_dry_run(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/singleItemDryRun")
        regex_s = selector.RegexSelector(re.compile("Tossed"),
                                         [(re.compile("Cayenne Shrimp Salad"),
                                           re.compile("Dressing Mixed In"))])
        errorCode = seamless_browser_i.order(
            "username=OttoLunch&password=OttosStupidPassword",
            "",
            regex_s,
            wk="Thursday",
            dry_run=True)
        self.assertEquals(errorCode, 0)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             u'Successfully added Cayenne Shrimp Salad',
             'total price = 9.990000'])
    def test_no_items_selected(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/singleItemDryRun")
        regex_s = selector.RegexSelector(re.compile("Tossed"),
                                         [])
        errorCode = seamless_browser_i.order(
            "username=OttoLunch&password=OttosStupidPassword",
            "",
            regex_s,
            wk="Thursday",
            dry_run=True)
        self.assertEquals(errorCode, 3)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             'No items selected!'])
    def test_single_item_over_budget(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/singleItemOverBudget")
        interactive_s = selector.InteractiveSelector()
        with mock.patch('__builtin__.raw_input', side_effect=["0", "44", "", "1"]):
            errorCode = seamless_browser_i.order(
                "username=OttoLunch&password=OttosStupidPassword",
                "(617)555-3000",
                interactive_s,
                wk="Thursday")
        self.assertEquals(errorCode, 4)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             u'Successfully added Baked Ziti',
             'total price = 10.000000',
             'Looks like the order failed for some reason -- probably exceeded the meal allowance.',
             ''])
    def test_incorrect_sum(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/incorrectSum")
        regex_s = selector.RegexSelector(re.compile("India Palace"),
                                         [(re.compile("Lamb Rogan Josh - Lunch"),
                                           re.compile("Medium Hot")),
                                          (re.compile("Papadum"), re.compile("None"))])
        errorCode = seamless_browser_i.order(
            "username=OttoLunch&password=OttosStupidPassword",
            "(617)555-3000",
            regex_s,
            wk="Thursday")
        self.assertEquals(errorCode, 4)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             u'Successfully added Lamb Rogan Josh - Lunch',
             'total price = 7.950000',
             u'Successfully added Papadum',
             'total price = 9.900000',
             'Looks like the order failed for some reason -- probably exceeded the meal allowance.',
             u'The sum of all allocations must total the order total.  Please correct the allocation amounts and try again.'])
    def test_multiple_items_dry_run(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/multipleItemsDryRun")
        favorites_s = favorites.FavoritesSelector("tests/fixtures/favorites.txt")
        with mock.patch('random.uniform', return_value=0.2):
            errorCode = seamless_browser_i.order(
                "username=OttoLunch&password=OttosStupidPassword",
                "(617)555-3000",
                favorites_s,
                wk="Thursday",
                dry_run=True)
        self.assertEquals(errorCode, 0)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             u'Successfully added Shrimp Quesadilla',
             'total price = 6.250000',
             u'Successfully added Chips with Salsa',
             'total price = 9.740000'])
    def test_multiple_items_over_budget(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/multipleItemsOverBudget")
        favorites_s = favorites.FavoritesSelector("tests/fixtures/favorites.txt")
        with mock.patch('random.uniform', return_value=1.5):
            errorCode = seamless_browser_i.order(
                "username=OttoLunch&password=OttosStupidPassword",
                "(617)555-3000",
                favorites_s,
                wk="Thursday")
        self.assertEquals(errorCode, 4)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             u'Successfully added Chole Saag - Lunch',
             'total price = 6.950000',
             u'Successfully added Naan',
             'total price = 9.900000',
             'Looks like the order failed for some reason -- probably exceeded the meal allowance.',
             ''])
    def test_multiple_items_successful(self):
        sys.stdout = mock.Mock()
        log = Logger()
        seamless_browser_i = seamless_browser.SeamlessBrowser(log)
        seamless_browser_i.url_opener = \
            MockUrlOpener(self, "tests/fixtures/multipleItemsSuccessful")
        favorites_s = favorites.FavoritesSelector("tests/fixtures/favorites.txt")
        with mock.patch('random.uniform', return_value=2.5):
            errorCode = seamless_browser_i.order(
                "username=OttoLunch&password=OttosStupidPassword",
                "(617)555-3000",
                favorites_s,
                wk="Thursday")
        self.assertEquals(errorCode, 0)
        self.assertEquals(log.log,
            ["Selected day is Thursday. Let's see if we need to order anything...",
             u'Successfully added Lamb Rogan Josh - Lunch',
             'total price = 7.950000',
             u'Successfully added Papadum',
             'total price = 9.900000',
             'I think we successfully ordered lunch.',
             "Here's the message from Seamless:",
             u"Your order (# 1486577951) for $11.09 on 4/30/2015 has been successfully submitted as part of your company's group order. As soon as the group order closes, your order will be sent over to the kitchen at India Palace (Boston) so they can start preparing your delicious meal. In the unlikely event that you should have any food or delivery-related issues with your order, please contact India Palace (Boston) at (617) 666-9770."])

if __name__ == '__main__':
    unittest.main()
