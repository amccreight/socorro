# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from textwrap import dedent

import mock
from pygments.formatters import HtmlFormatter

from django.urls import reverse
from django.utils.encoding import smart_text

from crashstats.sources.views import ALLOWED_SOURCE_HOSTS


HOST = ALLOWED_SOURCE_HOSTS[0]


def test_highlight_url(client, requests_mock):
    requests_mock.get(f"https://{HOST}/404.h", status_code=404)
    requests_mock.get(
        f"https://{HOST}/200.h",
        text=dedent(
            """
            //
            // Automatically generated by ipdlc.
            // Edit at your own risk
            //


            #include "mozilla/layers/PCompositorBridgeChild.h"
            """
        ),
    )

    url = reverse("sources:highlight_url")

    # No url provided and empty url
    response = client.get(url)
    assert response.status_code == 400
    response = client.get(url, {"url": ""})
    assert response.status_code == 400

    # Bad host
    response = client.get(url, {"url": "https://example.com/403.h"})
    assert response.status_code == 403

    # Correct host, but bad scheme
    response = client.get(url, {"url": f"ftp://{HOST}/404.h"})
    assert response.status_code == 403

    # Correct host, but missing page
    response = client.get(url, {"url": f"https://{HOST}/404.h"})
    assert response.status_code == 404

    # Correct host and correct page
    response = client.get(url, {"url": f"https://{HOST}/200.h"})
    assert response.status_code == 200

    # Make sure it's really an HTML page.
    assert "</html>" in smart_text(response.content)
    assert response["content-type"] == "text/html"

    # Our security headers should still be set.
    # Just making sure it gets set. Other tests assert their values.
    assert response["x-frame-options"]
    assert response["content-security-policy"]


def test_highlight_line(client, requests_mock):
    requests_mock.get(
        f"https://{HOST}/200.h",
        text=dedent(
            """
            //
            // Automatically generated by ipdlc.
            // Edit at your own risk
            //


            #include "mozilla/layers/PCompositorBridgeChild.h"
            """
        ),
    )

    url = reverse("sources:highlight_url")
    static_kwargs = {"full": True, "linenos": "table", "lineanchors": "L"}

    with mock.patch(
        "crashstats.sources.views.HtmlFormatter", wraps=HtmlFormatter
    ) as MockFormatter:
        # A missing line parameter means no lines are highlighted
        response = client.get(url, {"url": f"https://{HOST}/200.h"})
        assert response.status_code == 200
        MockFormatter.assert_called_with(title="/200.h", hl_lines=[], **static_kwargs)

        # An invalid line parameter means no lines are highlighted
        MockFormatter.reset_mock()
        response = client.get(
            url, {"url": f"https://{HOST}/200.h", "line": "not_a_number"}
        )
        assert response.status_code == 200
        MockFormatter.assert_called_with(title="/200.h", hl_lines=[], **static_kwargs)

        # A valid line parameter is passed on to pygments
        MockFormatter.reset_mock()
        response = client.get(url, {"url": f"https://{HOST}/200.h", "line": "403"})
        assert response.status_code == 200
        MockFormatter.assert_called_with(
            title="/200.h", hl_lines=[403], **static_kwargs
        )
