from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from docutils.core import publish_parts

from faq.models import QuestionAnswer


def questions(request):
    context = {
        'questions': QuestionAnswer.objects.all().\
                        order_by('category__order_priority',
                                 'order_priority',
                                 'id'),
        'title': 'Frequently asked questions regarding Wishi Washi'
    }
    return render_to_response('faq/questions.html',
                              context,
                              context_instance=RequestContext(request))

def question(request, slug):
    try:
        question_answer = QuestionAnswer.objects.get(slug=slug)
    except QuestionAnswer.DoesNotExist:
        raise Http404()

    context = {
        'question': question_answer,
        'answer': publish_parts(question_answer.answer,
                                writer_name='html')['html_body'],
        'title': 'Wishi Washi, %s' % question_answer.question,
    }

    return render_to_response('faq/question.html',
                              context,
                              context_instance=RequestContext(request))
