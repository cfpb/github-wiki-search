import json
import os
import copy

DIR = os.path.dirname(os.path.abspath(__file__))

typs = {
  'wiki': ['tags', 'status', 'assignee'],
  'gh_page': ['tags', 'status', 'assignee'],
  'readme': ['tags', 'status', 'assignee'],
  'issue': [],
}

def get_search_schema():
  with open(os.path.join(DIR, 'search_base.json'), 'r') as f:
    search_schema = json.load(f)

  with open(os.path.join(DIR, 'search_item.json'), 'r') as f:
    search_item = json.load(f)

  for typ, excluded_properties in typs.items():
    typ_schema = copy.deepcopy(search_item)
    for property in excluded_properties:
      del typ_schema['properties'][property]
    search_schema['mappings'][typ] = typ_schema

  return search_schema

def get_autocomplete_schema():
  with open(os.path.join(DIR, 'autocomplete.json'), 'r') as f:
    autocomplete = json.load(f)
  return autocomplete

search = test_search = get_search_schema()
autocomplete = test_autocomplete = get_autocomplete_schema()
