#!/usr/bin/env python

# Given a url, performs GET requests until it gets back an HTTP 200
# or exceeds the wait timeout.

import argparse
import socket
import urllib.error
import urllib.request
import sys
import time


def main(args):
    parser = argparse.ArgumentParser(
        description=(
            "Performs GET requests against given URL until HTTP 200 or exceeds "
            "wait timeout."
        )
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--timeout", type=int, default=10, help="Wait timeout")
    parser.add_argument("--codes", default="200", help="Comma-separated list of valid HTTP response codes")
    parser.add_argument("url", help="URL to test")

    parsed = parser.parse_args(args)

    ok_codes = [int(code.strip()) for code in parsed.codes.split(",")]

    if parsed.verbose:
        print("Testing %s for %s with timeout %d..." % (parsed.url, repr(ok_codes), parsed.timeout))

    socket.setdefaulttimeout(1)

    start_time = time.time()

    last_fail = ""
    while True:
        try:
            with urllib.request.urlopen(parsed.url) as resp:
                if resp.code in ok_codes:
                    sys.exit(0)
                last_fail = "HTTP status code: %s" % resp.code
        except urllib.error.URLError as error:
            if error.code in ok_codes:
                sys.exit(0)
            last_fail = "URLError: %s" % error

        if parsed.verbose:
            print(last_fail)

        time.sleep(1)

        if time.time() - start_time > parsed.timeout:
            print("Failed. %s" % last_fail)
            sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
