from django.db import models

class User(models.Model):
    name     = models.CharField(max_length = 10)
    password = models.CharField(max_length = 100)

    def __str__(self):
        return self.name

class SignInToken(models.Model):
    user        = models.ForeignKey(User)
    token       = models.CharField(max_length = 40)
    expired     = models.BooleanField(default = False)
    expire_date = models.DateTimeField()

    def __str__(self):
        return '{0}({1}), expire date: {2}'.format(self.user.name, self.token, self.expire_date)

class Word(models.Model):
    """"""
    kannji = models.CharField(max_length = 100)
    kana   = models.CharField(max_length = 100)

    def __str__(self):
        return '{0}({1})'.format(self.kannji, self.kana)

    @property
    def word_classes(self):
        return WordClass.objects.filter(word = self)

    def get_word_classes_display(self, separator = '，'):
        return separator.join(sorted(word_class.get_word_class_display() for word_class in self.word_classes))

    @property
    def meanings(self):
        return Meaning.objects.filter(word = self)


class WordClass(models.Model):
    """"""
    WORD_CLASSES = (
        (0, '一类动词'),
        (1, '一类形容词'),
        (2, '三类动词'),
        (3, '二类动词'),
        (4, '二类形容词'),
        (5, '他动词'),
        (6, '代词'),
        (7, '副词'),
        (8, '助词'),
        (9, '名词'),
        (10, '常用语'),
        (11, '接尾词'),
        (12, '接续词'),
        (13, '自动词'),
        (14, '补助动词'),
        (15, '语气词'),
        (16, '连体词'),
        (17, '连语'),
        (18, '量词')
    )
    WORD_CLASS_DICTIONARY = dict([(v, k) for k, v in WORD_CLASSES])


    word       = models.ForeignKey(Word)
    word_class = models.IntegerField(default = 0, choices = WORD_CLASSES)

    def __str__(self):
        return '{0}-{1}'.format(self.word, self.get_word_class_display())

    @property
    def class_name(self):
        return WordClass.WORD_CLASSES[self.word_class][1]

class Meaning(models.Model):
    """"""
    word = models.ForeignKey(Word)
    text = models.CharField(max_length = 200)

    def __str__(self):
        return '{0}-{1}'.format(self.word, self.text)

    @property
    def examples(self):
        return Example.objects.filter(meaning = self)


class Example(models.Model):
    """"""
    meaning = models.ForeignKey(Meaning)
    text    = models.CharField(max_length = 200)

    def __str__(self):
        return '{0}-{1}'.format(self.meaning.word, self.text)


class Question(models.Model):
    """"""
    QUESTION_TYPES = (
        (0, '假名测试'),
    )

    related_word      = models.ForeignKey(Word)
    question_type     = models.IntegerField(choices = QUESTION_TYPES)
    question          = models.CharField(max_length = 500)
    correct_answer    = models.CharField(max_length = 100)
    user              = models.ForeignKey(User)
    answered          = models.BooleanField(default = False)
    answer_date       = models.DateTimeField(null = True, blank = True)
    answer_is_correct = models.BooleanField(default = False)

    def __str__(self):
        return '{0}({1})-{2}'.format(self.get_question_type_display(), self.user.name, self.question)


class LearnedWord(models.Model):
    """"""
    word                   = models.ForeignKey(Word)
    user                   = models.ForeignKey(User)
    learned_date           = models.DateField(auto_now_add = True)
    last_review_date       = models.DateField(auto_now_add = True)
    total_answered_count   = models.IntegerField(default = 0)
    correct_answered_count = models.IntegerField(default = 0)
    unfamiliarity          = models.FloatField(default = 1)


class UpdateHistory(models.Model):
    """"""
    user        = models.ForeignKey(User)
    update_date = models.DateTimeField(auto_now_add = True)


class Grammar(models.Model):
    """"""
    pattern     = models.CharField(max_length = 200)
    explanation = models.CharField(max_length = 500)
