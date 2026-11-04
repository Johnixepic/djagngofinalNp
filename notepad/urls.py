from django.urls import path
from . import views

app_name = "notepad"

urlpatterns = [
    path("", views.note_list, name="note_list"),
    path("new/", views.note_new, name="note_new"),
    path("import/", views.note_import, name="note_import"),
    path("<uuid:pk>/edit/", views.note_edit, name="note_edit"),
    path("<uuid:pk>/delete/", views.note_delete, name="note_delete"),
    path("<uuid:pk>/download/", views.note_download, name="note_download"),
    path("<uuid:pk>/preview/", views.markdown_preview, name="markdown_preview"),
    path("preview/raw/", views.markdown_preview_raw, name="markdown_preview_raw"),
]
