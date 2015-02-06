var $megaSearchBar_query = $('#mega-search-bar_query');
var $results = $('#results');
var $results_list = $('#results_list');
var $more_btn = $('.results_search-more');

var source = $("#results-template").html();
var template = Handlebars.compile(source);

// Kick things off
$(function() {
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
            if (repoTerm.length < 3) {
                return cb([]);
            }
            return getSuggestions(repoTerm, ownerOwnly, cb);
            // return cb(ac_test_data.hits.hits);
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
        console.log('SUGGEST: ', JSON.stringify(suggestQuery));
        $.ajax(suggestLocation, {
            type: "POST",
            data: JSON.stringify(suggestQuery),
            success: function(data) {
                cb(data.hits.hits);
            },
            dataType: 'json',
            contentType: "application/json"
        });

    }

    $megaSearchBar_query.typeahead({
        minLength: 0,
        highlight: true,
    }, {
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
    }).on('typeahead:autocompleted', function() {
        console.log("AUTOCOMPLETE");
        sendQuery();
    }).on('typeahead:selected', function() {
        console.log("SELECTED");
        sendQuery();
    });

    $(window).hashchange(function() {
        var query = decodeURIComponent(window.location.hash.substring(1));
        if (query != $megaSearchBar_query.typeahead('val')) {
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
        console.log('QUERY:', JSON.stringify(queryData));
        $.ajax(queryLocation, {
            type: "POST",
            data: JSON.stringify(queryData),
            success: querySuccess,
            dataType: 'json',
            contentType: "application/json",
            searchTerm: $megaSearchBar_query.typeahead('val'),
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
    console.log(searchResults);

    var templated_html = template(searchResults);

    $("#results").append(template(searchResults));
    $('#results').show();

    if (!this.from) {
        $results_list.html('');
    }
    busy = false;
}

// cleans a single response item
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

function extractRepoOwner(qs) {
    // extract the repo or owner from the query string qs.

    var tokens = qs.split(' ');

    var new_qs = [];
    var new_repo_qs = null;
    var new_owner_qs = null;
    var new_owner_only = null;
    var insert_index = -1;

    for (var i = 0; i < tokens.length; i++) {
        var token = tokens[i];
        var remainder_tokens = tokens.slice(i + 1);
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