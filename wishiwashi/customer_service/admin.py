from django.contrib import admin
from .models import (UserProfile,
                     CustomerContactTemplate,
                     MessageToCustomer,
                     Ticket)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)


admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(CustomerContactTemplate)
admin.site.register(MessageToCustomer)
admin.site.register(Ticket)


