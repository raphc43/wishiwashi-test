from django.contrib import admin
from .models import (AbandonedOrders, Address, Category, CleanOnlyOrder, Item, ItemAndQuantity, OperatingTimeRange, Order, OrderNotes,
                     OutCodes, OutCodeNotServed, Vendor, Voucher, ExpectedBackCleanOnlyOrder, TrackConfirmedOrderSlots)
from payments.models import Stripe
from vendors.models import OrderIssue


class AbandonedOrdersAdmin(admin.ModelAdmin):
    list_display = ('vendor',
                    'order',)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address_line_1',
                    'postcode',)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'order_priority')

    ordering = ('order_priority',)


class ItemAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'category',
                    'price',
                    'order_priority',
                    'visible')

    list_filter = ('category', 'visible')

    ordering = ('category__order_priority', 'order_priority')


class ItemAndQuantityAdmin(admin.ModelAdmin):
    list_display = ('item',
                    'quantity',)


class OperatingTimeRangeAdmin(admin.ModelAdmin):
    list_display = ('day_of_week',
                    'start_hour',
                    'end_hour',)


class OrderIssueInline(admin.TabularInline):
    model = OrderIssue
    extra = 1
    fields = ('issue',
              'is_other_issue',
              'other_issue_details',
              'item',
              'status')


class OrderNotesInline(admin.TabularInline):
    model = OrderNotes
    extra = 1

    fields = ('description', 'created')
    readonly_fields = ('created',)


class CleanOnlyOrderInline(admin.TabularInline):
    model = CleanOnlyOrder

    readonly_fields = ('created',)


class StripeInline(admin.StackedInline):
    model = Stripe
    extra = 0
    fieldsets = (
        ('Details', {
            'fields': (('token', 'charge',),
                       ('amount',),
                       ('cvv2_code_check_passed', 'postcode_check_passed',),
                       )
        }),
        ('Status', {
            'fields': (
                ('authorisation_status', 'last_authorised_charge_time',
                 'successful_authorised_charge_time'),
                ('card_charged_status', 'last_charged_event_time',
                 'successful_charged_time'),
                ('charge_back_status', 'charge_back_time',
                 'charge_back_last_event_time'),
                ('refund_status', 'refund_amount', 'refund_successful_time',
                 'last_refund_event_time'),
                )

        }),
        (None, {
            'fields': ('description',)
        }),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('ipaddress', 'created', 'modified',)
        })
    )
    readonly_fields = ('ipaddress', 'token', 'created', 'modified',)


class OrderAdmin(admin.ModelAdmin):
    inlines = [
        CleanOnlyOrderInline,
        StripeInline,
        OrderNotesInline,
        OrderIssueInline,
    ]
    date_hierarchy = 'placed_time'
    fieldsets = (
        ('Customer', {
            'fields': (('name', 'email', ),
                       ('mobile', 'customer',),)
        }),
        ('Order', {
            'fields': (
                ('placed_time', 'uuid', 'ticket_id'),
                ('total_price_of_order', 'voucher_code'),
                ('vat_charge', 'price_excluding_vat_charge', 'transportation_charge'),
                ('items',),
                ('pick_up_and_delivery_address',),
                ('pick_up_time', 'drop_off_time'),
                ('order_status', 'order_claimed_time'),
                ('assigned_to_vendor',),
            )
        }),
        ('Status', {
            'classes': ('collapse',),
            'fields': (
                ('authorisation_status',),
                ('card_charged_status',),
                ('charge_back_status',),
                ('refund_status',),
                ('ipaddress',),
                )

        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': (('created', 'modified'))
        }),
    )

    raw_id_fields = ('pick_up_and_delivery_address',)
    list_display = ('uuid',
                    'ticket_id',
                    'first_name',
                    'last_name',
                    'email',
                    'postcode',
                    'total_price',
                    'placed',
                    'clean_only',
                    'pick_up_time',
                    'drop_off_time',)

    list_filter = ('assigned_to_vendor', 'placed',
                   'pick_up_time', 'drop_off_time',)

    search_fields = ['uuid',
                     'ticket_id',
                     'customer__email',
                     'customer__first_name',
                     'customer__last_name',
                     'customer__userprofile__mobile_number',
                     'pick_up_and_delivery_address__postcode']

    ordering = ("-placed", "-placed_time",)
    readonly_fields = ('uuid',
                       'ipaddress',
                       'created',
                       'modified',
                       'name',
                       'email',
                       'customer',
                       'total_price',
                       'voucher_code',
                       'mobile',
                       'items',
                       'placed_time',
                       'ticket_id',
                       'postcode',
                       'clean_only'
                       )

    list_per_page = 25

    def first_name(self, obj):
        return obj.customer.first_name

    def last_name(self, obj):
        return obj.customer.last_name

    def email(self, obj):
        return obj.customer.email

    def mobile(self, obj):
        return obj.customer.userprofile.mobile_number

    def name(self, obj):
        return " ".join((obj.customer.first_name, obj.customer.last_name))

    def voucher_code(self, obj):
        if obj.voucher:
            return "{} ({}% discount)".format(obj.voucher.voucher_code, obj.voucher.percentage_off)
        else:
            return ""

    def total_price(self, obj):
        return "\xc2\xa3 %.02f" % obj.total_price_of_order

    def postcode(self, obj):
        return obj.pick_up_and_delivery_address.postcode

    def clean_only(self, obj):
        return hasattr(obj, 'cleanonlyorder')
    clean_only.boolean = True


class OutCodesAdmin(admin.ModelAdmin):
    list_display = ('out_code',)


class OutCodeNotServedAdmin(admin.ModelAdmin):
    list_display = ('out_code',
                    'email_address',)


class VendorAdmin(admin.ModelAdmin):
    list_display = ('company_name',
                    'address',
                    'capacity_per_hour',
                    'outcodes',
                    'last_viewed_the_orders_page')

    def outcodes(self, obj):
        return ", ".join(o.out_code for o in obj.catchment_area.all())

    filter_horizontal = ('catchment_area',
                         'hours_of_operation',
                         'staff')

    readonly_fields = ('outcodes',
                       'last_viewed_the_orders_page')


class VoucherAdmin(admin.ModelAdmin):
    list_display = ('issued_by',
                    'percentage_off',
                    'voucher_code',
                    'valid_until',
                    'use_limit',
                    'use_count')

    readonly_fields = ('use_count',)
    list_filter = ('valid_until', 'created',)
    ordering = ('-valid_until',)
    search_fields = ['voucher_code']


class ExpectedBackCleanOnlyOrderAdmin(admin.ModelAdmin):
    list_display = ('clean_only_order',
                    'ticket_id',
                    'expected_back',
                    'confirmed_back',)

    def ticket_id(self, obj):
        return obj.clean_only_order.order.ticket_id


class TrackConfirmedOrderSlotsAdmin(admin.ModelAdmin):
    list_display = ('appointment',
                    'counter',)
    ordering = ('-appointment',)

admin.site.register(AbandonedOrders, AbandonedOrdersAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(ItemAndQuantity, ItemAndQuantityAdmin)
admin.site.register(OperatingTimeRange, OperatingTimeRangeAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OutCodes, OutCodesAdmin)
admin.site.register(OutCodeNotServed, OutCodeNotServedAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(Voucher, VoucherAdmin)
admin.site.register(ExpectedBackCleanOnlyOrder, ExpectedBackCleanOnlyOrderAdmin)
admin.site.register(TrackConfirmedOrderSlots, TrackConfirmedOrderSlotsAdmin)

