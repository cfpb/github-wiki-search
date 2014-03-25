/* ==========================================================================
   github-wiki-search
   ========================================================================== */


var currentSearchTerm = '';
var queryLocation = '/search/wiki/page/_search';
var queryResults = [];

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
var $results_searchAll_term = $('#results_search-all_term');


// Kick things off
$(function() {

  $megaSearchBar_query
    .keyup(function() {

      var val = $(this).val();

      // Make a query if the input is not empty or the same
      if (val === '') {

        currentSearchTerm = '';
        $results.slideUp('fast');

      } else if (val !== currentSearchTerm) {

        currentSearchTerm = val;

        // Update the query object
        allQuery.match._all = currentSearchTerm;
        queryData.query = allQuery;
        $.ajax(queryLocation, {type: "POST", data: JSON.stringify(queryData), success: querySuccess, dataType: 'json', contentType: "application/json"});

      }

    });

});


function querySuccess(data) {
  var rawResults = data.hits.hits;

  var results = $.map(rawResults, cleanResult);

  // Display the query results in the page
  updateSearchResultsHTML($results_list, results);

  // Update the search all link
  // $results_searchAll_term.text(currentSearchTerm);

}


// Loops through all items in response and returns a cleaned version
function cleanAllResponses(response) {

  var cleanedResponse = [];

  for (var i = 0; i < response.hits.hits.length; i++) {
    cleanedResponse.push(cleanOneResponse(response.hits.hits[i]));
  }

  return cleanedResponse;

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
  // if ( rawResult._source) {

  //   if (rawResult._source.url) {
  //     cleanedData.url = rawResult._source.url;
  //   }

  //   if (rawResult._source.repo) {
  //     if (rawResult._source.repo.charAt(0) === '/') {
  //       cleanedData.repo = rawResult._source.repo.substring(1);
  //     } else {
  //       cleanedData.repo = rawResult._source.repo;
  //     }
  //   }

  //   if (rawResult._source.title) {
  //     cleanedData.title = rawResult._source.title;
  //   }

  // }

  // if (rawResult.highlight) {

  //   if (rawResult.highlight.title && rawResult.highlight.title.length > 0) {
  //     // Only take the first result in the array
  //     cleanedData.highlight.title = rawResult.highlight.title[0].replace(/<(?:.|\n)*?>/gm, '');
  //   }

  //   if (rawResult.highlight.content && rawResult.highlight.content.length > 0) {
  //     // Only take the first result in the array
  //     cleanedData.highlight.content = rawResult.highlight.content[0].replace(/<(?:.|\n)*?>/gm, '');
  //   }

  // }

  // console.log(rawResult);
  // console.log(cleanedData);
  return cleanedData;

}


function updateSearchResultsHTML(ul, items) {

  // First clear the current results
  ul.html('');

  // Then add the new ones
  if (items.length > 0) {

    for (var i = 0; i < items.length; i++) {
      makeSearchResultItem($results_list, items[i]);
    }

    $results.slideDown('fast');

  } else {

    $results.slideUp('fast');

  }

}


function makeSearchResultItem(ul, item) {

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
    .appendTo(ul);

}