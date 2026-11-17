import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from scripts.discover import discover

class DiscoverTests(unittest.TestCase):
    @patch('scripts.discover.api_headers', return_value={})
    @patch('scripts.discover.request')
    def test_discovery(self, request, _headers):
        request.side_effect = [{'data': [{'id': '123'}]}, {'data': [{'id':'abc', 'title':'Teste', 'url':'https://clips.twitch.tv/abc', 'view_count':42, 'created_at':'2026-11-16T00:00:00Z','duration':18}]}]
        clips = discover(['alanzoka'], datetime(2026,11,16,tzinfo=timezone.utc))
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]['channel'], 'alanzoka')
        self.assertEqual(clips[0]['views'], 42)

if __name__ == '__main__':
    unittest.main()
