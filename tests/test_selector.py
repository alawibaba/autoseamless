#!/usr/bin/python

import mock
import re
import unittest

import selector

class MockChoice:
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return "MockChoice<%s>" % str(self.text)
    __repr__ = __str__

class TestInteractiveSelector(unittest.TestCase):
    def test_basic(self):
        interactive = selector.InteractiveSelector()
        restaurant_list = [MockChoice("Soups R Us"),
                           MockChoice("Tossed (Post Office Sq.)"),
                           MockChoice("Cahoots"),
                           MockChoice("Sugar & Spice"),
                           MockChoice("Eat At Jumbos")]
        with mock.patch('__builtin__.raw_input', return_value="1"), \
             mock.patch('__builtin__.print', return_value=None):
            self.assertEqual(interactive.restaurant_match(restaurant_list),
                                                          [restaurant_list[1]])
        item_list = [MockChoice("Design Your Own Salad"),
                     MockChoice("Cayenne Shrimp Salad"),
                     MockChoice("Chicken Caesar Salad"),
                     MockChoice("Giblets"),
                     MockChoice("Lobster Bisque")]
        with mock.patch('__builtin__.raw_input', return_value="0"), \
             mock.patch('__builtin__.print', return_value=None):
            selected_items = interactive.item_match(item_list)
            self.assertEqual([item for item, option in selected_items],
                             [item_list[0]])
        mock_options = {"D_0": {"label": "Dressing Mixed In",
                                "name": "D",
                                "value": "0",
                                "type": "radio"},
                        "D_1": {"label": "Dressing on the Side",
                                "name": "D",
                                "value": "1",
                                "type": "radio"},
                        "L_0_0": {"label": "Romaine Lettuce",
                                  "name": "L_0",
                                  "value": "0",
                                  "type": "checkbox"},
                        "L_1_1": {"label": "Artichoke Hearts",
                                  "name": "L_1",
                                  "value": "1",
                                  "type": "checkbox"},
                        "L_2_2": {"label": "Lowercase lettuce",
                                  "name": "L_2",
                                  "value": "2",
                                  "type": "checkbox"},
                        "L_3_3": {"label": "Iceberg Lettuce",
                                  "name": "L_3",
                                  "value": "3",
                                  "type": "checkbox"}}
        with mock.patch('__builtin__.raw_input', side_effect=["0", "0, 3"]), \
             mock.patch('__builtin__.print', return_value=None):
            selected_options = selected_items[0][1](mock_options)
            self.assertEqual(selected_options,
                             {"D": "0", "L_0": "0", "L_3": "3"})


class TestRegexSelector(unittest.TestCase):
    def test_basic_match(self):
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
    def test_multiple_match(self):
        regex_s = selector.RegexSelector(re.compile("Tossed|Sugar"),
                                         [(re.compile("Salad"),
                                           re.compile("Mixed In|Lettuce"))])
        restaurant_list = [MockChoice("Soups R Us"),
                           MockChoice("Tossed (Post Office Sq.)"),
                           MockChoice("Cahoots"),
                           MockChoice("Sugar & Spice"),
                           MockChoice("Eat At Jumbos")]
        selected_restaurants = regex_s.restaurant_match(restaurant_list)
        self.assertEqual(selected_restaurants, [restaurant_list[1],
                                                restaurant_list[3]])
        item_list = [MockChoice("Design Your Own Salad"),
                     MockChoice("Cayenne Shrimp Salad"),
                     MockChoice("Chicken Caesar Salad"),
                     MockChoice("Giblets"),
                     MockChoice("Lobster Bisque")]
        selected_items = regex_s.item_match(item_list)
        self.assertEqual(map(lambda x: x[0], selected_items), item_list[:3])
        mock_options = {"D_0": {"label": "Dressing Mixed In",
                                "name": "D",
                                "value": "0"},
                        "D_1": {"label": "Dressing on the Side",
                                "name": "D",
                                "value": "1"},
                        "L_0_0": {"label": "Romaine Lettuce",
                                  "name": "L_0",
                                  "value": "0"},
                        "L_1_1": {"label": "Artichoke Hearts",
                                  "name": "L_1",
                                  "value": "1"},
                        "L_2_2": {"label": "Lowercase lettuce",
                                  "name": "L_2",
                                  "value": "2"},
                        "L_3_3": {"label": "Iceberg Lettuce",
                                  "name": "L_3",
                                  "value": "3"}}
        selected_options = selected_items[0][1](mock_options)
        self.assertEqual(selected_options, {"D": "0", "L_0": "0", "L_3": "3"})

if __name__ == '__main__':
    unittest.main()
