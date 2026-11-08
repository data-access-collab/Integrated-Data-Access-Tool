from django.contrib import admin

from idat.dsa40_form_handler.models import DSAQuestion, VLOPSEQuestion


@admin.register(DSAQuestion)
class DSAQuestion(admin.ModelAdmin):
    pass


@admin.register(VLOPSEQuestion)
class VLOPSEQuestion(admin.ModelAdmin):
    pass
