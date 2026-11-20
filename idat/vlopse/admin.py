from django.contrib import admin

from idat.vlopse.models import Vlopse


@admin.register(Vlopse)
class VlopseAdmin(admin.ModelAdmin):
    list_display = ["name", "operator", "platform_type", "modality"]
    list_filter = ["platform_type", "modality"]
    search_fields = ["name", "operator"]
