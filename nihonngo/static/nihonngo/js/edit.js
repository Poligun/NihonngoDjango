$(document).ready(function() {
    $('textarea.meaning-text').on('change keyup paste', resizeTextarea).each(resizeTextarea);
    $('ul.edit-entry a.submit').click(submitWord);
    $('ul.edit-entry a.exists').click(function() {
        return false;
    });
});

function resizeTextarea() {
    $(this).css('height', 'auto').height(this.scrollHeight);
};

function submitWord() {
    var $ul = $(this).parents('ul');
    var data = {};

    data.kannji = $ul.find('input[name="kannji"]').val();
    data.kana = $ul.find('input[name="kana"]').val();
    data.word_classes = $ul.find('input[name="word-classes"]').val().split('，');
    data.meanings = [];
    $.each($ul.find('textarea').val().replace(/\n+\ +/g, '*').replace(/\n+/g, '#').split('#'), function(index, entry) {
        if (entry == '') return;
        var components = entry.split('*');
        var meaning = {'text': components[0], 'examples': []};

        for (var i = 1; i < components.length; i++)
            meaning.examples.push(components[i]);

        data.meanings.push(meaning);
    });
    
    //console.log($.toJSON(data));

    $.ajax({
        url      : $('#insertWordURL').attr('value'),
        type     : 'POST',
        dataType : 'JSON',
        data     : {'word_info': $.toJSON(data)},
        success  : function(data) {
            console.log(data);
            alert(data.message);
            if (data.success)
                window.location.href = data.redirect;
        },
        error    : function(jqXHR) {
            $('html').html(jqXHR.responseText);
        }
    });

    return false;
}
