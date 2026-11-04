from django.db import models
import uuid


class Note(models.Model):
    FORMAT_CHOICES = [
        ("txt", "Plain Text"),
        ("md", "Markdown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text="File name (without extension)")
    content = models.TextField(blank=True, default="")
    format_type = models.CharField(max_length=3, choices=FORMAT_CHOICES, default="txt")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def filename(self):
        ext = "md" if self.format_type == "md" else "txt"
        return f"{self.title}.{ext}"

    @property
    def preview_html(self):
        """Render markdown to HTML (sanitized)."""
        if self.format_type == "md":
            import markdown
            raw = markdown.markdown(
                self.content, extensions=["extra", "codehilite", "tables"]
            )
            from .views import _sanitize_markdown_html
            return _sanitize_markdown_html(raw)
        return None

    def __str__(self):
        return self.filename

    class Meta:
        ordering = ["-updated_at"]
