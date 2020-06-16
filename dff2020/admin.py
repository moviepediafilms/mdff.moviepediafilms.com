from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django import forms

from .models import Faq, Rule, Entry, Order


class RuntimeListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("runtime")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "runtime"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ("0-10 mins", _("within 10 minutes")),
            ("10-20 mins", _("from 10 to 20 minutes")),
            ("20+ mins", _("more than 20 minutes")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == "0-10 mins":
            return queryset.filter(runtime__gte=0, runtime__lte=10)
        if self.value() == "10-20 mins":
            return queryset.filter(runtime__gt=10, runtime__lte=20)
        if self.value() == "20+ mins":
            return queryset.filter(runtime__gt=20,)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_display = [
        "rzp_order_id",
        "rzp_payment_id",
        "receipt_number",
        "amount_inr",
        "created_at",
        "owner",
    ]
    list_filter = ["owner"]

    def amount_inr(self, obj):
        return obj.amount / 100


class FaqModelForm(forms.ModelForm):
    answer = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = Faq
        fields = "__all__"


class RuleModelForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = Rule
        fields = "__all__"


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    form = FaqModelForm
    list_display = ["question", "answer"]


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ["text", "type"]
    form = RuleModelForm


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["name", "director", "link", "synopsis_short", "runtime", "order"]
    list_filter = [RuntimeListFilter, "order"]

    def synopsis_short(self, obj):
        return obj.synopsis[:50]
