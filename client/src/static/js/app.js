var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var searchButton = $('#query_search');
var filterButton = $('#query_filter');
var $more_btn = $('.results_search-more');

var source = $("#results-template").html();
var template = Handlebars.compile(source);

searchButton.click(function () {
    var query = $megaSearchBar_query.val();
    console.log(query);
    set_hash({query: query});
    event.stopPropagation();
    event.preventDefault();
});


filterButton.click(function() {
    console.log('filter button');
    event.stopPropagation();
    event.preventDefault();
});

$(window).hashchange(function () {
    var hash = get_hash();
    $megaSearchBar_query.val(hash.query);
    var query = process_query(hash.query);
    console.log(query);
    sendQuery();
}).hashchange();

$more_btn
    .click(function () {
        if (busy) {
            return false;
        }
      
        query_from += 10;
        sendQuery();
        return false;
    });


function sendQuery() {
    var searchTerm = $megaSearchBar_query.val();
    if (searchTerm === '') {
        $results.slideUp('fast');
    } else {
        allQuery.match._all = searchTerm;

        queryData.query = allQuery;

        queryData.from = query_from;

        $.ajax(queryLocation, {
            type: "POST",
            data: JSON.stringify(queryData),
            success: querySuccess,
            dataType: 'json',
            contentType: "application/json",
            searchTerm: searchTerm,
            from: query_from
        });
    }

}

function querySuccess(data, status, xhr) {
    var from = this.from;

    $('#results').html('');

    // don't do anything if someone hit the more button and then changed the query before more came back
    if (this.from && this.searchTerm != $megaSearchBar_query.typeahead('val')) {
        busy = false;
        return;
    }

    var raw_results = data.hits.hits;

    var results = $.map(raw_results, cleanResult);
    searchResults['hits'] = results;
    searchResults['searchMore'] = data.hits.total > 10;

    $("#results").append(template(searchResults));
    $('#results').show();

    if (!this.from) {
        $results_list.html('');
    }
    busy = false;
}

function cleanResult(rawResult) {
console.log(rawResult);
    var cleanedData = {
        url: '',
        repo: '',
        title: '',
        content: '',
        index: '',
        type: ''
    };


    var fields = rawResult.fields;

    if (fields) {
        $.extend(cleanedData, {
            url: fields.url[0],
            repo: fields.path[0],
            title: fields.title[0],
            author: fields.author ? fields.author[0] : "",
            assignee: fields.assignee ? fields.assignee[0] : "",
            index: rawResult._index,
            type: rawResult._type
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
