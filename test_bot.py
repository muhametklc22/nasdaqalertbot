import unittest
from datetime import datetime, timezone, timedelta
from bot import analyze, news_summary, headline_assessment


class AlertTests(unittest.TestCase):
    def rows(self, price):
        highs = [9, 9.2, 10, 9.6, 9.5, 9.4, 9.3, max(price, 9.3)]
        return [dict(high=h, low=h-.3, close=(price if i==7 else h-.1),
                     timestamp=datetime.now(timezone.utc), volume=1000) for i,h in enumerate(highs)]

    def test_three_percent_boundary(self):
        self.assertIsNone(analyze(self.rows(9.699), [11, 12]))
        self.assertEqual(analyze(self.rows(9.7), [11, 12])['kind'], 'YAKLAŞMA')

    def test_breakout_and_resistances_above_entry(self):
        result = analyze(self.rows(10.01), [9, 11, 11.01, 12])
        self.assertEqual(result['kind'], 'KIRILIM')
        self.assertEqual(result['resistances'], [11, 12])
        self.assertLess(result['stop'], result['level'])

    def test_consumed_level_not_reused(self):
        rows = self.rows(10.1)
        rows[-2]['high'] = 10.05
        self.assertIsNone(analyze(rows, []))

    def test_no_invented_resistances(self):
        self.assertEqual(analyze(self.rows(9.8), [])['resistances'], [])

    def test_future_or_old_news_excluded(self):
        now = datetime.now(timezone.utc)
        items = [dict(content=dict(title='old', pubDate=(now-timedelta(days=2)).isoformat())),
                 dict(content=dict(title='future', pubDate=(now+timedelta(hours=1)).isoformat()))]
        self.assertNotIn('old', news_summary(items, now))
        self.assertNotIn('future', news_summary(items, now))

    def test_news_uncertainty_and_conflicting_headlines(self):
        self.assertTrue(headline_assessment('Company announces meeting').startswith('BELİRSİZ'))
        self.assertTrue(headline_assessment('FDA approval and public offering').startswith('KARIŞIK'))
        self.assertTrue(headline_assessment('Company regains Nasdaq compliance').startswith('OLUMLU İPUCU'))


if __name__ == '__main__':
    unittest.main()
