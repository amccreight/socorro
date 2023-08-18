# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import time
from urllib.parse import quote_plus, parse_qs, urlsplit

import pytest

from django.core.cache import cache
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.safestring import SafeText

from crashstats import libproduct
from crashstats.crashstats.templatetags.jinja_helpers import (
    generate_create_bug_url,
    change_query_string,
    digitgroupseparator,
    is_dangerous_cpu,
    replace_bugzilla_links,
    show_bug_link,
    show_duration,
    show_filesize,
    time_tag,
    timestamp_to_date,
    url,
)


class TestTimestampToDate:
    def test_timestamp_to_date(self):
        timestamp = time.time()
        date = datetime.datetime.fromtimestamp(timestamp)
        output = timestamp_to_date(int(timestamp))
        assert date.strftime("%Y-%m-%d %H:%M:%S") in output
        assert "%Y-%m-%d %H:%M:%S" in output

        # Test missing and bogus values.
        output = timestamp_to_date(None)
        assert output == ""

        output = timestamp_to_date("abc")
        assert output == ""


class TestTimeTag:
    def test_time_tag_with_datetime(self):
        date = datetime.datetime(2000, 1, 2, 3, 4, 5)
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            date.isoformat(), date.strftime("%a, %b %d, %Y at %H:%M %Z")
        )
        assert output == expected

    def test_time_tag_with_date(self):
        date = datetime.date(2000, 1, 2)
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            date.isoformat(), date.strftime("%a, %b %d, %Y at %H:%M %Z")
        )
        assert output == expected

    def test_time_tag_future(self):
        date = datetime.datetime(2000, 1, 2, 3, 4, 5)
        output = time_tag(date, future=True)

        expected = '<time datetime="{}" class="in">{}</time>'.format(
            date.isoformat(), date.strftime("%a, %b %d, %Y at %H:%M %Z")
        )
        assert output == expected

    def test_time_tag_invalid_date(self):
        output = time_tag("junk")
        assert output == "junk"

    def test_parse_with_unicode_with_timezone(self):
        # See https://bugzilla.mozilla.org/show_bug.cgi?id=1300921
        date = "2016-09-07T00:38:42.630775+00:00"
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            "2016-09-07T00:38:42.630775+00:00", "Wed, Sep 07, 2016 at 00:38 +00:00"
        )
        assert output == expected


class TestBugzillaLink:
    def test_show_bug_link_no_cache(self):
        output = show_bug_link(123)
        assert 'data-id="123"' in output
        assert "bug-link-without-data" in output
        assert "bug-link-with-data" not in output

    def test_show_bug_link_with_cache(self):
        cache_key = "buginfo:456"
        data = {
            "summary": "<script>xss()</script>",
            "resolution": "MESSEDUP",
            "status": "CONFUSED",
        }
        cache.set(cache_key, data, 5)
        output = show_bug_link(456)
        assert 'data-id="456"' in output
        assert "bug-link-without-data" not in output
        assert "bug-link-with-data" in output
        assert 'data-resolution="MESSEDUP"' in output
        assert 'data-status="CONFUSED"' in output
        assert 'data-summary="&lt;script&gt;xss()&lt;/script&gt;"' in output


class Test_generate_create_bug_url:
    CRASHING_THREAD = 0
    TEMPLATE = (
        "https://bugzilla.mozilla.org/enter_bug.cgi?"
        + "bug_type=%(bug_type)s&"
        + "product=Firefox&"
        + "op_sys=%(op_sys)s&"
        + "rep_platform=%(rep_platform)s&"
        + "cf_crash_signature=%(signature)s&"
        + "short_desc=%(title)s&"
        + "comment=%(description)s&"
        + "format=__default__"
    )
    CRASH_ID = "70dda764-a402-4ca3-b806-c38dd0240328"

    def _create_report(self, **overrides):
        default = {
            "signature": "$&#;deadbeef",
            "uuid": self.CRASH_ID,
            "cpu_arch": "x86",
            "os_name": None,
        }
        return dict(default, **overrides)

    def _extract_query_string(self, url):
        return parse_qs(urlsplit(url).query)

    def _create_frame(
        self,
        frame=1,
        module="fake_module",
        signature="foo::bar(char *x, int y)",
        file="fake.cpp",
        line=1,
        inlines=None,
        unloaded_modules=None,
    ):
        data = {
            "frame": frame,
            "module": module,
            "signature": signature,
            "file": file,
            "line": line,
        }
        if inlines:
            data["inlines"] = inlines
        if unloaded_modules:
            data["unloaded_modules"] = unloaded_modules

        return data

    def _create_thread(self, frames=None):
        return {"frames": frames or []}

    def _create_dump(self, threads=None):
        return {"threads": threads or []}

    def test_basic_url(self):
        report = self._create_report(
            os_name="Windows", crashing_thread=self.CRASHING_THREAD
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert qs["cf_crash_signature"] == ["[@ $&#;deadbeef]"]
        assert qs["format"] == ["__default__"]
        assert qs["product"] == ["Firefox"]
        assert qs["rep_platform"] == ["x86"]
        assert qs["short_desc"] == ["Crash in [@ $&#;deadbeef]"]
        assert qs["op_sys"] == ["Windows"]
        assert qs["bug_type"] == ["defect"]
        comment_lines = [
            f"Crash report: http://localhost:8000/report/index/{self.CRASH_ID}"
        ]
        comment = "\n".join(comment_lines)
        assert qs["comment"] == [comment]

    def test_truncate_short_desc(self):
        report = self._create_report(
            os_name="Windows",
            signature="x" * 1000,
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert len(qs["short_desc"][0]) == 255
        assert qs["short_desc"][0].endswith("...")

    def test_corrected_os_version_name(self):
        report = self._create_report(
            os_name="Windoooosws",
            os_pretty_version="Windows 10",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windows 10"]

        # os_name if the os_pretty_version is there, but empty
        report = self._create_report(
            os_name="Windoooosws",
            os_pretty_version="",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windoooosws"]

        # "OS X <Number>" becomes "macOS"
        report = self._create_report(
            os_name="OS X",
            os_pretty_version="OS X 11.1",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["macOS"]

        # "Windows 8.1" becomes "Windows 8"
        report = self._create_report(
            os_name="Windows NT",
            os_pretty_version="Windows 8.1",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windows 8"]

        # "Windows Unknown" becomes plain "Windows"
        report = self._create_report(
            os_name="Windows NT",
            os_pretty_version="Windows Unknown",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windows"]

    def test_with_os_name_is_null(self):
        """Some processed crashes have a os_name but it's null."""
        report = self._create_report(
            os_name=None,
            signature="java.lang.IllegalStateException",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        assert "op_sys" not in qs

    def test_with_unicode_signature(self):
        """The jinja helper generate_create_bug_url should work when
        the signature contains non-ascii characters.

        Based on an actual error in production:
        https://bugzilla.mozilla.org/show_bug.cgi?id=1383269
        """
        report = self._create_report(
            os_name=None,
            signature="YouTube\u2122 No Buffer (Stop Auto-playing)",
            crashing_thread=self.CRASHING_THREAD,
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        # Most important that it should work
        assert (
            "Crash+in+%5B%40+YouTube%E2%84%A2+No+Buffer+%28Stop+Auto-playing%29%5D"
            in url
        )

    def test_comment(self):
        report = self._create_report(
            crashing_thread=1,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(),  # Empty thread 0
                    self._create_thread(
                        frames=[
                            self._create_frame(frame=0),
                            self._create_frame(frame=1),
                            self._create_frame(frame=2),
                        ]
                    ),
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )

        # Assert that the crash id is in the comment
        assert quote_plus(report["uuid"]) in url

        # Assert that the top 3 frames are in the comment
        assert quote_plus("Top 3 frames of crashing thread:") in url

        frame1 = report["json_dump"]["threads"][1]["frames"][1]
        assert (
            quote_plus("1  {module}  {signature}  {file}:{line}".format(**frame1))
            in url
        )

    def test_comment_no_threads(self):
        """If json_dump has no threads available, do not output any frames."""
        report = self._create_report(crashing_thread=0)
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("frames of crashing thread:") not in url

    def test_comment_more_than_ten_frames(self):
        """If the crashing thread has more than ten frames, only display top ten."""
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[self._create_frame(frame=frame) for frame in range(10)]
                        + [self._create_frame(frame=10, module="do_not_include")]
                    )
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("do_not_include") not in url

    def test_comment_frame_long_signature(self):
        """If a frame signature is too long, it gets truncated."""
        long_signature = "foo::bar(" + ("char* x, " * 15) + "int y)"
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module="test_module",
                                signature=long_signature,
                                file="foo.cpp",
                                line=7,
                            )
                        ]
                    )
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        line = quote_plus(
            "0  "
            + "test_module  "
            + "foo::bar(char* x, char* x, char* x, char* x, char* x, char* x, char* x, char*...  "
            + "foo.cpp:7"
        )
        assert line in url

    def test_comment_function_inlines(self):
        """Include inlines functions."""
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module="test_module",
                                signature="foo::bar(char* x, int y)",
                                file="foo.cpp",
                                line=7,
                                inlines=[
                                    {
                                        "file": "foo_inline.cpp",
                                        "line": 100,
                                        "function": "_foo_inline",
                                    },
                                    {
                                        "file": "foo_inline.cpp",
                                        "line": 4,
                                        "function": "_foo_inline_amd64",
                                    },
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        comment = (
            "```\n"
            + "0  test_module  _foo_inline  foo_inline.cpp:100\n"
            + "0  test_module  _foo_inline_amd64  foo_inline.cpp:4\n"
            + "0  test_module  foo::bar(char* x, int y)  foo.cpp:7\n"
            + "```"
        )
        assert comment in qs["comment"][0]

    def test_comment_function_unloaded_modules(self):
        """Include unloaded modules."""
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module=None,
                                file=None,
                                line=None,
                                signature="(unloaded unmod@0xe4df)",
                            ),
                        ],
                    ),
                ],
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        qs = self._extract_query_string(url)
        comment = "```\n" + "0  ?  (unloaded unmod@0xe4df)\n" + "```"
        assert comment in qs["comment"][0]

    def test_comment_missing_line(self):
        """If a frame is missing a line number, do not include it."""
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module="test_module",
                                signature="foo::bar(char* x, int y)",
                                file="foo.cpp",
                                line=None,
                            )
                        ]
                    )
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("0  test_module  foo::bar(char* x, int y)  foo.cpp\n") in url

    def test_comment_missing_file(self):
        """If a frame is missing file info, do not include it."""
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module="test_module",
                                signature="foo::bar(char* x, int y)",
                                file=None,
                                line=None,
                            )
                        ]
                    )
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("0  test_module  foo::bar(char* x, int y)\n") in url

    def test_comment_missing_everything(self):
        """If a frame is missing everything, do not throw an error."""
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(threads=[self._create_thread(frames=[{}])]),
        )
        generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )

    def test_comment_no_html_escaping(self):
        """If a frame contains <, >, &, or ", they should not be HTML
        escaped in the comment body.

        """
        report = self._create_report(
            crashing_thread=0,
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module="&test_module",
                                signature="foo<char>::bar(char* x, int y)",
                                file='"foo".cpp',
                                line=7,
                            )
                        ]
                    )
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert (
            quote_plus('0  &test_module  foo<char>::bar(char* x, int y)  "foo".cpp:7')
            in url
        )

    def test_comment_java_stack_trace(self):
        """If there's a java stack trace, use that instead."""
        report = self._create_report(crashing_thread=0)
        report["java_stack_trace"] = "java.lang.NullPointerException: list == null"
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("Java stack trace:") in url
        assert quote_plus("java.lang.NullPointerException: list == null") in url

        # Make sure it didn't also add the crashing frames
        assert quote_plus("frames of crashing thread:") not in url

    def test_comment_reason(self):
        """Verify Reason makes it into the comment."""
        report = self._create_report(
            crashing_thread=0,
            reason="SIGSEGV /0x00000080",
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(frame=0),
                            self._create_frame(frame=1),
                            self._create_frame(frame=2),
                        ]
                    ),
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("Reason: ```SIGSEGV /0x00000080```") in url

    def test_comment_moz_crash_reason(self):
        """Verify Reason makes it into the comment."""
        report = self._create_report(
            crashing_thread=0,
            moz_crash_reason="good_data",
            moz_crash_reason_raw="bad_data",
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(frame=0),
                            self._create_frame(frame=1),
                            self._create_frame(frame=2),
                        ]
                    ),
                ]
            ),
        )
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("MOZ_CRASH Reason: ```good_data```") in url
        assert quote_plus("bad_data") not in url

    def test_comment_crashing_thread_none(self):
        """Verify Reason makes it into the comment."""
        report = self._create_report(
            json_dump=self._create_dump(
                threads=[
                    self._create_thread(
                        frames=[
                            self._create_frame(
                                frame=0,
                                module="test_module",
                                signature="foo::bar",
                                file="foo.cpp",
                                line=7,
                            ),
                        ]
                    ),
                ]
            )
        )
        # NOTE(willkg): we don't want crashing_thread in the report for this test
        assert "crashing_thread" not in report
        url = generate_create_bug_url(
            f"http://localhost:8000/report/index/{self.CRASH_ID}",
            self.TEMPLATE,
            report,
        )
        assert quote_plus("No crashing thread identified; using thread 0.") in url
        assert quote_plus("0  test_module  foo::bar") in url

    @pytest.mark.parametrize("fn", libproduct.get_product_files())
    def test_product_bug_links(self, fn):
        """Verify bug links templates are well-formed."""
        product = libproduct.load_product_from_file(fn)

        report = self._create_report(crashing_thread=0)

        for _, template in product.bug_links:
            # If there's an error in the template, it'll raise an exception here
            generate_create_bug_url(
                f"http://localhost:8000/report/index/{self.CRASH_ID}",
                template,
                report,
            )


class TestReplaceBugzillaLinks:
    def test_simple(self):
        text = "a bug #1129515 b"
        res = replace_bugzilla_links(text)
        expected = 'a <a href="https://bugzilla.mozilla.org/show_bug.cgi?id=1129515">bug #1129515</a> b'
        assert res == expected

    def test_several_bugs(self):
        text = "abc bug #43 def bug #40878 bug #7845"
        res = replace_bugzilla_links(text)
        assert "https://bugzilla.mozilla.org/show_bug.cgi?id=43" in res
        assert "https://bugzilla.mozilla.org/show_bug.cgi?id=40878" in res
        assert "https://bugzilla.mozilla.org/show_bug.cgi?id=7845" in res


class TesDigitGroupSeparator:
    def test_basics(self):
        assert digitgroupseparator(None) is None
        assert digitgroupseparator(1000) == "1,000"
        assert digitgroupseparator(-1000) == "-1,000"
        assert digitgroupseparator(1000000) == "1,000,000"


class TestHumanizers:
    def test_show_duration(self):
        html = show_duration(59)
        assert isinstance(html, SafeText)
        assert html == "59 seconds"

        html = show_duration(150)
        assert isinstance(html, SafeText)
        expected = (
            '150 seconds <span class="humanized" title="150 seconds">'
            "(2 minutes and 30 seconds)</span>"
        )
        assert html == expected

        # if the number is digit but a string it should work too
        html = show_duration("1500")
        expected = (
            '1,500 seconds <span class="humanized" title="1,500 seconds">'
            "(25 minutes)</span>"
        )
        assert html == expected

    def test_show_duration_different_unit(self):
        html = show_duration(150, unit="cool seconds")
        assert isinstance(html, SafeText)
        expected = (
            "150 cool seconds "
            '<span class="humanized" title="150 cool seconds">'
            "(2 minutes and 30 seconds)</span>"
        )
        assert html == expected

    def test_show_duration_failing(self):
        html = show_duration(None)
        assert html is None
        html = show_duration("not a number")
        assert html == "not a number"

    def test_show_duration_safety(self):
        html = show_duration("<script>")
        assert not isinstance(html, SafeText)
        assert html == "<script>"

        html = show_duration(150, unit="<script>")
        assert isinstance(html, SafeText)
        expected = (
            "150 &lt;script&gt; "
            '<span class="humanized" title="150 &lt;script&gt;">'
            "(2 minutes and 30 seconds)</span>"
        )
        assert html == expected

    def test_show_filesize(self):
        html = show_filesize(100)
        assert isinstance(html, SafeText)
        assert html == "100 bytes"

        html = show_filesize(10000)
        assert isinstance(html, SafeText)
        expected = (
            "10,000 bytes "
            '<span class="humanized" title="10,000 bytes">'
            "(10 KB)</span>"
        )
        assert html == expected

        html = show_filesize("10000")
        assert isinstance(html, SafeText)
        expected = (
            "10,000 bytes "
            '<span class="humanized" title="10,000 bytes">'
            "(10 KB)</span>"
        )
        assert html == expected

    def test_show_filesize_failing(self):
        html = show_filesize(None)
        assert html is None

        html = show_filesize("junk")
        assert html == "junk"


class TestChangeURL:
    def test_root_url_no_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/")
        result = change_query_string(context)
        assert result == "/"

    def test_with_path_no_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/")
        result = change_query_string(context)
        assert result == "/page/"

    def test_with_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar&bar=baz")
        result = change_query_string(context)
        assert result == "/page/?foo=bar&bar=baz"

    def test_add_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/")
        result = change_query_string(context, foo="bar")
        assert result == "/page/?foo=bar"

    def test_change_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar")
        result = change_query_string(context, foo="else")
        assert result == "/page/?foo=else"

    def test_remove_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar")
        result = change_query_string(context, foo=None)
        assert result == "/page/"

    def test_remove_leave_some(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar&other=thing")
        result = change_query_string(context, foo=None)
        assert result == "/page/?other=thing"

    def test_change_query_without_base(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar")
        result = change_query_string(context, foo="else", _no_base=True)
        assert result == "?foo=else"


class TestURL:
    def test_basic(self):
        output = url("crashstats:login")
        assert output == reverse("crashstats:login")

        # now with a arg
        output = url("crashstats:product_home", "Firefox")
        assert output == reverse("crashstats:product_home", args=("Firefox",))

        # now with a kwarg
        output = url("crashstats:product_home", product="Waterfox")
        assert output == reverse("crashstats:product_home", args=("Waterfox",))

    def test_arg_cleanup(self):
        output = url("crashstats:product_home", "Firefox\n")
        assert output == reverse("crashstats:product_home", args=("Firefox",))

        output = url("crashstats:product_home", product="\tWaterfox")
        assert output == reverse("crashstats:product_home", args=("Waterfox",))

        # this is something we've seen in the "wild"
        output = url("crashstats:product_home", "Winterfox\\\\nn")
        assert output == reverse("crashstats:product_home", args=("Winterfoxnn",))

        # check that it works if left as a byte string too
        output = url("crashstats:product_home", "Winterfox\\\\nn")
        assert output == reverse("crashstats:product_home", args=("Winterfoxnn",))


class TestIsDangerousCPU:
    def test_false(self):
        assert is_dangerous_cpu(None, None) is False
        assert is_dangerous_cpu(None, "family 20 model 1") is False

    def test_true(self):
        assert is_dangerous_cpu(None, "AuthenticAMD family 20 model 1") is True
        assert is_dangerous_cpu(None, "AuthenticAMD family 20 model 2") is True
        assert is_dangerous_cpu("amd64", "family 20 model 1") is True
        assert is_dangerous_cpu("amd64", "family 20 model 2") is True
