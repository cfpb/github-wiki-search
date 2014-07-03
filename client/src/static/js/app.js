/* ==========================================================================
   github-wiki-search
   ========================================================================== */

ac_test_data = {"took":3,"timed_out":false,"_shards":{"total":5,"successful":5,"failed":0},"hits":{"total":2,"max_score":1.0,"hits":[{"_index":"autocomplete","_type":"user","_id":"dgreisen","_score":1.0, "_source" : {"owner": "dgreisen", "count": 2}},{"_index":"autocomplete","_type":"repo","_id":"dgreisen%2Fgithub-search","_score":1.0, "_source" : {"owner": "dgreisen", "repo": "github-search", "count": 2}}]}};

var repoIdent = '/';
var ownerIdent = '@';

var currentSearchTerm = '';
var currentRepoTerm = null;
var currentOwnerOwnly = null;

var queryLocation = '/search/wiki/page/_search';
var suggestRepoLocation = '/search/autocomplete/repo/_search';
var suggestOwnerLocation = '/search/autocomplete/user/_search';
var suggestionOwnerRepoLocation = '/search/autocomplete/_search';
var queryResults = [];
var busy = false;
var query_from = 0;
var filteredQuery = {
  "filtered": {
    "filter": {
      "term": {
        "repo.path": "[/<owner>[/<repo>]]"
      }
    },
    "query": {
      "match": {
        "_all": "<query>"
      }
    }
  }
};

var allQuery = {
      "match": {
        "_all": "<query>"
      }
};

var queryData = {
  "fields": ["url", "repo", "title"],
  "from": 0,
  "query": {},
  "highlight": {
    "pre_tags" : [ "<mark>" ],
    "post_tags" : [ "</mark>" ],
    "fields": {
      "content": {},
      "title": {
        "number_of_fragments": 0
      }
    }
  }
};

// when only looking for an owner
var suggestOwnerQuery = {
  "size": 5,
  "filter": {
    "term": {
      "owner": "<owner>"
    }
  }
};

// when looking for a specific owner/repo combination
var suggestRepoQuery = {
  "size": 5,
  "filter": {
    "bool": {
      "must": [
        {"term": {"owner": "<owner>"}},
        {"term": {"repo": "<repo>"}}
      ]
    }
  }
};

// when don't know whether the entered value is owner or repo
var suggestOwnerRepoQuery = {
  "size": 5,
  "filter": {
    "bool": {
      "should": [
        {"term": {"owner": "<owner>"}},
        {"term": {"repo": "<repo>"}}
      ]
    }
  }
};

var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var $more_btn = $('.results_search-more');

// Kick things off
$(function() {
  $("#mega-search-bar_query").focus();

  function autocomplete(query, cb) {
    // manage autocomplete for owners and repos
    var terms = extractRepoOwner(query);
    var searchTerm = terms[0];
    var repoTerm = terms[1];
    var ownerOwnly = terms[2];
    
    window.location.hash = encodeURIComponent(query);
    query_from = 0;
    
    if (repoTerm && (repoTerm != currentRepoTerm || ownerOwnly != currentOwnerOwnly)) {
      currentRepoTerm = repoTerm;
      currentOwnerOwnly = ownerOwnly;
      if (repoTerm.length < 3) { return cb([]); }
        // return getSuggestions(repoTerm, ownerOwnly, cb);
        return cb(ac_test_data.hits.hits);
    } else {
      sendQuery();
      return cb([]);
    }
  }

  function getSuggestions(repoTerm, ownerOwnly, cb) {
    // call cb with suggestions returned by ES given a repoTerm (owner or owner/repo)
    // and whether to only return owners, not repos.
    repoTerm = repoTerm.split('/');
    var suggestQuery;
    var suggestLocation = (ownerOwnly) ? suggestOwnerLocation : suggestRepoLocation;
    if (ownerOwnly) {
      suggestLocation = suggestOwnerLocation;
      suggestQuery = suggestOwnerQuery;
      suggestQuery.filter.term.owner = repoTerm[0];
    } else if (repoTerm.length == 1) {
      suggestLocation = suggestionOwnerRepoLocation;
      suggestQuery = suggestOwnerRepoQuery;
      suggestQuery.filter.bool.should[0].term.owner = repoTerm[0];
      suggestQuery.filter.bool.should[1].term.repo = repoTerm[0];
    } else {
      suggestLocation = suggestRepoLocation;
      suggestQuery = suggestRepoQuery;
      suggestQuery.filter.bool.must[0].term.owner = repoTerm[0];
      suggestQuery.filter.bool.must[1].term.repo = repoTerm[1];
    }
    console.log(JSON.stringify(suggestQuery));
    $.ajax(suggestLocation, {type: "POST", data: JSON.stringify(suggestQuery), success: function(data) {cb(data.hits.hits);}, dataType: 'json', contentType: "application/json"});

  }
  $("#typeaheadField").on('focus', $("#typeaheadField").typeahead.bind($("#typeaheadField"), 'lookup'));
  $megaSearchBar_query.typeahead(
    {
      minLength: 0,
      highlight: true,
    },
    {
      name: 'my-dataset',
      source: autocomplete,
      displayKey: function(obj) {
        var val = $megaSearchBar_query.typeahead('val');
        terms = extractRepoOwner(val);
        var query = terms[0].split(' ');
        query.splice(terms[3], 0, ((terms[2]) ? ownerIdent : repoIdent) + decodeURIComponent(obj._id));
        // insert the completed data into the surrounding non-completed data
        return query.join(' ');
        },
    }
  ).on('typeahead:autocompleted', function() {
    sendQuery();
  });

  $(window).hashchange( function(){
    var query = decodeURIComponent(window.location.hash.substring(1));
    if (query != currentSearchTerm) {
      $megaSearchBar_query.eq(0).val(query).trigger('input');
    }
  }).hashchange();

  sendQuery();

  $more_btn
    .click(function() {
      if (busy) {
        return false;
      }
      query_from += 10;
      sendQuery();
      return false;
    });
});

function sendQuery() {
    var val = $megaSearchBar_query.typeahead('val');
    var terms = extractRepoOwner(val);
    var searchTerm = terms[0];
    var repoTerm = terms[1];
    var ownerOwnly = terms[2];

  // Make a query if the input is not empty or the same
  if (searchTerm === '') {
    $results.slideUp('fast');
  } else {
    busy = true;
    // Update the query object
    if (repoTerm) {
      filteredQuery.filtered.filter.term['repo.path'] = '/' + repoTerm;
      filteredQuery.filtered.query.match._all = searchTerm;
      queryData.query = filteredQuery;
    } else {
      allQuery.match._all = searchTerm;
      queryData.query = allQuery;
    }
    queryData.from = query_from;
    console.log(JSON.stringify(queryData));
    $.ajax(queryLocation, {type: "POST", data: JSON.stringify(queryData), success: querySuccess, dataType: 'json', contentType: "application/json", searchTerm: currentSearchTerm, from: query_from});
  }

}

function querySuccess(data, status, xhr) {
  var from = this.from;

  // don't do anything if someone hit the more button and then changed the query before more came back
  if (this.from && this.searchTerm != currentSearchTerm) {
    busy=false;
    return;
  }

  var raw_results = data.hits.hits;

  var results = $.map(raw_results, cleanResult);

  if (!this.from) {
    $results_list.html('');
  }

  $more_btn.toggle(this.from + 10 < data.hits.total);
  appendSearchResultsHTML(results);
  busy=false;
}

// cleans a single response item
function cleanResult(rawResult) {


  var cleanedData = {
    url: '',
    repo: '',
    title: '',
    content: '',
  };


  var fields = rawResult.fields;
  if (fields) {
    $.extend(cleanedData, {
      url: fields.url[0],
      repo: fields.repo[0],
      title: fields.title[0]
    });
  }

  var highlight = rawResult.highlight;
  if (highlight && highlight.title) {
    cleanedData.title = highlight.title[0];
  }
  if (highlight && highlight.content) {
    cleanedData.content = highlight.content[0];
  }

  return cleanedData;

}


function appendSearchResultsHTML(items) {
  // Then add the new ones
  if (items.length > 0) {
    $.each(items, makeSearchResultItem);

    $results.slideDown('fast');

  } else {

    $results.slideUp('fast');

  }

}


function makeSearchResultItem(index, item) {

  // Only include content if it is not empty.
  var content = '';
  if (item.content !== '') {
    content = '<span class="results_item_highlight">' + item.content + '</span>';
  }

  return $('<li>')
    .append('' +
      '<a class="results_item" href="' + item.url + '">' +
        '<span class="cf-icon cf-icon-document results_item_icon"></span> ' +
        '<span class="results_item_repo">' + item.repo + '</span>' +
        '<span class="results_item_title">' + item.title + '</span> ' +
        content +
      '</a>')
    .appendTo($results_list);

}

function extractRepoOwner(qs) {
  // extract the repo or owner from the query string qs.

  var tokens = qs.split(' ');

  var new_qs = [];
  var new_repo_qs = null;
  var new_owner_qs = null;
  var new_owner_only = null;
  var insert_index = -1;

  for (var i=0; i<tokens.length; i++) {
    var token = tokens[i];
    var remainder_tokens = tokens.slice(i+1);
    if (token.indexOf(repoIdent) === 0) {
      new_repo_qs = token.slice(repoIdent.length);
      new_qs = new_qs.concat(remainder_tokens);
      insert_index = i;
      new_owner_only = false;
      break;
    } else if (token.indexOf(ownerIdent) === 0) {
      new_repo_qs = token.slice(repoIdent.length);
      new_qs = new_qs.concat(remainder_tokens);
      insert_index = i;
      new_owner_only = true;
      break;
    } else {
      new_qs.push(token);
    }
  }
  return [new_qs.join(' '), new_repo_qs, new_owner_only, insert_index];
}
