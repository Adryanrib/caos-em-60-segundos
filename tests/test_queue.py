import unittest
from datetime import datetime, timezone
from scripts.queue import choose, rating

NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)

class QueueTests(unittest.TestCase):
    def make(self, ident, views, status='discovered'):
        return dict(id=ident, views=views, status=status,
                    original_url='https://twitch.tv/example/clip/abc',
                    created_at='2026-11-16T18:00:00Z')

    def test_select_high_views_without_duplicates(self):
        clips = [self.make('a', 5), self.make('b', 200), self.make('c', 100)]
        self.assertEqual([x['id'] for x in choose(clips, {'b'}, 2, NOW)], ['c', 'a'])

    def test_not_choose_processed(self):
        self.assertEqual(choose([self.make('a', 50, 'published')], set(), 3, NOW), [])

    def test_rating(self):
        self.assertLessEqual(rating(self.make('a', 1000000), NOW), 100)
