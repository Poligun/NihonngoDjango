from django.views import generic
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect

import json

from nihonngo.models import *
from nihonngo.api import *


class AuthRequiredMixin(object):
    """
    包含此 mixin 的 view 会在用户未认证时自动重定向到认证页面。
    """
    def get_context_data(self, **kwargs):
        context = super(AuthRequiredMixin, self).get_context_data(**kwargs)
        try:
            context['current_user'] = api_auth_get_user(self.request.session['user_id'])
        except:
            pass
        return context

    def get(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            return HttpResponseRedirect(reverse('nihonngo:signin'))
        else:
            return super(AuthRequiredMixin, self).get(request, *args, **kwargs)

class JsonResponseMixin(object):
    """
    包含此 mixin 的 view 可以调用 json_response 方法来返回一个 JSON 格式的 Response。
    """
    def json_response(self, object):
        return HttpResponse(json.dumps(object), content_type = 'application/json')

    def json_message_response(self, success = False, message = '', **kwargs):
        obj = {'success': success, 'message': message}
        obj.update(kwargs)
        return self.json_response(obj)

    def json_failed_message_response(self,  default_message, exception = None):
        if isinstance(exception, APIException):
            print('Exception: {0}'.format(exception.debug_message))
        else:
            print(exception)
        try:
            return self.json_message_response(success = False, message = exception if isinstance(exception, APIException) else default_message)
        except:
            return self.json_message_response(success = False, message = default_message)

# MARK - Views

class FrameworkView(AuthRequiredMixin, generic.TemplateView):
    """
    UI 开发试图，该 APP 的整体框架。
    """
    template_name = 'nihonngo/framework.html'

class SignInView(JsonResponseMixin, generic.TemplateView):
    """
    登录视图，该 APP 的登录界面。

        GET 请求：
            若用户已经登录，则将其重定向到主页。如果 cookies 中存有自动认证令牌，则
            尝试认证此令牌，如通过则跳转至主页。否则跳转至登录页面。使用 token 自动
            登录的用户会在 Session 中保存该 token 的 ID，这样登出时系统会注销该 token
            （服务器端标记 expired，前端删除对应 cookie）。

        POST 请求：
            根据用户提交的表单来验证身份。如果用户通过登录，则交由前端的 Javascript
            重定向至主页。如果用户选择了自动登录，则为其生成一个自动认证令牌，同样
            交由前端存入 cookies 中。
    """
    template_name = 'nihonngo/signin.html'

    def get(self, request, *args, **kwargs):
        if 'user_id' in request.session:
            return HttpResponseRedirect(reverse('nihonngo:home'))

        if 'sign_in_token' in request.COOKIES:
            try:
                token = api_auth_validate_token(request.COOKIES['sign_in_token'])
                request.session['user_id'] = token.user.id
                request.session['token_id'] = token.id
                return HttpResponseRedirect(reverse('nihonngo:home'))
            except:
                pass

        return super(SignInView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'name' not in request.POST or request.POST['name'] == '':
            return self.json_failed_message_response('用户名不能为空。')
        if 'password' not in request.POST or request.POST['password'] == '':
            return self.json_failed_message_response('密码不能为空。')

        try:
            user = api_auth_sign_in(request.POST['name'], request.POST['password'])
        except Exception as e:
            return self.json_failed_message_response(e, '认证失败。')

        request.session['user_id'] = user.id
        set_cookies = {}
        if request.POST.get('remember', False):
            try:
                token = api_auth_create_token(user.id)
                set_cookies['sign_in_token'] = token.token
            except:
                pass
        return self.json_message_response(success = True, message = '认证成功。', set_cookies = set_cookies, redirect = reverse('nihonngo:home'))

class SignOutView(generic.View):
    """
    登出视图。

        GET 请求：
            若用户已登录，则登出该用户。删除 Session 里的 user_id 键。如果存有自动
            认证令牌则一并标记为失效。
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponseRedirect(reverse('nihonngo:signin'))

        if 'user_id' in request.session:
            del(request.session['user_id'])

        if 'token_id' in request.session:
            message = api_auth_mark_expired(request.session['token_id'])
            response.delete_cookie('sign_in_token')

        return response

class WordsView(AuthRequiredMixin, generic.TemplateView):
    """
    生词视图，返回一个或多个生词。
    """
    template_name = 'nihonngo/words.html'

    def get(self, request, *args, **kwargs):
        try:
            words = api_search_word(self.kwargs['word'])
        except:
            words = []
        if len(words) == 0:
            return HttpResponseRedirect(reverse('nihonngo:lookup_word', kwargs = {'word': self.kwargs['word']}))
        else:
            context = self.get_context_data(**kwargs)
            context['words'] = words
            return self.render_to_response(context)

class ExamView(AuthRequiredMixin, generic.TemplateView):
    """
    测试视图，对应生词测试的页面。
    """
    template_name = 'nihonngo/exam.html'

class StatisticsView(AuthRequiredMixin, generic.TemplateView):
    """
    统计视图，对应用户测试数据的统计页面。
    """
    template_name = 'nihonngo/stats.html'

    def get_context_data(self, **kwargs):
        context = super(AuthRequiredMixin, self).get_context_data(**kwargs)
        try:
            user = api_auth_get_user(self.request.session['user_id'])
            context['statistics'] = api_get_statistics(user)
        except:
            pass
        return context

class GetQuestionView(AuthRequiredMixin, JsonResponseMixin, generic.View):
    """
    获取问题视图，返回一个 JSON 格式的 Response。
    """
    def get(self, request, *args, **kwargs):
        try:
            user = api_auth_get_user(request.session['user_id'])
            question = api_create_question(user)
            return self.json_message_response(success = True, message = '获取问题成功。', question = question)
        except Exception as e:
            return self.json_failed_message_response('获取问题失败。', e)

class AnswerQuestionView(JsonResponseMixin, generic.View):
    """
    回答问题视图，返回一个 JSON 格式的 Response。
    """
    def post(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            return self.json_failed_message_response('您未登录。')
        if 'question_id' not in request.POST:
            return self.json_failed_message_response('未指定问题的 ID。')
        if 'answer' not in request.POST:
            return self.json_failed_message_response('未给出答案。')

        try:
            correct_answer = api_answer_question(request.session['user_id'], int(request.POST['question_id']), request.POST['answer'])
            return self.json_message_response(success = True, message = '回答问题成功。', correct_answer = correct_answer)
        except Exception as e:
            return self.json_failed_message_response('回答问题失败。', e)

class LookupWordView(AuthRequiredMixin, generic.TemplateView):
    """
    查询单词视图。
    """
    template_name = 'nihonngo/lookup.html'

    def get_context_data(self, **kwargs):
        context = super(LookupWordView, self).get_context_data(**kwargs)
        context['words'] = []
        try:
            context['words'] = api_lookup_word(kwargs['word'])
        except:
            pass
        return context

class InsertWordView(JsonResponseMixin, generic.View):
    """
    插入新的生词的视图。
    """
    def post(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            return self.json_failed_message_response('您未登录。')
        if 'word_info' not in request.POST:
            return self.json_failed_message_response('未给出生词的基本信息 。')
        
        try:
            word_info = json.loads(request.POST['word_info'])
            new_word = api_insert_new_word(word_info)
            return self.json_message_response(success = True,
                                             message = '插入生词成功。',
                                             redirect = reverse('nihonngo:words', kwargs = {'word': new_word.kannji}))
        except Exception as e:
            return self.json_failed_message_response('插入生词失败。', e)
