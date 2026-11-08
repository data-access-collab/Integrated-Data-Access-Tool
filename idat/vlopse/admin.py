from django.contrib import admin

from idat.vlopse.models import Vlopse


@admin.register(Vlopse)
class VlopseAdmin(admin.ModelAdmin):
    pass
