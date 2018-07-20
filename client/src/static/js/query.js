regexes = {
    type: /type:(issue|readme|wiki|gh_page)(,issue|,readme|,wiki|,gh_page)*\s*/i,
    source: /source:(github enterprise|github|jira)(,github enterprise|,github|,jira)*\s*/i,
    author: /author:(\S+)\s*/i,
    assignee: /assignee:(\S+)\s*/i,
    from: /from:(\d\d+-\d\d\d\d)\s*/i,
    to: /to:(\d\d+-\d\d\d\d)\s*/i,
    path: /path:(\S+)\s*/i,
};

strip_regex = /^\s*(.*?)\s*$/;
strip = function(s) {
    return strip_regex.exec(s)[1];
};

process_query = function(raw_query) {
    // given a search query string, return a query object with all the filters
    var processed_query = {
        query: raw_query || '',
    };
 
    for (var keyword in regexes) {
        var regex = regexes[keyword];
        var match = regex.exec(processed_query.query);
        if (match) {
            var value = strip(match[0].split(':').slice(1).join(':'));
            if (['source', 'author', 'assignee', 'path', 'type'].indexOf(keyword) >= 0) {
                value = value.split(',');
            } else if (['to', 'from'].indexOf(keyword) >= 0) {
                value = value.split('-');
            }
            processed_query[keyword] = value;
            processed_query.query = processed_query.query.replace(regex, '');
        }
    }
    processed_query.query = processed_query.query.replace(/^\s+|\s+$/g,'');
    return processed_query;
};

build_query = function(processed_query) {
    // given a query object, return a query string
    query = processed_query.query || '';
    for (var keyword in processed_query) {
        if (keyword == 'query') {continue;}
        var value = processed_query[keyword];
        if (!value || (value instanceof Array && !value.length)) {continue;}
        if (['source', 'author', 'assignee', 'path', 'type'].indexOf(keyword) >= 0) {
            value = value.join(',');
        } else if (['to', 'from'].indexOf(keyword) >= 0) {
            value = value.join('-');
        }
        query += ' ' + keyword + ':' + value;
    }
    return strip(query);
};

function buildESQuery(queryObj) {
    // takes in a query object and returns an ElasticSearch query
    function hasFilters(queryObj) {
        if (Object.keys(queryObj).length > 1) {
            return true;
        }
        else if (Object.keys(queryObj).length == 1 &&
                 Object.keys(queryObj)[0] != 'query') {
            return true;
        }
        else {
            return false;
        }
    }
    function hasQuery(queryObj) {
        if (queryObj.query && queryObj.query.length > 0) {
         return true;
        }
        else {
            return false;
        }
    }
    function buildTermOr(esFieldName, qFieldName) {
        var orTemp = { "or": []};
        var qField = queryObj[qFieldName || esFieldName];
        for (var i=0; i < qField.length; i++) {
            var singleTemp = {"term": {}};
            singleTemp.term[esFieldName] = qField[i];
            orTemp.or.push(singleTemp);
        }
        return orTemp;
    }
    
    var esQuery = {
      "_source": true,
      "query": {
        "bool": {
          "must": {
          },
          "filter": {
          }
        }
      }
    };
    
    if (hasQuery(queryObj)) {
        esQuery.query.bool.must =  {
            "match": {
              "_all": queryObj.query
                }
              };
        esQuery.stored_fields = ['url', 'path', 'title', 'author', 'assignee', 'source'];
        esQuery.highlight = {
            "pre_tags": [
              "<mark>"
            ],
            "post_tags": [
              "</mark>"
            ],
            "fields": {
              "content": {},
              "title": {
                "number_of_fragments": 0
              }
            }
          };
    }

    if (hasFilters(queryObj)) {
        esQuery.query.filtered.filter = {"and": []};
    
        if (queryObj.from || queryObj.to) {
            var dateTemp = {
                "range": {
                    "updated_date": {
                    }
                }
            };
            if (queryObj.from) {
                dateTemp.range.updated_date.gte = queryObj.from[1] + "-" + queryObj.from[0];
            }
            if (queryObj.to) {
                // Add 1 to the higher bounded month so the result set
                // includes results from that month
                var monthFixed = (parseInt(queryObj.to[0], 10) + 1).toString();
                dateTemp.range.updated_date.lt = queryObj.to[1] + "-" + monthFixed;
            }
            esQuery.query.filtered.filter.and.push(dateTemp);
        }
        
        if (queryObj.type) {
            var typesTemp = { "or": []};
            for (var i=0; i < queryObj.type.length; i++) {
                var indTypeTemp = {
                    "type" : {
                        "value" : queryObj.type[i]
                    }
                };
                typesTemp.or.push(indTypeTemp);
            }
            esQuery.query.filtered.filter.and.push(typesTemp);
        }
        if (queryObj.source) {
            sourcesTemp = buildTermOr("source");
            esQuery.query.filtered.filter.and.push(sourcesTemp);
        }
        if (queryObj.author) {
            authorsTemp = buildTermOr("author");
            esQuery.query.filtered.filter.and.push(authorsTemp);
        }
        if (queryObj.assignee) {
            assigneesTemp = buildTermOr("assignee");
            esQuery.query.filtered.filter.and.push(assigneesTemp);
        }
        if (queryObj.path) {
            pathsTemp = buildTermOr("path_analyzed", "path");
            esQuery.query.filtered.filter.and.push(pathsTemp);
        }
    }

    
    return esQuery;
}


_set_source = function(sources) {
    ['github enterprise', 'github', 'jira'].forEach(function(source) {
        if (sources.indexOf(source) >= 0) {
            $('[value="' + source + '"]').prop('checked', true).parent('.form-group_item').addClass('is-checked');
        } else {
            $('[value="' + source + '"]').prop('checked', false).parent('.form-group_item').removeClass('is-checked');
        }
    });
};

_set_type = function(types) {
    ['issue', 'readme', 'wiki', 'gh_page'].forEach(function(type) {
        if (types.indexOf(type) >= 0) {
            $('[value="' + type + '"]').prop('checked', true).parent('.form-group_item').addClass('is-checked');
        } else {
            $('[value="' + type + '"]').prop('checked', false).parent('.form-group_item').removeClass('is-checked');
        }
    });
};

_set_author = function(author) {
    $('[name=filter_author]').val(author.join(','));
};

_set_assignee = function(assignee) {
    $('[name=filter_assignee]').val(assignee.join(','));
};

_set_path = function(path) {
    $('[name=filter_path]').val(path.join(','));
};

_set_date = function(name) {
    return function(date) {
        $('[name=filter_' + name + '-year]').val(date[1]);
        $('[name=filter_' + name + '-year]').siblings('.custom-select_text').text($('[name=filter_' + name + '-year] :selected').text());
        $('[name=filter_' + name + '-month]').val(date[0]);
        $('[name=filter_' + name + '-month]').siblings('.custom-select_text').text($('[name=filter_' + name + '-month] :selected').text());
    };
};

setters = {
    type: _set_type,
    source: _set_source,
    author: _set_author,
    assignee: _set_assignee,
    from: _set_date('from'),
    to: _set_date('to'),
    path: _set_path,
};

set_filters = function(query_obj) {
    // given a query object (generated by process_query), set the filters form
    for (var key in query_obj) {
        if (key == 'query') {continue;}
        var value = query_obj[key];
        setters[key](value);
    }
};

_get_source = function() {
    var $els = $('[name=filter_source]');
    var sources = [];
    for (var i=0; i<$els.length; i++) {
        $el = $($els[i]);
        if ($el.prop('checked')) {
            sources.push($el.val());
        }
    }
    return sources;
};

_get_type = function() {
    var $els = $('[name=filter_type]');
    var types = [];
    for (var i=0; i<$els.length; i++) {
        $el = $($els[i]);
        if ($el.prop('checked')) {
            types.push($el.val());
        }
    }
    return types;
};

_get_author = function() {
    var author = $('[name=filter_author]').val();
    return (author) ? author.split(',') : [];
};

_get_path = function() {
    var path = $('[name=filter_path]').val();
    return (path) ? path.split(',') : [];
};

_get_assignee = function() {
    var assignee = $('[name=filter_assignee]').val();
    return (assignee) ? assignee.split(',') : [];
};

_get_date = function(name) {
    var month = $('[name=filter_' + name + '-month]').val();
    var year = $('[name=filter_' + name + '-year]').val();
    var date = [];
    if (month && year) {
        date = [month, year];
    }
    return date;
};

get_filters = function() {
    // get a query object from the current filter state
    var filters = {
        source: _get_source(),
        type: _get_type(),
        author: _get_author(),
        assignee: _get_assignee(),
        from: _get_date('from'),
        to: _get_date('to'),
        path: _get_path(),
    };
    return filters;
};

get_hash = function() {
    // get the hash of the form `#/?a=b&c=d` and parse it into an object
    // {a: 'b', c: 'd'}
    var params = {};
    var hash = window.location.hash.slice(3);
    var processed_hash = hash.split('&');
    for (var i=0; i<processed_hash.length; i++) {
        var param = processed_hash[i].split('=');
        var k = decodeURIComponent(param[0]);
        var v = decodeURIComponent(param[1]);
        params[k] = v;
    }
    return params;
};

make_hash = function(obj) {
    // given an object, serialize it to a hash string and return the hash string
    var params = [];
    for (var k in obj) {
        v = obj[k];
        params.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
    }
    var hash = '#/?' + params.join('&');
    return hash;
};

set_hash = function(obj) {
    // given an object, serialize it to a hash string and insert it into hash.
    var hash = make_hash(obj);
    window.location.hash = hash;
};
