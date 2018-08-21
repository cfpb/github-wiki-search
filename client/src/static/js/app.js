var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var searchButton = $('#query_search');
var filterButton = $('#query_filter');

var source = $("#results-template").html();
var template = Handlebars.compile(source);

// from http://stackoverflow.com/questions/4801655/how-to-go-to-a-specific-element-on-page
(function($) {
    $.fn.goTo = function() {
        $('html, body').animate({
            scrollTop: $(this).offset().top + 'px'
        }, 'fast');
        return this; // for chaining...
    };
})(jQuery);
// end from http://stackoverflow.com/questions/4801655/how-to-go-to-a-specific-element-on-page

searchButton.click(function () {
    var query = $megaSearchBar_query.val();
    set_hash({query: query});
    event.stopPropagation();
    event.preventDefault();
});


filterButton.click(function() {
    event.stopPropagation();
    event.preventDefault();
    var current_query = process_query($megaSearchBar_query.val()).query;
    var new_query_obj = get_filters();
    new_query_obj.query = current_query;
    var new_query = build_query(new_query_obj);
    set_hash({query: new_query});
});

$(window).hashchange(function () {
    var hash = get_hash();
    $megaSearchBar_query.val(hash.query);
    var query = process_query(hash.query);
    set_filters(query);
    if (!query.query) {
        return;
    }
    sendQuery();
}).hashchange();

handleNextBtnClick = function () {
    $results.goTo();
};


function sendQuery() {
    var hash = get_hash();
    var query = process_query(hash.query);
    var page = parseInt(hash.page, 10) || 0;
    var queryFrom = page * 10;

    if (!query.query) {
        $results.slideUp('fast');
    } else {

        var queryData = buildESQuery(query);
        queryData.from = queryFrom;
        
        $.ajax('/search/search/_search', {
            type: "POST",
            data: JSON.stringify(queryData),
            success: querySuccess,
            dataType: 'json',
            contentType: "application/json",
        });
    }
}

function querySuccess(data, status, xhr) {
    var hash = get_hash();
    var page = parseInt(hash.page, 10) || 0;

    $('#results').html('');

    var raw_results = data.hits.hits;
    var results = $.map(raw_results, cleanResult);

    var searchResults = {};
    searchResults.hits = results;
    if (data.hits.total >= (page + 1) * 10) {
        hash.page = page + 1;
        searchResults.nextUrl = make_hash(hash);
    }
    if (page > 0) {
        hash.page = page - 1;
        searchResults.prevUrl = make_hash(hash);
    }

    $("#results").html(template(searchResults));
    $('.results_search-next').click(handleNextBtnClick);
    $('#results').show();
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

    var fields = rawResult._source;
    if (fields) {
        $.extend(cleanedData, {
            url: fields.url,
            path: fields.path,
            title: fields.title,
            author: fields.author ? fields.author : "",
            assignee: fields.assignee ? fields.assignee : "",
            source: fields.source,
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
