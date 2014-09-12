from django.conf.urls import patterns, url

from nihonngo.views import *

urlpatterns = patterns('',
    url(r'^framework/$', FrameworkView.as_view(), name = 'framework'),
    url(r'^home/$', FrameworkView.as_view(), name = 'home'),
    url(r'^signin/$', SignInView.as_view(), name='signin'),
    url(r'^signout/$', SignOutView.as_view(), name='signout'),
    url(r'^word/lookup/(?P<word>.+)/$', LookupWordView.as_view(), name = 'lookup_word'),
    url(r'^word/insert/$', InsertWordView.as_view(), name = 'insert_word'),
    url(r'^word/(?P<word>.+)/$', WordsView.as_view(), name = 'words'),
    url(r'^exam/$', ExamView.as_view(), name="exam"),
    url(r'^exam/stats/$', StatisticsView.as_view(), name="statistics"),
    url(r'^exam/question/get/$', GetQuestionView.as_view(), name = 'get_question'),
    url(r'^exam/question/answer/$', AnswerQuestionView.as_view(), name = 'answer_question'),
)
