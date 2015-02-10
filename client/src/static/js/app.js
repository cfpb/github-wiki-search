var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var searchButton = $('#query_search');
var $more_btn = $('.results_search-more');

var source = $("#results-template").html();
var template = Handlebars.compile(source);

searchButton.click(function () {
    sendQuery();
    event.stopPropagation();
    event.preventDefault();

});
$megaSearchBar_query.keyup(function () {
    window.location.hash = encodeURIComponent($megaSearchBar_query.val());
    event.stopPropagation();
    event.preventDefault();
});

$(window).hashchange(function () {
    var query = decodeURIComponent(window.location.hash.substring(1));
    console.log("query:", query);
    if (query != $megaSearchBar_query.val()) {
        $megaSearchBar_query.val(query).trigger('input');
    }
}).hashchange();

$more_btn
    .click(function () {
        if (busy) {
            return false;
        }
        console.log("trigger");
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
        console.log(searchTerm);

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


    var templated_html = template(searchResults);

    $("#results").append(template(searchResults));
    $('#results').show();

    if (!this.from) {
        $results_list.html('');
    }
    busy = false;
}

function cleanResult(rawResult) {

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

