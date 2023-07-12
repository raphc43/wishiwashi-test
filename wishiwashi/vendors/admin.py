from django.contrib import admin
from .models import (IssueType, CleanOnlyPrices, CleanAndCollectPrices,
                     DefaultCleanOnlyPrices, DefaultCleanAndCollectPrices,
                     OrderPayments)


admin.site.register(IssueType)


class DefaultPricesAdmin(admin.ModelAdmin):
    list_display = ('item',
                    'item_category',
                    'price')

    list_filter = ('item__category__name',)

    ordering = ('item__category__order_priority',)

    read_only_fields = ('item_category',)

    def item_category(self, obj):
        return obj.item.category.name


class DefaultCleanOnlyPricesAdmin(DefaultPricesAdmin):
    pass


class DefaultCleanAndCollectPricesAdmin(DefaultPricesAdmin):
    pass


class CleanAdmin(DefaultPricesAdmin):
    list_display = ('item',
                    'item_category',
                    'vendor',
                    'price')

    list_filter = ('item__category__name', 'vendor')


class CleanOnlyPricesAdmin(CleanAdmin):
    pass


class CleanAndCollectPricesAdmin(CleanAdmin):
    pass


class OrderPaymentsAdmin(admin.ModelAdmin):
    list_display = ('order',
                    'total_amount')


admin.site.register(DefaultCleanOnlyPrices, DefaultCleanOnlyPricesAdmin)
admin.site.register(DefaultCleanAndCollectPrices, DefaultCleanAndCollectPricesAdmin)
admin.site.register(CleanOnlyPrices, CleanOnlyPricesAdmin)
admin.site.register(CleanAndCollectPrices, CleanAndCollectPricesAdmin)
admin.site.register(OrderPayments, OrderPaymentsAdmin)
