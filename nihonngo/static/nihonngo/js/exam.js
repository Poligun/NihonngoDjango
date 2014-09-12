$(document).ready(function() {
    nextQuestion();
});

$(document).keydown(function(e) {
    var optionIndex = e.keyCode - 49;

    if (optionIndex >= 0 && optionIndex < NumberOfOptions) {
        OptionLock = true;
        answerKanaQuestion('' + optionIndex);
    }
});


function nextQuestion() {
    $.ajax({
        url      : $('#getQuestionURL').attr('value'),
        type     : 'GET',
        dataType : 'JSON',
        success  : function(data) {
            console.log(data);
            if (data.success) {
                console.log(data.message);
                $('question').attr('qid', data.question.question_id);
                switch(data.question.question_type) {
                    case 0:
                        prepareKanaQuestion(data.question);
                        break;
                }
            }
        },
        error    : function(jqXHR) {
            $('html').html(jqXHR.responseText);
        }
    });
};

function prepareKanaQuestion(question) {
    var $lefList = $('div.kana-question .left-list');
    var $rightList = $('div.kana-question .right-list');

    $rightList.find('.meaning').remove();
    $rightList.find('.kannji').html(question.kannji);
    $rightList.find('.word-classes').html(question.word_classes);
    $.each(question.meanings, function(index, meaning) {
        $('<li class="meaning">{0}. {1}</li>'.format(index + 1, meaning)).appendTo($rightList);
    });

    var familiarity = (1 - question.unfamiliarity) * 100;
    var familiarityString = '熟悉度：';

    if (familiarity >= 10) {
        while (familiarity >= 10) {
            familiarityString += '★';
            familiarity -= 10;
        }
    } else {
        familiarityString += '☆';
    }
    $rightList.find('.familiarity').html(familiarityString + ' ' + question.unfamiliarity);

    $lefList.find('.option').remove();
    $.each(question.question, function(index, element) {
        $('<li class="option"><a href="#" index={0}>{1}.{2}</a></li>'.format(index, index + 1, element))
        .appendTo($lefList)
        .find('a').click(function() {
            if (!OptionLock) {
                OptionLock = true;
                answerKanaQuestion($(this).attr('index'));
            }
        });
    });

    //记录选项个数，方便按键
    NumberOfOptions = question.question.length
    //选项锁，用以确保客户端只选取一个选项。
    OptionLock = false;
};

function findKanaOptionLi(optionIndex) {
    return $('div.kana-question .left-list a[index="{0}"]'.format(optionIndex)).parent();
};

function answerKanaQuestion(optionIndex) {
    $.ajax({
        url      : $('#answerQUestionURL').attr('value'),
        type     : 'POST',
        dataType : 'JSON',
        data     : {'question_id': $('question').attr('qid'), 'answer': optionIndex},
        success  : function(data) {
            console.log(data);
            if (data.success) {
                if (data.correct_answer == optionIndex) {
                    findKanaOptionLi(optionIndex).addClass('option-right');
                } else {
                    findKanaOptionLi(optionIndex).addClass('option-wrong');
                    findKanaOptionLi(data.correct_answer).addClass('option-right');
                }
                setTimeout(function () {
                    nextQuestion();
                }, 1000);
            } else {
                alert(data.message);
            }
        },
        error    : function(jqXHR) {
            $('html').html(jqXHR.responseText);
        }
    });
};
