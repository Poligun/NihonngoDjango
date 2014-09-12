from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from nihonngo.models import User, SignInToken
from nihonngo.models import Word, WordClass, Meaning, Example, Question, LearnedWord, UpdateHistory
from nihonngo.extract import WordExtractor

import random, hashlib, json, re, inspect
from datetime import date, datetime, timedelta

"""
    API Module 里提供的 API 封装了对 Models 的操作，View 层不应越过此层直接操作 Models。
    API 的函数前缀为 api_ ，私有函数的前缀为 p_ ，剩余部分为动宾短语，名词以单数形式。
    API 的函数使用 transaction 保证其原子性，出错时会直接抛出 Exception。
    APIException 的错误描述具有安全性，而 API 函数抛出的其他类型的 Exception 则可能暴露
    数据库信息。因此在调用 API 时应该仅输出 APIException 的描述信息，对于其他 Exception
    则简单描述为调用失败。
"""

class APIException(Exception):
    def __init__(self, value):
        self.caller_api = inspect.stack()[2][3]
        self.value = value

    def __str__(self):
        return repr(self.value)

    @property
    def debug_message(self):
        return '在 {0} 中：{1}'.format(self.caller_api, self.value)
    

class InvalidArgumentException(APIException):
    pass


# MARK - Content Filter and Validator

def p_caller_name(stack_index = 2):
    return inspect.stack()[stack_index][3]

def p_validate_argument(*args, allow_blank = False):
    """
    校验参数的合法性，在不合法时抛出 InvalidArgumentException。
        参数：
            *args  个数应为3的倍数，每组参数的形式为 (name, value, type）。
    """
    assert len(args) % 3 == 0, 'p_validate_argument 函数的变参数个数必须为3的倍数。'
    while len(args) > 0:
        assert type(args[0]) is str, '{0} 不是 str 类型。'.format(args[0])
        if not isinstance(args[1], args[2]):
            raise InvalidArgumentException('参数 {0} 不是 {1} 类型。其类型为：{2}'.format(args[0], args[2], type(args[1])))
        if not allow_blank:
            if isinstance(args[1], str) and args[1] == '':
                raise InvalidArgumentException('参数 {0} 不能为空。其值为：{1}'.format(args[0], args[1]))
        args = args[3:]

def p_validate_dictionary(name, dictionary, *args):
    """
    校验字典实例的合法性，在不合法时抛出 InvalidArgumentException。
        参数：
            name        字典的名称，用于报错；
            dictionary  待校验的字典实例；
            *args       个数为3的倍数，每组参数的形式为（key, type, allow_blank）。
    """
    if not isinstance(dictionary, dict):
        raise InvalidArgumentException('{1} 不是 dict 类型。'.format(p_caller_name, name))
    assert len(args) % 3 == 0, 'p_validate_dictionary 函数的变参数个数必须为3的倍数。'
    while len(args) > 0:
        assert type(args[2]) is bool, '{0} 不是 bool 类型。'.format(args[2])
        if args[0] not in dictionary:
            raise InvalidArgumentException('{0} 不在字典 {1} 中。'.format(args[0], name))
        key, value = args[0], dictionary[args[0]]
        if not isinstance(value, args[1]):
            raise InvalidArgumentException('键 {0} 的值不是 {1} 类型。其值为：{2}'.format(key, args[1], value))
        if not args[2]:
            if isinstance(value, str) and value == '':
                raise InvalidArgumentException('字符串类型的键 {0} 的值不能为空。'.format(key))
            if (isinstance(value, list) or isinstance(value, tuple)) and len(value) == 0:
                raise InvalidArgumentException('序列类型的的键 {0} 的值不能为空。'.format(key))
            if isinstance(value, dict) and len(value == 0):
                raise InvalidArgumentException('字典类型的的键 {0} 的值不能为空。'.format(key))
        args = args[3:]


def p_remove_invalid_characters(string):
    #TO-DO: Complete this function
    return re.sub('[a-zA-Z0-9\ \t\n\r]+', '', string)

def p_filter_kannji(kannji):
    """
    过滤汉字 kannji 的方法。
    """
    return p_remove_invalid_characters(kannji)

def p_filter_kana(kana):
    """
    过滤假名 kana 的方法。
    """
    return p_remove_invalid_characters(kana)

def p_filter_meaning(meaning):
    """
    过滤释义 meaning 的方法。
    """
    #TO-DO: Implement this function
    return meaning

def p_filter_example(example):
    """
    过滤释义 example 的方法。
    """
    #TO-DO: Implement this function
    return example

def p_validate_word_class(word_class):
    """
    判断 word_class 是否合法
    """
    return word_class in WordClass.WORD_CLASS_DICTIONARY


# MARK - API for Authentication

"""
    所有的认证 API 的前缀均为 api_auth_ ，暂不开放创建和删除功能。
"""

def api_auth_sign_in(name, password):
    """
    以用户名、密码的形式进行认证。
        参数：
            name      用户名；
            password  密码。
        返回值：
            通过认证的用户的 User 实例。
    """
    p_validate_argument('name', name, str, 'password', password, str)
    users = User.objects.filter(name = name, password = password)
    if len(users) != 1:
        raise APIException('用户名或密码错误。')
    return users[0]

def api_auth_get_user(user_id):
    """
    根据 user_id 来获取对应的 User 实例。
        参数：
            user_id  用户的 ID。
        返回值：
            user_id 所对应的用户的 User 实例。
    """
    p_validate_argument('user_id', user_id, int)

    users = User.objects.filter(id = user_id)
    if len(users) != 1:
        raise APIException('不存在的用户。')
    else:
        return users[0]

def api_auth_create_token(user_id, expire_delta = timedelta(weeks = 2)):
    """
    新建一个自动认证令牌。
        参数：
            user_id  用户的 ID。
        返回值：
            创建的自动认证令牌的 SignInToken 实例。
    """
    p_validate_argument('user_id', user_id, int, 'expire_delta', expire_delta, timedelta)

    user = api_auth_get_user(user_id)
    token_string = "{0}{1}{2}".format(user.name, random.uniform(0, 1), timezone.now())
    token = hashlib.sha1(token_string.encode('utf-8')).hexdigest()
    expire_date = timezone.now() + expire_delta

    new_token = SignInToken(user_id = user.id, token = token, expire_date = expire_date)
    new_token.save()
    return new_token

def api_auth_validate_token(token):
    """
    认证令牌。
        参数：
            token  自动认证令牌的值。
        返回值：
            通过认证的对应的 SignInToken 实例。
    """
    p_validate_argument('token', token, str)

    tokens = SignInToken.objects.filter(token = token)
    if len(tokens) != 1:
        raise APIException('不存在的令牌。')
    with tokens[0] as token:
        if token.expired:
            raise APIException('令牌已失效。')
        if token.expire_date <= timezone.now():
            raise APIException('令牌已过期。')
        return token

def api_auth_mark_token_expired(token_id):
    """
    标记令牌为失效。
        参数：
            token_id  自动认证令牌的 ID。
        返回值：
            无。
    """
    p_validate_argument('token_id', token_id, int)

    tokens = SignInToken.objects.filter(id = token_id)
    if len(tokens) != 1:
        raise APIException('不存在的令牌。')
    with tokens[0] as token:
        if token.expired:
            raise APIException('该令牌已经失效。')
        token.expired = True
        token.save()


# MARK - API for Models

def api_create_word(kannji, kana):
    """
    中新建一个生词。
        参数：
            kannji  生词的汉字；
            kana    生词的假名。
        返回值：
            新建的生词的 Word 实例。
    """
    p_validate_argument('kannji', kannji, str, 'kana', kana, str)
    
    kannji, kana = p_filter_kannji(kannji), p_filter_kana(kana)
    if len(Word.objects.filter(kannji = kannji, kana = kana)) > 0:
        raise APIException('生词"{0}（{1}）"已经存在。'.format(kannji, kana))

    new_word = Word(kannji = kannji, kana = kana)
    new_word.save()
    return new_word

def api_search_word(search_string):
    """
    查询符合搜索串的生词，判断条件为：汉字或假名包含搜索串。
        参数：
            search_string  搜索串。
        返回值：
            包含符合条件的生词 list 实例。
    """
    p_validate_argument('search_string', search_string, str)
    return Word.objects.filter(Q(kannji__contains = search_string) | Q(kana__contains = search_string)).order_by('kannji')

def api_create_word_class(word_id, word_class):
    """
    新建一个词类。
        参数：
            word_id     对应生词的 ID；
            word_class  词类名。
        返回值：
            新建的词类的 WordClass 实例。
    """
    p_validate_argument('word_id', word_id, int, 'word_class', word_class, str)
    if not p_validate_word_class(word_class):
        raise APIException('"{0}" 不是合法的词类。'.format(word_class))

    new_word_class = WordClass(word_id = word_id, word_class = WordClass.WORD_CLASS_DICTIONARY[word_class])
    new_word_class.save()
    return new_word_class

def api_get_class_index(word_class):
    """
    根据词类名反查其对应的 index。
        参数：
            word_class  词类名。
        返回值：
            词类名所对应的 index。
    """
    p_validate_argument('word_class', word_class, str)

    if word_class in WordClass.WORD_CLASS_DICTIONARY:
        return WordClass.WORD_CLASS_DICTIONARY[word_class]
    else:
        raise APIException('不存在的词类名。')

def api_create_meaning(word_id, meaning):
    """
    新建一个释义。
        参数：
            word_id  对应生词的 ID；
            meaning  释义。
        返回值：
            新建的释义的 Meaning 实例。
    """
    p_validate_argument('word_id', word_id, int, 'meaning', meaning, str)
    
    meaning = p_filter_meaning(meaning)

    new_meaning = Meaning(word_id = word_id, text = meaning)
    new_meaning.save()
    return new_meaning

def api_create_example(meaning_id, example):
    """
    新建一个例子。
        参数：
            word_id  对应释义的 ID；
            example  例子。
        返回值：
            新建的例子的 Example 实例。
    """
    p_validate_argument('meaning_id', meaning_id, int, 'example', example, str)

    example = p_filter_example(example)

    new_example = Example(meaning_id = meaning_id, text = example)
    new_example.save()
    return new_example


# MARK - API for Word Lookup and Edition

def api_lookup_word(kannji):
    """
    从网络词典中查询生词的信息。
        参数：
            kannji  生词的汉字。
        返回值：
            包含查询到的所有生词的 list 实例。
    """
    p_validate_argument('kannji', kannji, str)

    try:
        extractor = WordExtractor()
        words = extractor.extract(kannji)
    except Exception as e:
        raise APIException('查询失败。')

    for word in words:
        if len(Word.objects.filter(kannji = word['kannji'], kana = word['kana'])) > 0:
            word['exists'] = True
    return words

def api_insert_new_word(word_info):
    """
    插入一个新的生词（从网络词典中查询后，经由用户编辑确认）。
        参数：
            word_info  新的生词的基本信息，一个 dict 实例。
        返回值：
            插入的生词的 Word 实例。
    """
    p_validate_dictionary('word_info', word_info,
                              'kannji'      ,  str, False,
                              'kana'        ,  str, False,
                              'word_classes', list, False,
                              'meanings'    , list, False,)

    with transaction.atomic():
        new_word = api_create_word(word_info['kannji'], word_info['kana'])
        for word_class in word_info['word_classes']:
            new_word_class = api_create_word_class(new_word.id, word_class)
        for meaning in word_info['meanings']:
            p_validate_dictionary('meaning', meaning,
                                      'text'    ,  str, False,
                                      'examples', list,  True,)
            new_meaning = api_create_meaning(new_word.id, meaning['text'])
            for example in meaning['examples']:
                new_example = api_create_example(new_meaning.id, example)

    return new_word


# MARK - API for Exam & Question

def p_lcs_length(sequence1, sequence2):
    """
    计算两个 sequence 的最长公共子序列（LCS）的长度。
        参数：
            sequence1, sequence2  两个序列。
        返回值：
            最长公共子序列的长度。
    """
    if len(sequence1) == 0 or len(sequence2) == 0: return 0
    f = {'max': 0}
    for i in range(len(sequence1)):
        for j in range(len(sequence2)):
            f[(i, j)] = 1 if sequence1[i] == sequence2[j] else 0
            if i > 0 and j > 0:
                f[(i, j)] += f[(i - 1, j - 1)]
            if i > 0 and f[(i - 1, j)] > f[(i, j)]:
                f[(i, j)] = f[(i - 1, j)]
            if j > 0 and f[(i, j - 1)] > f[(i, j)]:
                f[(i, j)] = f[(i, j - 1)]
            if f[(i, j)] > f['max']:
                f['max'] = f[(i, j)]
    return f['max']

def p_create_kana_question(word, user, num_of_options = 6):
    """
    生成一个假名测试问题。
    """
    lcs_dict = dict((w.kana, p_lcs_length(word.kana, w.kana)) for w in Word.objects.all() if w.kana != word.kana)
    kana_options = sorted(list(lcs_dict.items()), key = lambda e: (-e[1], e[0]))[:2 * num_of_options]
    options = [e[0] for e in random.sample(kana_options, num_of_options - 1)] + [word.kana]
    random.shuffle(options)

    for i in range(len(options)):
        if options[i] == word.kana:
            correct_answer = i
            break

    new_question = Question(related_word_id = word.id,
                              question_type = 0,
                                   question = json.dumps(options),
                             correct_answer = str(correct_answer),
                                    user_id = user.id)
    new_question.save()
    return new_question

QUESTION_GENERATOR_FUNCTIONS = [p_create_kana_question]

UNFAMILIARITY_COEFFICIENT = 8

def p_bound_value(value, boundary):
    """
    使 value 落入 boundary 的范围内。
        参数：
            value     待限界的值；
            boundary  界限。
        返回值：
            限界后的值。
    """
    if value < boundary[0]: value = boundary[0]
    if value > boundary[1]: value = boundary[1]
    return value

def p_calculate_unfamiliarity_with_params(time_delta, unfamiliarity, correct_answered_count):
    """
    根据给定的参数来计算不熟悉度。
        参数：
            time_delta              距离上次复习的时间；
            unfamiliarity           上次计算的不熟悉度；
            correct_answered_count  该生词的测试中回答正确次数。
        返回值：
            新计算的不熟悉度。
    """
    new_unfamiliarity = unfamiliarity + time_delta.days / (5 * (correct_answered_count + UNFAMILIARITY_COEFFICIENT))
    return p_bound_value(new_unfamiliarity, (0, 1))

def p_calculate_unfamiliarity(learned_word):
    """
    计算已学习生词的不熟悉度。
        参数：
            learned_word  已学习的生词。
        返回值：
            不熟悉程度。
    """
    time_delta = timezone.now().date() - learned_word.last_review_date
    unfamiliarity = learned_word.unfamiliarity
    correct_answered_count = learned_word.correct_answered_count
    return p_calculate_unfamiliarity_with_params(time_delta, unfamiliarity, correct_answered_count)

def p_prune_question(question):
    """
    修剪生成的问题，隐去不必要的信息。
        参数：
            question  原问题。
        返回值：
            修剪后的问题。
    """
    pruned_question = {
        'question'     : question.question,
        'question_type': question.question_type,
        'question_id'  : question.id,
    }

    if question.question_type == 0:
        pruned_question['question']     = json.loads(pruned_question['question'])
        pruned_question['kannji']       = question.related_word.kannji
        pruned_question['meanings']     = [m.text for m in question.related_word.meanings]
        pruned_question['word_classes'] = '，'.join(w.class_name for w in question.related_word.word_classes)

    return pruned_question

def api_create_question(user, new_word_prob = 0.4, unfamiliarity_threshold = 1, return_unanswered = True):
    """
    为给定的 user 生成一个新的问题，测试的形式和所测试的问题由该算法决定。
    目前的选取方法为：计算生词的修正不熟悉程度，降序排列后从前十中随机抽取。
        参数：
            user                     要生成测试的用户；
            new_word_prob            选择新单词的概率；
            unfamiliarity_threshold  不熟悉度阈值，若有生词的不熟悉度超过此值，则不会选择新词；
            return_unanswered        若设为 True，当数据库中有未回答的问题时，先返回该问题。
        返回值：
            生成的问题的 Question 实例。
    """
    p_validate_argument('user', user, User)

    if return_unanswered:
        unanswered_questions = Question.objects.filter(user_id = user.id, answered = False)
        if len(unanswered_questions) > 0:
            choosed_question = random.choice(unanswered_questions)
            try:
                unfamiliarity = p_calculate_unfamiliarity(LearnedWord.objects.get(word_id = choosed_question.related_word_id))
            except:
                unfamiliarity = 1.0
            choosed_question = p_prune_question(choosed_question)
            choosed_question['unfamiliarity'] = unfamiliarity
            return choosed_question

    try:
        latest_history = UpdateHistory.objects.filter(user_id = user.id).latest('update_date')
        time_delta = timezone.now() - latest_history.update_date
        needs_update = True if time_delta.days > 0 else False
    except:
        needs_update = True

    if needs_update:
        with transaction.atomic():
            for learned_word in LearnedWord.objects.filter(user_id = user.id):
                learned_word.unfamiliarity = p_calculate_unfamiliarity(learned_word)
                learned_word.save()
            new_update_history = UpdateHistory(user_id = user.id)
            new_update_history.save()

    learned_words = LearnedWord.objects.filter(user_id = user.id).order_by('-unfamiliarity')
    if len(learned_words) == 0:
        choose_new = True
    else:
        average_unfamiliarity = sum(learned_word.unfamiliarity for learned_word in learned_words) / len(learned_words)
        if average_unfamiliarity >= unfamiliarity_threshold:
            choose_new = False
        else:
            choose_new = True if random.random() < new_word_prob else False

    if choose_new:
        while True:
            choosed_word = random.choice(Word.objects.all())
            if len(LearnedWord.objects.filter(user_id = user.id, word_id = choosed_word.id)) == 0:
                break
        unfamiliarity = 1.0
    else:
        choosed_entry = random.choice(learned_words.filter(unfamiliarity__gte = 0.1))
        choosed_word, unfamiliarity = choosed_entry.word, choosed_entry.unfamiliarity

    new_question = random.choice(QUESTION_GENERATOR_FUNCTIONS)(word = choosed_word, user = user)
    new_question = p_prune_question(new_question)
    new_question['unfamiliarity'] = unfamiliarity
    print('Unfamiliarity: {0}'.format(unfamiliarity))
    return new_question

def api_answer_question(user_id, question_id, answer):
    """
    提交对应问题的回答。
        参数：
            user_id      提交回答的用户的 ID；
            question_id  要回答的问题的 ID；
            answer       用户的回答。
    """
    p_validate_argument('user_id', user_id, int, 'question_id', question_id, int, 'answer', answer, str)

    questions = Question.objects.filter(id = question_id)
    if len(questions) != 1:
        raise APIException('不存在的问题。')
    question = questions[0]

    if question.user_id != user_id:
        raise APIException('该问题不属于此用户。')

    if question.answered:
        raise APIException('该问题已经被回答。')

    with transaction.atomic():
        question.answered = True
        question.answer_date = timezone.now()
        question.answer_is_correct = True if question.correct_answer == answer else False
        question.save()

        learned_words = LearnedWord.objects.filter(word_id = question.related_word_id, user_id = user_id)
        if len(learned_words) == 0:
            learned_word = LearnedWord(word_id = question.related_word_id, user_id = user_id)
            learned_word.save()
        else:
            learned_word = learned_words[0]

        learned_word.last_review_date = timezone.now().date()
        learned_word.unfamiliarity = p_calculate_unfamiliarity(learned_word)
        learned_word.total_answered_count += 1
        if question.answer_is_correct:
            learned_word.correct_answered_count += 1
            learned_word.unfamiliarity -= 1 / UNFAMILIARITY_COEFFICIENT
        else:
            learned_word.unfamiliarity += 1 / UNFAMILIARITY_COEFFICIENT
        learned_word.unfamiliarity = p_bound_value(learned_word.unfamiliarity, (0, 1))
        learned_word.save()

        return question.correct_answer

def p_recheck_leanred_words(user):
    """
    重新检查并计算给定用户的已学习生词的信息。
        参数：
            待重新检查的用户的 ID。
    """
    with transaction.atomic():
        LearnedWord.objects.all().delete()

        question_dict = {}
        for question in Question.objects.filter(user_id = user.id, answered = True):
            if question.related_word_id not in question_dict:
                question_dict[question.related_word_id] = []
            question_dict[question.related_word_id].append(question)

        for key, value in question_dict.items():
            learned_word = LearnedWord(word_id = key, user_id = user.id)
            learned_word.save()
            value.sort(key = lambda q: q.answer_date)

            unfamiliarity = 1
            learned_word.learned_date = current_date = value[0].answer_date.date()
            total_answered_count = 0
            correct_answered_count = 0

            for question in value:
                time_delta = question.answer_date.date() - current_date
                unfamiliarity = p_calculate_unfamiliarity_with_params(time_delta, unfamiliarity, correct_answered_count)
                
                total_answered_count += 1
                if question.answer_is_correct:
                    correct_answered_count += 1
                    unfamiliarity -= 1 / UNFAMILIARITY_COEFFICIENT
                else:
                    unfamiliarity += 1 / UNFAMILIARITY_COEFFICIENT

                unfamiliarity = p_bound_value(unfamiliarity, (0, 1))
                current_date = question.answer_date.date()

            learned_word.last_review_date = current_date
            learned_word.total_answered_count = total_answered_count
            learned_word.correct_answered_count = correct_answered_count
            learned_word.unfamiliarity = unfamiliarity
            learned_word.save()

# MARK - API for Statistics

def p_stat_correct_answer_probability(user):
    """
    统计用户回答问题的正确率。
        参数：
            user  待统计的用户。
        返回值：
            该用户的正确率。
    """
    p_validate_argument('user', user, User)

    return Question.objects.filter(user_id = user.id, answer_is_correct = True).count() / \
           Question.objects.filter(user_id = user.id, answered = True).count()

def p_stat_answered_question_number_today(user, date = None):
    """
    统计用户在指定日期的一天内回答的问题总数。
        参数：
            user  待统计的用户；
            date  可选，若为 None 则统计本地时间今天。
        返回值：
            该天内回答的问题总数。
    """
    p_validate_argument('user', user, User)

    start_time = datetime.combine(date if isinstance(date, datetime) else datetime.now().date(), datetime.min.time())
    end_time = start_time + timedelta(days = 1, microseconds = -1)
    start_time = start_time.utcnow().replace(tzinfo = timezone.utc)
    end_time = end_time.utcnow().replace(tzinfo = timezone.utc)
    questions = Question.objects.filter(user_id = user.id,
                                       answered = True,
                               answer_date__gte = start_time,
                               answer_date__lte = end_time)
    return len(questions)

def p_stat_number_of_answer_required_today(user, goal = 90):
    """
    粗略估算用户一天内需要回答的问题个数。
        参数：
            user  待估算的用户；
            goal  预计完成学习的天数，默认为90天。
        返回值：
            今天应回答的问题个数（假设每天回答同样个数的问题）。
    """
    p_validate_argument('user', user, User, 'goal', goal, int)

    speed = (2 * p_stat_correct_answer_probability(user) - 1) / UNFAMILIARITY_COEFFICIENT
    learned_words = LearnedWord.objects.filter(user_id = user.id)
    unfamiliarity_to_go = sum(lw.unfamiliarity for lw in learned_words) + \
                          (Word.objects.count() - learned_words.count())
    #Word.objects.count() * goal / (3 * UNFAMILIARITY_COEFFICIENT)
    return unfamiliarity_to_go / speed / goal

def p_stat_average_learned_word_familiarity(user):
    """
    """
    p_validate_argument('user', user, User)

    learned_words = LearnedWord.objects.filter(user_id = user.id)
    return sum(learned_word.unfamiliarity for learned_word in learned_words) / len(learned_words)

def api_get_statistics(user, finish_date = date(2014, 6, 20)):
    """
    获取用户相关的统计数据
    """
    return (
        ('回答正确率', p_stat_correct_answer_probability(user)),
        ('平均不熟悉度', p_stat_average_learned_word_familiarity(user)),
        ('今日回答问题数', p_stat_answered_question_number_today(user)),
        ('今日应回答问题数', p_stat_number_of_answer_required_today(user, (finish_date - timezone.now().date()).days)),
    )
