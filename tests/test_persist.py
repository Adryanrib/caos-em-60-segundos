import unittest
from scripts.persist import persist


class PersistTests(unittest.TestCase):
    def test_insert_and_update_do_not_touch_status(self):
        calls = []
        def fake(url, key, table, method='GET', query='', payload=None):
            calls.append((table, method, query, payload))
            if table == 'sources':
                return [{'id':'source-1', 'platform':'twitch', 'channel':'alanzoka', 'enabled': True, 'rights_verified':True}]
            if table == 'clips' and method == 'GET':
                return [{'platform_clip_id':'existing-id','views':5}]
            return []
        inp = [
            {'id':'existing-id','source':'twitch','channel':'alanzoka','url':'https://www.twitch.tv/clip/existing-id','views':8},
            {'id':'new-id','source':'twitch','channel':'alanzoka','url':'https://www.twitch.tv/clip/new-id','views':10},
            {'id':'unauthorized','source':'twitch','channel':'unknown','url':'https://www.twitch.tv/clip/unauthorized','views':100},
        ]
        self.assertEqual(persist(inp,'https://project.supabase.co','secret', fake),(1,1))
        writes = [(t,m,p) for t,m,q,p in calls if m in ('POST','PATCH')]
        self.assertEqual(len(writes),2)
        self.assertEqual(writes[0][2][0]['platform_clip_id'],'new-id')
        self.assertEqual(writes[1][2], {'views':8})


if __name__ == '__main__':
    unittest.main()
