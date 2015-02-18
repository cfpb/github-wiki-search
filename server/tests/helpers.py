try:
    import unittest2 as unittest
except:
    import unittest

from server.search import helpers
es_client = helpers.es_client
helpers.search_client = es_client.test_search
helpers.ac_client = es_client.test_autocomplete
helpers.history_client = es_client.test_history

helpers.search_index = 'test_search'
helpers.history_index = 'test_history'

from server import schemas

class TestResetIndex(unittest.TestCase):
    def test_expect_creates_index(self):
        cut = helpers.reset_index

        cut('test_search')

        actual = es_client._cat.indices.get().text
        self.assertIn('test_search', actual)

    def test_expect_adds_appropriate_mapping(self): 
        cut = helpers.reset_index

        cut('test_search')

        actual = es_client.test_search._mapping.get().json()['test_search']['mappings'].keys()
        actual.sort()
        schema_keys = schemas.test_search['mappings'].keys()
        schema_keys.sort()
        self.assertEqual(actual, schema_keys)

    def test_expect_destroys_existing_index(self):
        cut = helpers.reset_index

        cut('test_search')
        es_client.test_search.test_type.test_item.put(data={'hello': 'world'})

        cut('test_search')

        actual = es_client.test_search.test_type.test_item.get()
        self.assertGreater(actual.status_code, 400)

class TestDeleteIndexSubset(unittest.TestCase):
    def setUp(self):
        helpers.reset_index('test_search')

    def test_expect_delete_all_repo_docs(self):
        es_client.test_search.wiki.test1.put(data={'path':'/a/b', 'title': 'test1', 'source': 'github'})

        cut = helpers.delete_index_subset
        cut('GH', 'wiki', '/a/b')

        actual = es_client.test_search.wiki.test1.get()
        self.assertGreater(actual.status_code, 400)

    def test_expect_not_delete_docs_in_other_repo(self):
        es_client.test_search.wiki.test1.put(data={'path':'/a/c', 'title': 'test1', 'source': 'github'})

        cut = helpers.delete_index_subset
        cut('GH', 'wiki', '/a/b')

        actual = es_client.test_search.wiki.test1.get()
        self.assertEqual(actual.status_code, 200)

    def test_expect_not_delete_docs_of_other_type(self):
        es_client.test_search.readme.test1.put(data={'path':'/a/b', 'title': 'test1', 'source': 'github'})

        cut = helpers.delete_index_subset
        cut('GH', 'wiki', '/a/b')

        actual = es_client.test_search.readme.test1.get()
        self.assertEqual(actual.status_code, 200)

    def test_expect_not_delete_docs_of_other_gh_type(self):
        es_client.test_search.wiki.test1.put(data={'path':'/a/b', 'title': 'test1', 'source': 'enterprise'})

        cut = helpers.delete_index_subset
        cut('GH', 'wiki', '/a/b')

        actual = es_client.test_search.wiki.test1.get()
        self.assertEqual(actual.status_code, 200)

class TestGetIndexedVersion(unittest.TestCase):
    def setUp(self):
        helpers.reset_index('test_history')

    def test_expect_returns_None_if_no_indexed_version(self):
        repo_name = '/a/b'

        cut = helpers.get_indexed_version
        actual = cut('GH', repo_name, 'wiki')

        self.assertIsNone(actual)

    def test_expect_returns_indexed_version_if_exists(self):
        repo_name = '/a/b'
        helpers.save_indexed_version('GH', repo_name, 'wiki', 'xxx')

        cut = helpers.get_indexed_version
        actual = cut('GH', repo_name, 'wiki')

        self.assertEqual(actual, 'xxx')


class TestSaveIndexedVersion(unittest.TestCase):
    def setUp(self):
        helpers.reset_index('test_history')

    def test_expect_create_doc_with_new_verison_if_not_exist(self):
        repo_name = '/a/b'
        doc_id = ('GH/' + repo_name).replace('/', '%2F')
        cut = helpers.save_indexed_version

        cut('GH', repo_name, 'wiki', 'xxx')

        actual = helpers.history_client.wiki._(doc_id).get().json()
        self.assertEqual(actual['_source'], {u'version': u'xxx'})

    def test_expect_update_doc_with_new_verison_if_already_exist(self):
        repo_name = '/a/b'
        doc_id = ('GH/' + repo_name).replace('/', '%2F')
        cut = helpers.save_indexed_version

        cut('GH', repo_name, 'wiki', 'xxx')

        cut('GH', repo_name, 'wiki', 'yyy')

        actual = helpers.history_client.wiki._(doc_id).get().json()
        self.assertEqual(actual['_source'], {u'version': u'yyy'})

class TestWriteBulkData(unittest.TestCase):
    def setUp(self):
        helpers.reset_index('test_search')

    bulk_data = [
      {
        "index": {
          "_type": "wiki",
          "_id": "a%2Fb",
          "_index": "test_search"
        }
      },
      {
        "url": "http://example.com/a/b",
        "content": "The quick brown fox",
        "path": "/a/b",
        "title": "Alpha Bravo"
      },
      {
        "index": {
          "_type": "wiki",
          "_id": "c%2Fd",
          "_index": "test_search"
        }
      },
      {
        "url": "http://example.com/c/d",
        "content": "jumped over the lazy dog",
        "path": "/c/d",
        "title": "Charly Delta"
      },
    ]
    def test_expect_writes_bulk_rows(self):
        cut = helpers.write_bulk_data

        cut(self.bulk_data)
        actual = es_client.test_search._count.get().json()
        self.assertEqual(actual['count'], 2)
