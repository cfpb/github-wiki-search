/* ==========================================================================
   github-wiki-search
   ========================================================================== */


var currentSearchTerm = '';
var query = 'data.json';
var queryResults = [];

var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var $results_searchAll_term = $('#results_search-all_term');


// Kick things off
$(function() {

  $megaSearchBar_query
    .keyup(function() {

      var queryString = '';
      var encodedSearchTerm;

      currentSearchTerm = $(this).val();
      encodedSearchTerm = encodeURIComponent(currentSearchTerm);

      queryString = query + '?' + encodedSearchTerm;
      // console.log(queryString);

      // Make a query if the input is not empty
      if (currentSearchTerm !== '') {
        $.getJSON(queryString, querySuccess);
      } else {
        $results.hide();
      }

    });

});


function querySuccess(data) {

  // clean the query results and save them
  queryResults = cleanAllResponses(data);

  // Display the query results in the page
  updateSearchResultsHTML($results_list, queryResults);

  // Update the search all link
  $results_searchAll_term.text(currentSearchTerm);

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
function cleanOneResponse(sourceData) {

  var cleanedData = {
    url: '',
    repo: '',
    title: '',
    highlight: {
      title: '',
      content: ''
    }
  };

  if ( sourceData._source) {

    if (sourceData._source.url) {
      cleanedData.url = sourceData._source.url;
    }

    if (sourceData._source.repo) {
      if (sourceData._source.repo.charAt(0) === '/') {
        cleanedData.repo = sourceData._source.repo.substring(1);
      } else {
        cleanedData.repo = sourceData._source.repo;
      }
    }

    if (sourceData._source.title) {
      cleanedData.title = sourceData._source.title;
    }

  }

  if (sourceData.highlight) {

    if (sourceData.highlight.title && sourceData.highlight.title.length > 0) {
      // Only take the first result in the array
      cleanedData.highlight.title = sourceData.highlight.title[0].replace(/<(?:.|\n)*?>/gm, '');
    }

    if (sourceData.highlight.content && sourceData.highlight.content.length > 0) {
      // Only take the first result in the array
      cleanedData.highlight.content = sourceData.highlight.content[0].replace(/<(?:.|\n)*?>/gm, '');
    }

  }

  // console.log(sourceData);
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

    $results.show();

  } else {

    $results.hide();

  }

}


function makeSearchResultItem(ul, item) {

  // Only include highlight.content if it is not empty.
  var highlight = '';
  if (item.highlight.content !== '') {
    highlight = '<span class="results_item_highlight">' + item.highlight.content + '</span>';
  }

  return $('<li>')
    .append('' +
      '<a class="results_item" href="' + item.url + '">' +
        '<i class="icon-book results_item_icon"></i> ' +
        '<span class="results_item_repo">' + item.repo + '</span>' +
        '<span class="results_item_title">' + item.title + '</span> ' +
        highlight +
      '</a>')
    .appendTo(ul);

}


// http://stackoverflow.com/questions/822452/strip-html-from-text-javascript

function strip(html)
{
   var tmp = document.createElement("DIV");
   tmp.innerHTML = html;
   return tmp.textContent || tmp.innerText || "";
}
