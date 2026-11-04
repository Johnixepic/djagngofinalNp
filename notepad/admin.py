from django.contrib import admin
from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("filename", "format_type", "created_at", "updated_at")
    list_filter = ("format_type", "created_at")
    search_fields = ("title", "content")
    date_hierarchy = "created_at"
    ordering = ("-updated_at",)
