import random
import re
import selector
import sys

MEAL_RE = re.compile(r'([^\{\},]+)(?:\{([^\}]*)\}([^\{\},]*))?(?:,|$)')

def parse_favorites(f):
    """Parse favorites from the given object.

    Args:
        f: An object that supports line iteration (like an open file).
    Returns:
        Dictionary mapping from restaurant name to a list of meals.
    """
    current_restaurant = None
    result = {}
    for raw_line in f:
        line = raw_line.strip()
        if line == "":
            continue
        elif line.startswith("#"):
            continue
        elif line.startswith("[") and line.endswith("]"):
            current_restaurant = line[1:-1].strip()
            result[current_restaurant] = []
            continue
        # this line is a meal
        match = MEAL_RE.findall(line)
        if match is None:
            raise ValueError("bad line %s" % line)
        result[current_restaurant].append(
            [((mpre + mpost).strip(),
                    [opt.strip() for opt in opts.split(",") if opt.strip() != ''])
                    for mpre, opts, mpost in match])
    return result

def print_funct(x):
    print x

class FavoritesSelector(selector.Selector):
    """Selector that selects restaurant, items, and options from a favorites
    file, the format of which is compact, elegant, profound, sublime."""
    def __init__(self, f, log=None):
        """Constructor.

        Arguments:
        f -- An object that supports iteration over its lines (such as an open file).
        """
        self.choice = None
        self.selections = parse_favorites(f)
        if log:
            self.log = log
        else:
            self.log = print_funct

    def restaurant_match(self, restaurants):
        restaurant_choices = [] ; num_options = 0
        for x in self.selections.keys():
            for choice in restaurants:
                if choice.text.find(x) >= 0:
                    restaurant_choices.append((choice, self.selections[x]))
                    num_options += len(self.selections[x])
                    break
        idx = int(random.uniform(0, num_options))
        if idx == num_options: idx -= 1
        for c, l in restaurant_choices:
            if idx < len(l):
                self.choice = l[idx]
                self.log("Selected %s" % c.text)
                return [c]
            idx -= len(l)

    def option_selector(self, options):
        if len(options) == 0:
            return None
        def rvalue(full_options_list):
            opt_dict = {}
            order = [x for x in full_options_list.keys() if 'label' in full_options_list[x]]
            order.sort(lambda x,y: len(full_options_list[x]['label']) - len(full_options_list[y]['label']))
            for opt in options:
                for o in order:
                    if full_options_list[o]['label'].find(opt) >= 0:
                        self.log("-- %s" % full_options_list[o]['label'])
                        opt_dict[full_options_list[o]['name']] = full_options_list[o]['value']
                        break
            return opt_dict
        return rvalue

    def item_match(self, items):
        rvalue = []
        sorted_items = items[:]
        sorted_items.sort(lambda x, y: len(x.text)-len(y.text))
        for item_name, options in self.choice:
            for item in sorted_items:
                if item.text.find(item_name) >= 0:
                    self.log("Selected %s" % item.text)
                    rvalue.append((item, self.option_selector(options)))
                    break
        return rvalue
