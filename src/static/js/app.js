/* ==========================================================================
   github-wiki-search
   ========================================================================== */


var currentSearchTerm = '';
var queryLocation = '/search/wiki/page/_search';
var queryResults = [];
var busy = false;

var filteredQuery = {
  "filtered": {
    "filter": {
      "term": {
        "repo": "[/<owner>[/<repo>]]"
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

var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var $more_btn = $('.results_search-more');

// Kick things off
$(function() {
  $megaSearchBar_query
    .keyup(function() {
      var val = $megaSearchBar_query.val();
      if (currentSearchTerm == val) {
        return;
      }
      currentSearchTerm = val;
      query_from = 0;
      query();
    });

  $more_btn
    .click(function() {
      if (busy) {
        return false;
      }
      query_from += 10;
      query();
      return false;
    });

});

function query() {
  // Make a query if the input is not empty or the same
  if (currentSearchTerm === '') {
    $results.slideUp('fast');
  } else {
    busy = true;
    // Update the query object
    allQuery.match._all = currentSearchTerm;
    queryData.query = allQuery;
    queryData.from = query_from;
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
        '<i class="icon-book results_item_icon"></i> ' +
        '<span class="results_item_repo">' + item.repo + '</span>' +
        '<span class="results_item_title">' + item.title + '</span> ' +
        content +
      '</a>')
    .appendTo($results_list);

}