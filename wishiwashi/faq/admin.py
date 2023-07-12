from django.contrib import admin
from faq.models import (FAQCatagory,
                        QuestionAnswer)


class FAQCatagoryAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'order_priority',)

    ordering = ('order_priority',)


class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ('category',
                    'order_priority',
                    'question')

    ordering = ('category__order_priority', 'order_priority', 'id')


admin.site.register(FAQCatagory, FAQCatagoryAdmin)
admin.site.register(QuestionAnswer, QuestionAnswerAdmin)
