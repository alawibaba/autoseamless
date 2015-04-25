import random
import re
import selector

class FavoritesSelector(selector.Selector):
    def __init__(self, fname):
        self.choice = None
        self.selections = {}
        current_restaurant = None
        for raw_line in open(fname):
            line = raw_line.strip()
            if line == "":
                continue
            elif line[0] == "#":
                continue
            elif line[0] == "[":
                current_restaurant = line.strip()[1:-1]
                self.selections[current_restaurant] = []
                continue
            # this line is a meal
            match = re.compile('([^\{\},]+)(?:\{([^\}]*)\}([^\{\},]*))?(?:,|$)').findall(line)
            if match is None:
                raise ValueError("bad line %s" % line)
            self.selections[current_restaurant].append(
                [((mpre + mpost).strip(),
                  [opt.strip() for opt in opts.split(",") if opt.strip() != ''])
                 for mpre, opts, mpost in match])
    
    def restaurantMatch(restaurants):
        restaurant_choices = [] ; num_options = 0
        for x in favorites.keys():
            for choice in restaurants:
                if choice.text.find(x) >= 0:
                    restaurant_choices.append((choice, favorites[x]))
                    num_options += len(favorites[x])
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

    def itemMatch(self, items):
        rvalue = []
        items.sort(lambda x, y: len(x.text)-len(y.text))
        for item_name, options in restaurant_selector.choice:
            for x in items:
                if x.text.find(item_name) >= 0:
                    print "Selected %s" % x.text
                    rvalue.append((x, self.option_selector(options)))
                    break
        return rvalue
