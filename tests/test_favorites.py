#!/usr/bin/python

import mock
import re
import unittest

import favorites

class MockChoice:
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return "MockChoice<%s>" % str(self.text)
    __repr__ = __str__

class TestRegexSelector(unittest.TestCase):
    def test_basic_match(self):
        favorites_s = favorites.FavoritesSelector("tests/fixtures/favorites.txt")
        restaurant_list = [MockChoice("Viva Burrito"),
                           MockChoice("Sugar & Spice")]
        selected_restaurants = favorites_s.restaurant_match(restaurant_list)
        self.assertEqual(selected_restaurants, restaurant_list[:1])
        item_list = [MockChoice("Shrimp Quesadilla"),
                     MockChoice("Chips"),
                     MockChoice("Chips with Salsa"),
                     MockChoice("Chips with Salsa (Ugly ones)")]
        selected_items = favorites_s.item_match(item_list)
        self.assertEqual(map(lambda x: x[0], selected_items), [item_list[0], item_list[2]])
        self.assertEquals(selected_items[0][1], None)
        self.assertEquals(selected_items[1][1], None)

    def test_random_selection(self):
        favorites_s = favorites.FavoritesSelector("tests/fixtures/favorites.txt")
        restaurant_list = [MockChoice("Viva Burrito"),
                           MockChoice("India Palace")]
        with mock.patch('random.uniform', return_value=0.2):
            selected_restaurants = favorites_s.restaurant_match(restaurant_list)
            self.assertEqual(selected_restaurants, restaurant_list[:1])
        with mock.patch('random.uniform', return_value=1.5):
            selected_restaurants = favorites_s.restaurant_match(restaurant_list)
            self.assertEqual(selected_restaurants, restaurant_list[1:])
        with mock.patch('random.uniform', return_value=2.5):
            selected_restaurants = favorites_s.restaurant_match(restaurant_list)
            self.assertEqual(selected_restaurants, restaurant_list[1:])

    def test_options_selection(self):
        favorites_s = favorites.FavoritesSelector("tests/fixtures/favorites.txt")
        restaurant_list = [MockChoice("Jimbo's Soylent Emporium"),
                           MockChoice("India Palace")]
        with mock.patch('random.uniform', return_value=2.5):
            selected_restaurants = favorites_s.restaurant_match(restaurant_list)
            self.assertEqual(selected_restaurants, restaurant_list[1:])
        item_list = [MockChoice("Lamb Rogan Josh - Lunch"),
                     MockChoice("Papadum"),
                     MockChoice("Catheter Chili")]
        selected_items = favorites_s.item_match(item_list)
        self.assertEqual(map(lambda x: x[0], selected_items), [item_list[0], item_list[1]])
        mock_options = {"D_0": {"label": "Mild",
                                "name": "D",
                                "value": "0"},
                        "D_1": {"label": "Medium Hot",
                                "name": "D",
                                "value": "1"},
                        "D_2": {"label": "Medium Hot is what we say, but this actually will melt your face",
                                "name": "D",
                                "value": "2"},
                        "D_3": {"label": "Lava",
                                "name": "D",
                                "value": "3"}}
        selected_options = selected_items[0][1](mock_options)
        self.assertEqual(selected_options, {"D": "1"})
        self.assertEquals(selected_items[1][1], None)

if __name__ == '__main__':
    unittest.main()
