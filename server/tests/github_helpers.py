try:
    import unittest2 as unittest
except:
    import unittest

from server.indexers import github_helpers
es_client = github_helpers.es_client
github_helpers.search_client = es_client.test_search
github_helpers.ac_client = es_client.test_autocomplete
github_helpers.history_client = es_client.test_history

from server import schemas

class TestResetIndex(unittest.TestCase):
    def test_expect_creates_index(self):
        cut = github_helpers.reset_index

        cut('test_search')

        actual = es_client._cat.indices.get().text
        self.assertIn('test_search', actual)

    def test_expect_adds_appropriate_mapping(self):
        cut = github_helpers.reset_index

        cut('test_search')

        actual = es_client.test_search._mapping.get().json()['test_search']['mappings'].keys()
        actual.sort()
        schema_keys = schemas.test_search['mappings'].keys()
        schema_keys.sort()
        self.assertEqual(actual, schema_keys)

    def test_expect_destroys_existing_index(self):
        cut = github_helpers.reset_index

        cut('test_search')
        es_client.test_search.test_type.test_item.put(data={'hello': 'world'})

        cut('test_search')

        actual = es_client.test_search.test_type.test_item.get()
        self.assertGreater(actual.status_code, 400)

class TestDeleteRepoType(unittest.TestCase):
    def setUp(self):
        github_helpers.reset_index('test_search')

    def test_expect_delete_all_repo_docs(self):
        es_client.test_search.wiki.test1.put(data={'path':'/a/b', 'title': 'test1'})

        cut = github_helpers.delete_repo_type
        cut('/a/b', 'wiki')

        actual = es_client.test_search.wiki.test1.get()
        self.assertGreater(actual.status_code, 400)

    def test_expect_not_delete_docs_in_other_repo(self):
        es_client.test_search.wiki.test1.put(data={'path':'/a/c', 'title': 'test1'})

        cut = github_helpers.delete_repo_type
        cut('/a/b', 'wiki')

        actual = es_client.test_search.wiki.test1.get()
        self.assertEqual(actual.status_code, 200)

    def test_expect_not_delete_docs_of_other_type(self):
        es_client.test_search.readme.test1.put(data={'path':'/a/b', 'title': 'test1'})

        cut = github_helpers.delete_repo_type
        cut('/a/b', 'wiki')

        actual = es_client.test_search.readme.test1.get()
        self.assertEqual(actual.status_code, 200)

class TestSaveIndexedVersion(unittest.TestCase):
    def setUp(self):
        github_helpers.reset_index('test_history')

    def test_expect_create_doc_with_new_verison_if_not_exist(self):
        repo_name = '/a/b'
        escaped_repo_name = repo_name.replace('/', '%2F')
        cut = github_helpers.save_indexed_version

        cut(repo_name, 'wiki', 'xxx')

        actual = github_helpers.history_client.wiki._(escaped_repo_name).get()
        print actual.json()