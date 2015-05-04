import random
import re
import selector
import sys

MEAL_RE = re.compile(r'([^\{\},]+)(?:\{([^\}]*)\}([^\{\},]*))?(?:,|$)')

def parse_favorites(filename):
    """Parse favorites from the given filename.

    Args:
        filename: Filename to read from.
    Returns:
        Dictionary mapping from restaurant name to a list of meals.
    """
    with open(filename) as f:
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


class FavoritesSelector(selector.Selector):
    def __init__(self, fname):
        self.choice = None
        self.selections = parse_favorites(fname)

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
                print "Selected %s" % c.text ; sys.stdout.flush()
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
                        print "-- %s" % full_options_list[o]['label']
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
                    print "Selected %s" % item.text
                    rvalue.append((item, self.option_selector(options)))
                    break
        return rvalue
