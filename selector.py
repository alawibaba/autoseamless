#!/usr/bin/python

class Selector:
    def restaurantMatch(self, restaurantList):
        return []
    def itemMatch(self, itemList):
        return []

class InteractiveSelector(Selector):
    def iSelectBasic(self, choices, labels):
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
    def iSelectMulti(self, choices, labels):
        for idx in xrange(len(choices)):
            print idx, labels[idx]
        idx = []
        while True:
            print "Please enter a list of integers between 0 and %d (inclusive)." % (len(choices) - 1)
            idxList = raw_input("Select> ")
            if idxList.strip() == "":
                return []
            try:
                return map(lambda k: choices[k], map(int, idxList.split(",")))
            except ValueError:
                pass
            except KeyError:
                pass
    def iOptions(self, allOptions):
        rvalue = {}
        optionGroups = {}
        for optId in allOptions.keys():
            groupId = optId.split("_")[0]
            try:
                optionGroups[groupId][1].append(optId)
            except KeyError:
                optionGroups[groupId] = (allOptions[optId]['type'], [optId])
        optionGroupKeys = optionGroups.keys()
        optionGroupKeys.sort()
        for optionGroupKey in optionGroupKeys:
            inpType, inpIds = optionGroups[optionGroupKey]
            if inpType == "hidden":
                continue
            elif inpType == "text":
                for inpId in inpIds:
                    try:
                        print allOptions[inpIds[0]]['label']
                        val = raw_input("> ")
                        rvalue[inpId] = val
                    except KeyError:
                        continue
            elif inpType == "radio":
                print "Please select one."
                choices = [] ; labels = []
                for idx, inpId in zip(range(len(inpIds)), inpIds):
                    try:
                        labels.append(allOptions[inpId]['label'])
                        choices.append(inpId)
                    except KeyError:
                        continue
                inpId = iSelectBasic(choices, labels)
                rvalue[allOptions[inpId]['name']] = allOptions[inpId]['value']
            elif inpType == "checkbox":
                print "Please select as many as you like (separate by commas)."
                choices = [] ; labels = []
                for idx, inpId in zip(range(len(inpIds)), inpIds):
                    try:
                        labels.append(allOptions[inpId]['label'])
                        choices.append(inpId)
                    except KeyError:
                        continue
                selectedInpIds = iSelectMulti(choices, labels)
                for inpId in selectedInpIds:
                    rvalue[allOptions[inpId]['name']] = allOptions[inpId]['value']
        return rvalue
    def restaurantMatch(self, restaurantList):
        return [self.iSelectBasic(choices, map(lambda x: x.text, choices))]
    def itemMatch(self, itemList):
        return [(self.iSelectBasic(choices, map(lambda x: x.text, choices)), self.iOptions)]

class RegexSelector(Selector):
    def __init__(self, restaurantRE, itemsRE):
        self.restaurantRE = restaurantRE
        self.itemsRE = itemsRE
    def restaurantMatch(self, restaurantList):
        rvalue = []
        for choice in restaurantList:
            if self.restaurantRE.search(choice.text):
                rvalue.append(choice)
        return rvalue
    def optionsMatch(optionsRE):
        def currySelect(allOptions):
            rvalue = {}
            for inpID in allOptions.keys():
                try:
                    if optionsRE.search(allOptions[inpID]["label"]):
                        rvalue[allOptions[inpID]["name"]] = allOptions[inpID]["value"]
                except KeyError:
                    pass
            return rvalue
        return currySelect
    def itemMatch(self, itemList):
        rvalue = []
        for choice in itemList:
            for itemRE, optionsRE in self.itemsRE:
                if self.itemRE.search(choice.text):
                    rvalue.append((choice, self.optionsMatch(optionsRE)))
                    break
        return rvalue
