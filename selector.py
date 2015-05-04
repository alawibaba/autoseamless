#!/usr/bin/python

class Selector:
    """Abstract class that defines the Selector interface."""
    def restaurant_match(self, restaurant_list):
        """Which restaurants do we want?
        
        Arguments:
        restaurant_list -- A list of restaurants, given as objects that have a
                           "text" field which is the name of the restaurant
                           (as a string).
        
        Return-value: A list of elements from restaurant_list.
        """
        return []
    def item_match(self, item_list):
        """Which items do we want?
        
        Arguments:
        item_list -- A list of items, given as objects that have a
                     "text" field which is the name of the item
                     (as a string).
        
        Return-value: A list of tuples of length two. The first element of
                      each tuple is an element from the item_list, and the
                      second element is a method that takes a list of
                      possible options as an argument and returns a
                      dictionary of choices. Please see the tests for sample
                      usage.
        """
        return []

class InteractiveSelector(Selector):
    """Interactive Selector: Emits the list of restaurants, menu, and options
    to the console, and uses raw_input to solicit choices from the user."""
    def i_select_basic(self, choices, labels):
        """Basic interactive selection: select one of a list of items.
 
        Keyword arguments:
        choices -- The list of objects to select from.
        labels -- The list of labels of the objects. len(labels) == len(choices)

        Return-value: One of the elements from the choices list.
        """
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
    def i_select_multi(self, choices, labels):
        """Select zero or more of a list of items.
 
        Keyword arguments:
        choices -- The list of objects to select from.
        labels -- The list of labels of the objects. len(labels) == len(choices)

        Return-value: A list of elements from the choices list (possibly many).
        """
        for idx in xrange(len(choices)):
            print idx, labels[idx]
        idx = []
        while True:
            print "Please enter a list of integers between 0 and %d (inclusive)." % (len(choices) - 1)
            idx_list = raw_input("Select> ")
            if idx_list.strip() == "":
                return []
            try:
                return map(lambda k: choices[k], map(int, idx_list.split(",")))
            except ValueError:
                pass
            except KeyError:
                pass
    def i_options(self, all_options):
        """Interactive options selector.
 
        Keyword arguments:
        all_options -- A list of options.

        Return-value: A dictionary indicating which options were chosen.
        """
        rvalue = {}
        option_groups = {}
        for opt_id in all_options.keys():
            group_id = opt_id.split("_")[0]
            try:
                option_groups[group_id][1].append(opt_id)
            except KeyError:
                option_groups[group_id] = (all_options[opt_id]['type'], [opt_id])
        option_group_keys = option_groups.keys()
        option_group_keys.sort()
        for option_group_key in option_group_keys:
            inp_type, inp_ids = option_groups[option_group_key]
            if inp_type == "hidden":
                continue
            elif inp_type == "text":
                for inp_id in inp_ids:
                    try:
                        print all_options[inp_ids[0]]['label']
                        val = raw_input("> ")
                        rvalue[inp_id] = val
                    except KeyError:
                        continue
            elif inp_type == "radio":
                print "Please select one."
                choices = [] ; labels = []
                for idx, inp_id in zip(range(len(inp_ids)), inp_ids):
                    try:
                        labels.append(all_options[inp_id]['label'])
                        choices.append(inp_id)
                    except KeyError:
                        continue
                inp_id = self.i_select_basic(choices, labels)
                rvalue[all_options[inp_id]['name']] = all_options[inp_id]['value']
            elif inp_type == "checkbox":
                print "Please select as many as you like (separate by commas)."
                if 'max_included' in all_options[inp_ids[0]] and \
                    all_options[inp_ids[0]]['max_included'] > 0:
                        print "Up to %d is included in the base price." % all_options[inp_ids[0]]['max_included']
                choices = [] ; labels = []
                for idx, inp_id in zip(range(len(inp_ids)), inp_ids):
                    try:
                        labels.append(all_options[inp_id]['label'])
                        choices.append(inp_id)
                    except KeyError:
                        continue
                selected_inp_ids = self.i_select_multi(choices, labels)
                for inp_id in selected_inp_ids:
                    rvalue[all_options[inp_id]['name']] = all_options[inp_id]['value']
        return rvalue
    def restaurant_match(self, restaurant_list):
        return [self.i_select_basic(restaurant_list, map(lambda x: x.text, restaurant_list))]
    def item_match(self, item_list):
        return [(self.i_select_basic(item_list, map(lambda x: x.text, item_list)), self.i_options)]

class RegexSelector(Selector):
    """Regex Selector: Selection of restaurants, items, and options via regular
    expression."""
    def __init__(self, restaurant_re, items_re):
        """Constructor.

        Arguments:
        restaurant_re -- regular expression for the restaurant you want.
        items_re -- A list of tuples, the first element of which is a regular
                    expression for the item, and the second of which is an
                    expression for the options."""
        self.restaurant_re = restaurant_re
        self.items_re = items_re
    def restaurant_match(self, restaurant_list):
        rvalue = []
        for choice in restaurant_list:
            if self.restaurant_re.search(choice.text):
                rvalue.append(choice)
        return rvalue
    def options_match(self, options_re):
        """Returns an options matcher.
 
        Keyword arguments:
        options_re -- A regular expression for the desired options.

        Return-value: A method which takes an options list and returns
                      a dictionary indicating which options were selected.
        """

        def curry_select(all_options):
            rvalue = {}
            for inp_id in all_options.keys():
                try:
                    if options_re.search(all_options[inp_id]["label"]):
                        rvalue[all_options[inp_id]["name"]] = all_options[inp_id]["value"]
                except KeyError:
                    pass
            return rvalue
        return curry_select
    def item_match(self, item_list):
        rvalue = []
        for choice in item_list:
            for item_re, options_re in self.items_re:
                if item_re.search(choice.text):
                    rvalue.append((choice, self.options_match(options_re)))
                    break
        return rvalue
