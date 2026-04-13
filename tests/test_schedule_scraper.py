import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1watch.scrapers.schedule import get_f1_event_details, get_f1_schedule  # noqa: E402


def _response(html: str) -> Mock:
    response = Mock()
    response.content = html.encode("utf-8")
    response.raise_for_status = Mock()
    return response


class TestScheduleScraper(unittest.TestCase):
    def test_get_f1_event_details_ignores_non_session_lists_before_schedule(self):
        html = """
        <html><body>
        <ul>
          <li><span></span><span>Why the Miami Grand Prix is special</span></li>
        </ul>
        <ul>
          <li>
            <span>01 May</span><span>01</span><span>May</span><span></span>
            <span>Practice 1</span><span>Practice 1</span><span></span>
            <span>16:30 - 17:30</span><span>16:30 - 17:30</span>
          </li>
        </ul>
        </body></html>
        """
        session = Mock()
        session.get.return_value = _response(html)

        details = get_f1_event_details(2026, "/en/racing/2026/miami", session=session)

        self.assertEqual(
            details,
            [{"event": "Miami", "session": "FP1", "start": "2026-05-01T16:30:00-00:00"}],
        )

    def test_get_f1_event_details_parses_session_rows(self):
        html = """
        <html><body>
        <ul>
          <li>
            <span>01 May</span><span>01</span><span>May</span><span></span>
            <span>Practice 1</span><span>Practice 1</span><span></span>
            <span>16:30 - 17:30</span><span>16:30 - 17:30</span>
          </li>
        </ul>
        </body></html>
        """
        session = Mock()
        session.get.return_value = _response(html)

        details = get_f1_event_details(2026, "/en/racing/2026/miami", session=session)

        self.assertEqual(
            details,
            [{"event": "Miami", "session": "FP1", "start": "2026-05-01T16:30:00-00:00"}],
        )

    def test_get_f1_schedule_fails_when_an_event_page_cannot_be_fetched(self):
        season_html = """
        <html><body>
          <a class="group" href="/en/racing/2026/miami">Miami</a>
          <a class="group" href="/en/racing/2026/canada">Canada</a>
        </body></html>
        """
        canada_html = """
        <html><body>
        <ul>
          <li>
            <span>22 May</span><span>22</span><span>May</span><span></span>
            <span>Practice 1</span><span>Practice 1</span><span></span>
            <span>16:30 - 17:30</span><span>16:30 - 17:30</span>
          </li>
        </ul>
        </body></html>
        """

        class FakeSession:
            def get(self, url, timeout):
                if url.endswith("/en/racing/2026"):
                    return _response(season_html)
                if url.endswith("/en/racing/2026/miami"):
                    raise requests.exceptions.RequestException("boom")
                if url.endswith("/en/racing/2026/canada"):
                    return _response(canada_html)
                raise AssertionError(f"Unexpected URL: {url}")

            def mount(self, *_args, **_kwargs):
                return None

        with patch("f1watch.scrapers.schedule._http_session", return_value=FakeSession()):
            with self.assertRaisesRegex(RuntimeError, "miami"):
                get_f1_schedule(2026)


if __name__ == "__main__":
    unittest.main()
