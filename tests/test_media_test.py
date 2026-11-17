import unittest
from unittest.mock import patch
from scripts.media_test import validate_twitch_clip_url, select_candidate


class MediaTests(unittest.TestCase):
    def test_public_clip_link(self):
        self.assertEqual(validate_twitch_clip_url('https://www.twitch.tv/alanzoka/clip/GlamorousArtsyHerringOhMyDog-y88u-LZMiRLckMmf?lang=pt-br'), 'https://www.twitch.tv/alanzoka/clip/GlamorousArtsyHerringOhMyDog-y88u-LZMiRLckMmf')

    def test_external_url_rejected(self):
        for url in ('https://evil.com/a/clip/abcdefgh', 'http://www.twitch.tv/alanzoka/clip/abcdefgh', 'https://www.twitch.tv/alanzoka'):
            with self.assertRaises(ValueError):
                validate_twitch_clip_url(url)

    @patch('scripts.media_test.supabase_request')
    def test_queue_requires_rights(self, request):
        request.side_effect = [
            [{'clip_id': '123', 'rank_score': 80}],
            [{'id': '123', 'source_id': '555', 'title': 'Teste', 'original_url': 'https://www.twitch.tv/alanzoka/clip/abcdefgh'}],
            [{'id': '555', 'platform': 'twitch', 'channel': 'alanzoka', 'enabled': True, 'rights_verified': False}]
        ]
        with self.assertRaises(RuntimeError):
            select_candidate()


if __name__ == '__main__':
    unittest.main()
