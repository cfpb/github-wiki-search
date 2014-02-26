import unittest
import sync
import types

class TestGitEvents(unittest.TestCase):
    def test_get_changed_page_urls_when_one_new_wiki_event_expect_one_url(self):
        page_url = 'http://host.com/user/repo/wiki/page'
        cut = sync.GitEvents()
        def moc_get_page_of_events(self, page=1, etag=True):
            return [{'id': '5', 'type': 'gollumEvent', 'pages': [{'html_url': page_url}]}]

        cut.get_page_of_events = types.MethodType(moc_get_page_of_events, cut)

        actual = cut.get_changed_page_urls()

        self.assertEqual(actual, [page_url])

    def test_get_changed_page_urls_when_one_new_wiki_event_with_two_changed_pages_expect_two_urls(self):
        page1_url = 'http://host.com/user/repo/wiki/page1'
        page2_url = 'http://host.com/user/repo/wiki/page2'
        cut = sync.GitEvents()
        def moc_get_page_of_events(self, page=1, etag=True):
            return [{'id': '5', 'type': 'gollumEvent', 'pages': [{'html_url': page1_url}, {'html_url': page2_url}]}]

        cut.get_page_of_events = types.MethodType(moc_get_page_of_events, cut)

        actual = cut.get_changed_page_urls()

        self.assertIn(page1_url, actual)
        self.assertIn(page2_url, actual)
        self.assertEqual(len(actual), 2)

    def test_get_changed_page_urls_when_two_new_wiki_event_for_same_page_expect_one_url(self):
        page_url = 'http://host.com/user/repo/wiki/page'
        cut = sync.GitEvents()
        def moc_get_page_of_events(self, page=1, etag=True):
            return [{'id': '6', 'type': 'gollumEvent', 'pages': [{'html_url': page_url}]}, {'id': '5', 'type': 'gollumEvent', 'pages': [{'html_url': page_url}]}]

        cut.get_page_of_events = types.MethodType(moc_get_page_of_events, cut)

        actual = cut.get_changed_page_urls()

        self.assertEqual(actual, [page_url])

    def test_get_changed_page_urls_when_one_new_wiki_event_one_other_event_expect_one_url(self):
        page_url = 'http://host.com/user/repo/wiki/page'
        cut = sync.GitEvents()
        def moc_get_page_of_events(self, page=1, etag=True):
            return [{'id': '6', 'type': 'add'}, {'id': '5', 'type': 'gollumEvent', 'pages': [{'html_url': page_url}]}]

        cut.get_page_of_events = types.MethodType(moc_get_page_of_events, cut)

        actual = cut.get_changed_page_urls()

        self.assertEqual(actual, [page_url])

    def test_get_changed_page_urls_when_one_new_and_one_old_wiki_event_expect_one_url(self):
        page1_url = 'http://host.com/user/repo/wiki/page1'
        page2_url = 'http://host.com/user/repo/wiki/page2'
        cut = sync.GitEvents()
        def moc_get_page_of_events(self, page=1, etag=True):
            return [{'id': '6', 'type': 'gollumEvent', 'pages': [{'html_url': page2_url}]}, {'id': '5', 'type': 'gollumEvent', 'pages': [{'html_url': page1_url}]}]

        cut.get_page_of_events = types.MethodType(moc_get_page_of_events, cut)
        cut.last_event = 5
        actual = cut.get_changed_page_urls()

        self.assertEqual(actual, [page2_url])

    def test_get_changed_page_urls_when_two_new_events_on_two_result_pages_expect_two_urls(self):
        page1_url = 'http://host.com/user/repo/wiki/page1'
        page2_url = 'http://host.com/user/repo/wiki/page2'
        cut = sync.GitEvents()
        cut.last_event = 4
        def moc_get_page_of_events(self, page=1, etag=True):
            print "PAGE", page
            if page == 1:
                return [{'id': '6', 'type': 'gollumEvent', 'pages': [{'html_url': page2_url}]}]
            if page == 2:
                return [{'id': '5', 'type': 'gollumEvent', 'pages': [{'html_url': page1_url}]}, {'id': '4', 'type': 'add'}]
        cut.get_page_of_events = types.MethodType(moc_get_page_of_events, cut)

        actual = cut.get_changed_page_urls()

        self.assertIn(page1_url, actual)
        self.assertIn(page2_url, actual)
        self.assertEqual(len(actual), 2)

if __name__ == '__main__':
    unittest.main() 