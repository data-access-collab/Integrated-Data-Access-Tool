from django.contrib import admin

from idat.dsa40.models import Vlopse


@admin.register(Vlopse)
class VlopseAdmin(admin.ModelAdmin):
    pass
