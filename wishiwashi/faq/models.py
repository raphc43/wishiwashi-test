from django.db import models


class FAQCatagory(models.Model):
    name = models.TextField()
    order_priority = models.FloatField(default=1.0, db_index=True)

    def __unicode__(self):
        return self.name


class QuestionAnswer(models.Model):
    category = models.ForeignKey(FAQCatagory)
    order_priority = models.FloatField(default=1.0, db_index=True)
    slug = models.CharField(max_length=75, unique=True, db_index=True)

    question = models.TextField(help_text='This is RST-formatted')
    answer = models.TextField(help_text='This is RST-formatted')

    def __unicode__(self):
        return self.question
