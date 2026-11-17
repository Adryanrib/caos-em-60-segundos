import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import batch_render as b

class BatchTests(unittest.TestCase):
    @patch.object(b, 'request')
    def test_claim_uses_conditional_patch(self, req):
        req.return_value = [{'clip_id': 'id1'}]
        self.assertTrue(b.claim({'clip_id': 'id1'}))
        args, _ = req.call_args
        self.assertEqual(args[2]['status'], 'eq.awaiting_media')
        self.assertEqual(args[1], 'PATCH')

    @patch.object(b, 'request')
    def test_claim_denied(self, req):
        req.return_value = []
        self.assertFalse(b.claim({'clip_id': 'id1'}))

    @patch.object(b, 'request')
    def test_count_today_excludes_old_records(self, req):
        req.return_value = [{'clip_id': 'x'}, {'clip_id': 'y'}]
        self.assertEqual(b.count_today(), 2)
        kwargs = req.call_args.kwargs
        self.assertIn('rendered_at', kwargs['params'])

if __name__ == '__main__':
    unittest.main()
