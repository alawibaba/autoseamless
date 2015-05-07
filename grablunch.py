#!/usr/bin/python

import argparse
import favorites
import os
import random
import re
import seamless_browser
import selector
import sys

class EnvDefaultArgParser(argparse.ArgumentParser):
    @staticmethod
    def get_custom_formatter(env_prefix):
        class _CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
            def _get_help_string(self, action):
                help = super(_CustomHelpFormatter,
                        self)._get_help_string(action)
                if action.dest != 'help':
                    help += ' [env: %s%s]' % (env_prefix, action.dest.upper())
                return help
        return _CustomHelpFormatter

    def __init__(self,
            env_prefix="",
            formatter_class=None,
            **kwargs):
        self.env_prefix = env_prefix
        if formatter_class is None:
            formatter_class = EnvDefaultArgParser.get_custom_formatter(
                    env_prefix)
        super(EnvDefaultArgParser, self).__init__(
                formatter_class=formatter_class, **kwargs)

    def _add_action(self, action):
        action.default = os.environ.get(
                "%s%s" % (self.env_prefix, action.dest.upper()),
                action.default)
        return super(EnvDefaultArgParser, self)._add_action(action)

if __name__ == "__main__":
    def log(msg):
        print msg

    parser = EnvDefaultArgParser(env_prefix="SEAMLESS_")
    parser.add_argument('--dry_run',
            help='Do a dry run (don\'t actually order).',
            const=True,
            default=False,
            action='store_const')
    parser.add_argument('--credentials',
            help='Location of credentials file (default: loginCredentials).',
            default="loginCredentials",
            type=str)
    parser.add_argument('--phone_number',
            help='The phone number to provide to seamless.',
            default=seamless_browser.DEFAULT_PHONE)
    parser.add_argument('--day',
            help='Which day to order for (default: today).',
            default=None,
            type=str)
    parser.add_argument('--favorites',
            help='Location of favorites file.',
            default="favorites.txt",
            type=str)
    parser.add_argument('--interactive',
            help='Interactive mode (default: False).',
            const=True,
            default=False,
            action='store_const')
    parser.add_argument('--restaurant',
            help='Restaurant (regex).',
            default=None,
            type=str)
    parser.add_argument('--items',
            help='Item to order (regex).',
            default=None,
            type=str)
    parser.add_argument('--options',
            help='Item options (regex).',
            default=None,
            type=str)
    args = parser.parse_args()

    if args.restaurant and args.items and args.options:
        selector = selector.RegexSelector(
                re.compile(args.restaurant),
                [(re.compile(args.items),
                    re.compile(args.options))])
    elif args.interactive:
        selector = selector.InteractiveSelector()
    else:
        selector = favorites.FavoritesSelector(args.favorites)

    login_credentials = open(args.credentials).readlines()[0].strip()
    try:
      sys.exit(
          seamless_browser.SeamlessBrowser(log).order(
              login_credentials,
              args.phone_number,
              selector,
              wk=args.day,
              dry_run=args.dry_run))
    except KeyboardInterrupt:
        print "\n\nAbort."
