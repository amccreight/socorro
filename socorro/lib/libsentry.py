# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from urllib.parse import parse_qsl, urlencode
import sys

import markus
import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger


SENTRY_MODULE_NAME = __name__
metrics = markus.get_metrics(SENTRY_MODULE_NAME)
logger = logging.getLogger(SENTRY_MODULE_NAME)


MASK_TEXT = "[Scrubbed]"


ALL_COOKIE_KEYS = object()
ALL_QUERY_STRING_KEYS = object()


def scrub(value):
    """Scrub a value"""
    return MASK_TEXT


def build_scrub_cookies(params):
    """Scrub specified keys in HTTP request cookies

    Sentry says the cookies can be:

    * an unparsed string
    * a dictionary
    * a list of tuples

    For the unparsed string, this parses it and figures things out.

    For dictionary and list of tuples, this returns the scrubbed forms of those.

    If the specified params is ALL_COOKIE_KEYS, then this will filter all cookie values.

    """

    def _scrub_cookies(value):
        to_scrub = params

        if not value:
            return value

        if isinstance(value, dict):
            if to_scrub is ALL_COOKIE_KEYS:
                value = {key: MASK_TEXT for key in value.keys()}
                return value

            for param in to_scrub:
                if param in value:
                    value[param] = MASK_TEXT
            return value

        if isinstance(value, list):
            if to_scrub is ALL_COOKIE_KEYS:
                value = [(pair[0], MASK_TEXT) for pair in value]
                return value

            for i, pair in enumerate(value):
                if pair[0] in to_scrub:
                    value[i] = (pair[0], MASK_TEXT)
            return value

        has_scrubbed_item = False
        scrubbed_pairs = []
        for cookie in value.split(";"):
            name, val = cookie.split("=", 1)
            name = name.strip()
            val = val.strip()

            if to_scrub is ALL_COOKIE_KEYS or name in to_scrub:
                if val:
                    val = MASK_TEXT
                    has_scrubbed_item = True
            scrubbed_pairs.append((name, val))

        if not has_scrubbed_item:
            return value

        return "; ".join(["=".join(pair) for pair in scrubbed_pairs])

    return _scrub_cookies


def build_scrub_query_string(params):
    """Scrub specified keys in an HTTP request query_string

    Sentry says the query_string can be:

    * an unparsed string
    * a dictionary
    * a list of tuples

    For the unparsed string, this parses it and figures things out. If there's nothing
    that needs to be scrubbed, then it returns the original string. Otherwise it
    returns a query_string value with the items scrubbed, and reformed into a
    query_string. This sometimes means that other things in the string have changed and
    that may make debugging issues a little harder.

    For dictionary and list of tuples, this returns the scrubbed forms of those.

    If the params is ALL_QUERY_STRING_KEYS, then this will drop the query_string
    altogether.

    .. Note::

       The Sentry docs say that the query_string could be part of the url. This doesn't
       handle that situation.

    """

    def _scrub_query_string(value):
        to_scrub = params
        if not value:
            return value

        if isinstance(value, dict):
            if to_scrub is ALL_QUERY_STRING_KEYS:
                value = {key: MASK_TEXT for key in value.keys()}
                return value

            for param in to_scrub:
                if param in value:
                    value[param] = MASK_TEXT
            return value

        if isinstance(value, list):
            if to_scrub is ALL_QUERY_STRING_KEYS:
                value = [(pair[0], MASK_TEXT) for pair in value]
                return value

            for i, pair in enumerate(value):
                if pair[0] in to_scrub:
                    value[i] = (pair[0], MASK_TEXT)
            return value

        has_scrubbed_item = False
        scrubbed_pairs = []
        for name, val in parse_qsl(value, keep_blank_values=True):
            if to_scrub is ALL_QUERY_STRING_KEYS or name in to_scrub:
                if val:
                    val = MASK_TEXT
                    has_scrubbed_item = True
            scrubbed_pairs.append((name, val))

        if not has_scrubbed_item:
            return value

        return urlencode(scrubbed_pairs)

    return _scrub_query_string


SCRUB_KEYS_DEFAULT = [
    # Hide stacktrace variables
    ("exception.values.[].stacktrace.frames.[].vars.username", scrub),
    ("exception.values.[].stacktrace.frames.[].vars.password", scrub),
]


def get_target_dicts(event, key_path):
    """Given a key_path, yields the dicts that hold given key.

    Uses a dotted path of key names. To traverse arrays, use `[]`.

    Examples::

        request.query_string
        exception.stacktrace.frames.[].vars.code_id

    """
    if not key_path:
        return

    parent = event
    for i, part in enumerate(key_path[:-1]):
        if part == "[]" and isinstance(parent, (tuple, list)):
            for item in parent:
                yield from get_target_dicts(item, key_path[i + 1 :])
            return

        elif part in parent:
            parent = parent[part]

    if isinstance(parent, dict) and key_path[-1] in parent:
        yield parent


class Scrubber:
    """Scrubber pipeline for Sentry events

    https://docs.sentry.io/platforms/python/configuration/filtering/

    """

    def __init__(self, scrub_keys=SCRUB_KEYS_DEFAULT):
        """
        :arg scrub_keys: list of ``(key_path, scrub function)`` tuples

            A key_path is a Python dotted path of keys with ``[]`` to denote arrays
            to traverse.

            Example of scrub keys::

                ("request.data.csrfmiddlewaretoken", scrub()),

                ("exception.stacktrace.frames.[].vars.code_id", scrub()),

            A scrub function takes a value and returns a scrubbed value. For
            example::

                def hide_letter_a(value):
                    return "".join([letter if letter != "a" else "*" for letter in value])

        """
        self.scrub_keys = [
            (key_path.split("."), scrub_function)
            for key_path, scrub_function in scrub_keys
        ]

    def __call__(self, event, hint):
        """Implements before_send function interface and scrubs Sentry event

        This tries really hard to be very defensive such that even if there are bugs in
        the scrubs, it still emits something to Sentry.

        It will log errors, so we should look for those log statements. They'll all have
        "LIBSENTRYERROR" in the message making them easy to find regardless of the
        logger name.

        Further, they emit two incr metrics:

        * hide_fun_error
        * get_target_dicts_error

        Put those in a dashboard with alerts so you know when to look in the logs.

        """

        for key_path, hide_fun in self.scrub_keys:
            key_to_scrub = key_path[-1]
            try:
                for parent in get_target_dicts(event, key_path):
                    val = parent[key_to_scrub]

                    try:
                        filtered_val = hide_fun(val)
                    except Exception:
                        logger.exception(f"LIBSENTRYERROR: Error in {hide_fun}")
                        metrics.incr("hide_fun_error")
                        filtered_val = "ERROR WHEN SCRUBBING"

                    parent[key_to_scrub] = filtered_val
            except Exception:
                logger.exception("LIBSENTRYERROR: Error in get_target_dicts")
                metrics.incr("get_target_dicts_error")

        return event


def set_up_sentry(release, host_id, sentry_dsn, **kwargs):
    """Set up Sentry

    :arg release: the release name to tag events with
    :arg host_id: some str representing the host this service is running on
    :arg sentry_dsn: the Sentry DSN
    :arg kwargs: any additional arguments to pass to sentry_sdk.init()

    """

    if not sentry_dsn:
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        release=release,
        send_default_pii=False,
        server_name=host_id,
        **kwargs,
    )

    # Ignore logging from this module
    ignore_logger(SENTRY_MODULE_NAME)


def is_enabled():
    """Return True if sentry was initialized with a DSN"""
    return (
        sentry_sdk.Hub.current.client
        and sentry_sdk.Hub.current.client.options["dsn"] is not None
    )


def get_hub():
    """Get the initialized Sentry hub.

    With a previous SDK (raven), this was called get_client, and initialized
    the it with a DSN. With the current SDK, this returns the Hub, and is
    mostly used to give tests something to test against.

    """
    return sentry_sdk.Hub.current


def capture_error(use_logger=None, exc_info=None, extra=None):
    """Capture an error to send to Sentry

    If Sentry is configured, this will send it using capture_exception().

    If Sentry is not enabled, this will log it to the logger.

    :arg use_logger: the logger to use; defaults to the logger for this module
    :arg exc_info: the exception information as a tuple like from ``sys.exc_info``
    :arg extra: dict holding additional information to add to the scope before
        capturing this exception

    """
    use_logger = use_logger or logger

    exc_info = exc_info or sys.exc_info()

    if is_enabled():
        extra = extra or {}

        try:
            # Get the configured Sentry hub
            hub = get_hub()

            with sentry_sdk.push_scope() as scope:
                for key, value in extra.items():
                    scope.set_extra(key, value)

                # Send the exception.
                identifier = hub.capture_exception(error=exc_info)
                use_logger.info("Error captured in Sentry! Reference: %s" % identifier)

                # At this point, if everything is good, the exceptions were
                # successfully sent to sentry and we can return.
                return
        except Exception:
            # Log the exception from trying to send the error to Sentry.
            use_logger.error("Unable to report error with Sentry", exc_info=True)

    # Sentry isn't configured or it's busted, so log the error we got that we
    # wanted to capture.
    use_logger.warning("Sentry has not been configured and an exception happened")
    use_logger.error("Exception occurred", exc_info=exc_info)