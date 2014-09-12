$(document).ready(function() {
    $('#signInForm a').click(function() {
        $form = $('#signInForm');
        dataArray = $form.serializeArray();

        $.each(dataArray, function(index, object) {
            if (object.value == '') {
                $('.message-div').text('用户名或密码不能为空。');
                return;
            }
            if (object.name == 'password')
                object.value = $.md5(object.value);
        });

        $('.message-div').text('');

        $.ajax({
            url      : $form.attr('action'),
            type     : 'POST',
            dataType : 'JSON',
            data     : dataArray,
            success  : function(data) {
                console.log(data);
                if (data.set_cookies != undefined) {
                    $.each(data.set_cookies, function(key, value) {
                        $.cookie(key, value, {path: '/'});
                    });
                }
                if (!data.success)
                    $('.message-div').text(data.message);
                else
                    window.location.href = data.redirect;
            },
            error    : function(jqXHR) {
                $('html').html(jqXHR.responseText);
            }
        });
    });
});
