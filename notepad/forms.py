from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Note


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "content", "format_type"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Untitled"}),
            "content": forms.Textarea(
                attrs={
                    "rows": 25,
                    "cols": 80,
                    "class": "editor-textarea",
                    "placeholder": "Start typing...",
                }
            ),
            "format_type": forms.Select(choices=Note.FORMAT_CHOICES),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise ValidationError("Title cannot be empty or whitespace-only.")
        if len(title) > 255:
            raise ValidationError("Title must be 255 characters or fewer.")
        if "/" in title or "\\" in title:
            raise ValidationError("Title cannot contain / or \\ characters.")
        # Reject control characters (Unicode categories Cc and Cf, excluding common whitespace)
        for ch in title:
            if ord(ch) < 32 or (ord(ch) == 127):
                raise ValidationError("Title contains invalid control characters.")
        return title


class ImportForm(forms.Form):
    """Form for importing .txt and .md files into notes."""

    file = forms.FileField(
        label="File",
        help_text="Upload a .txt or .md file (max 1 MiB).",
        allow_empty_file=True,
    )

    def clean_file(self):
        # Get the raw file from cleaned_data, bypassing Django's empty-file check
        uploaded = self.files.get("file")
        if not uploaded:
            raise ValidationError("No file was uploaded.")

        # Validate extension server-side
        name = uploaded.name if uploaded.name else ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ("txt", "md"):
            raise ValidationError(
                f"Unsupported file type '.{ext}'. Only .txt and .md files are accepted."
            )

        # Enforce max upload size (1 MiB) — Django does not enforce this on FileField
        # by default; we check manually.
        MAX_SIZE = 1 * 1024 * 1024  # 1 MiB
        if uploaded.size > MAX_SIZE:
            raise ValidationError(
                f"File is too large. Maximum allowed size is 1 MiB (got {uploaded.size} bytes)."
            )

        # Read and decode content — do NOT execute or render it
        raw_bytes = uploaded.read()

        # Encoding fallback chain:
        #   1. UTF-8-sig — primary for modern text; strips BOM if present.
        #   2. CP1252 — legacy Windows Western text (superset of Latin-1 for printable range).
        #   3. Latin-1 — universal fallback that accepts every byte value.
        content = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                content = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise ValidationError(
                "The uploaded file could not be decoded as text. Please ensure it is a valid UTF-8, CP1252, or Latin-1 encoded text file."
            )

        # Binary rejection heuristic.
        # After the Latin-1 fallback any byte sequence is decodable, so we apply
        # a post-decode sanity check to avoid silently accepting binary data.
        #
        # Policy:
        #   - C1 control characters (U+0080–U+009F) never appear in legitimate text
        #     files; their presence is a strong binary indicator.
        #   - A non-printable-character ratio above 5 % (excluding \t, \n, \r)
        #     indicates binary or heavily corrupted content.
        if content:
            total_chars = len(content)
            c1_controls = sum(
                1 for ch in content if 0x80 <= ord(ch) <= 0x9F
            )
            if c1_controls > 0:
                raise ValidationError(
                    "The uploaded file appears to contain binary data. Please upload a valid text file."
                )
            non_printable = sum(
                1 for ch in content
                if not ch.isprintable() and ch not in ("\t", "\n", "\r")
            )
            np_ratio = non_printable / total_chars
            if np_ratio > 0.05:
                raise ValidationError(
                    "The uploaded file appears to contain binary data. Please upload a valid text file."
                )

        # Derive title from filename (without extension)
        stem = name.rsplit(".", 1)[0].strip() if "." in name else ""
        if not stem:
            raise ValidationError("Could not derive a valid title from the filename.")

        # Re-validate using existing title rules
        if len(stem) > 255:
            raise ValidationError("Derived title is too long (must be 255 characters or fewer).")
        if "/" in stem or "\\" in stem:
            raise ValidationError("Derived title cannot contain / or \\ characters.")
        for ch in stem:
            if ord(ch) < 32 or (ord(ch) == 127):
                raise ValidationError("Derived title contains invalid control characters.")

        # Store decoded content and derived metadata on the form instance
        self.decoded_content = content
        self.derived_title = stem
        self.format_type = ext

        return uploaded
