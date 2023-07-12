from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from faq.models import QuestionAnswer


class Views(TestCase):
    fixtures = ['faq']

    def setUp(self):
        self.client = Client()
        super(Views, self).setUp()

    def test_questions(self):
        resp = self.client.get(reverse('faq:questions'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['questions'].count() > 10)

    def test_all_questions(self):
        for question in QuestionAnswer.objects.all():
            resp = self.client.get(reverse('faq:question',
                                           kwargs={'slug': question.slug}))
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.context['question'].slug, question.slug)
            self.assertTrue(len(resp.context['answer']) > 10)
