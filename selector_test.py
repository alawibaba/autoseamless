#!/usr/bin/python

import re
import selector
import unittest

class MockChoice:
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return "MockChoice<%s>" % str(self.text)
    __repr__ = __str__

class TestRegexSelector(unittest.TestCase):
    def test_basic_restaurant_match(self):
        regex_s = selector.RegexSelector(re.compile("Tossed"),
                                         [(re.compile("Cayenne Shrimp Salad"),
                                           re.compile("Dressing Mixed In"))])
        restaurant_list = [MockChoice("Tossed (Post Office Sq.)"),
                           MockChoice("Sugar & Spice")]
        selected_restaurants = regex_s.restaurant_match(restaurant_list)
        self.assertEqual(selected_restaurants, restaurant_list[:1])
        item_list = [MockChoice("Cayenne Shrimp Salad"),
                     MockChoice("Chicken Caesar Salad")]
        selected_items = regex_s.item_match(item_list)
        self.assertEqual(map(lambda x: x[0], selected_items), item_list[:1])
        mock_options = {"D_0": {"label": "Dressing Mixed In",
                                "name": "D",
                                "value": "0"},
                        "D_1": {"label": "Dressing on the Side",
                                "name": "D",
                                "value": "1"}}
        selected_options = selected_items[0][1](mock_options)
        self.assertEqual(selected_options, {"D": "0"})

if __name__ == '__main__':
    unittest.main()
