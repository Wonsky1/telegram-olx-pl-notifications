from datetime import datetime
from unittest import IsolatedAsyncioTestCase

from tools.datetime_utils import WARSAW_TZ, now_warsaw


class TestNowWarsaw(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass

    async def test_returns_naive_datetime_in_warsaw_timezone(self):
        dt = now_warsaw()
        self.assertIsInstance(dt, datetime)
        self.assertIsNone(dt.tzinfo)
        # Compare against current Warsaw time (naive)
        expected = datetime.now(WARSAW_TZ).astimezone(WARSAW_TZ).replace(tzinfo=None)
        # Should be within a few seconds
        self.assertLess(abs((expected - dt).total_seconds()), 5)
