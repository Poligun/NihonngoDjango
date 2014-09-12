$(document).ready(function() {
    initAjax();
    initNavBar();
});

// Mark - Initialization Functions

function searchWord(event) {
    var url = $('.nav-search-bar url').attr('url');
    var searchString = $('.nav-search-bar input').val().replace(/\s+/g, '');


    if ('' == searchString)
        $('.nav-search-bar input').trigger('focus');
    else
        window.location.href = url.replace('search_string', searchString);
    event.preventDefault();
}

function initNavBar() {
    $('.nav-search-bar input').focus(function() {
        $(this).parent().addClass('search-bar-focus');
    }).blur(function() {
        $(this).parent().removeClass('search-bar-focus');
    }).keydown(function(e) {
        if (e.keyCode == 13)
            searchWord();
    });
    $('.nav-search-bar a').click(searchWord);
    $(document).keydown(function (e) {
        if (e.keyCode == 115) {
            $('.nav-search-bar input').trigger('focus');
        }
    });
}

function initAjax() {
    var csrftoken = $.cookie('csrftoken');
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

// Mark - String Prototype Enhancement

String.prototype.format = function() {
    var string = this;
    var index = arguments.length;

    while (index--) {
        string = string.replace(new RegExp('\\{' + index + '\\}', 'gm'), arguments[index]);
    }
    return string;
};

String.prototype.startsWith = function(string) {
    return this.indexOf(string) == 0;
};
