from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import FileResponse, Http404
from .models import Note
from .forms import NoteForm, ImportForm
import bleach


def note_list(request):
    """List all notes — the sidebar file browser. Supports ?q= search."""
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        notes = Note.objects.filter(
            Q(title__icontains=q) | Q(content__icontains=q)
        )
    else:
        notes = Note.objects.all()
    return render(request, "notepad/list.html", {"notes": notes, "q": q})


def note_new(request):
    """Create a new blank note."""
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New note created.")
            return redirect("notepad:note_list")
    else:
        form = NoteForm()
    notes = Note.objects.all()
    return render(request, "notepad/editor.html", {
        "form": form, "note": None, "current_note_pk": None,
        "notes": notes,
    })


def _validate_saveas_title(raw_title: str) -> tuple[str | None, str | None]:
    """Validate a Save As title. Returns (cleaned_title, error_message)."""
    title = raw_title.strip() if raw_title else ""
    if not title:
        return None, "Title cannot be empty or whitespace-only."
    if len(title) > 255:
        return None, "Title must be 255 characters or fewer."
    if "/" in title or "\\" in title:
        return None, "Title cannot contain / or \\ characters."
    for ch in title:
        if ord(ch) < 32 or (ord(ch) == 127):
            return None, "Title contains invalid control characters."
    return title, None


def note_edit(request, pk):
    """Edit an existing note."""
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "saveas":
            # Save As must copy the current editor values, not the stale database
            # instance. The editor submits title/content/format_type with the action.
            new_title, error = _validate_saveas_title(
                request.POST.get("new_title", f"{note.title}_copy")
            )
            notes = Note.objects.all()
            if error:
                messages.error(request, error)
                form = NoteForm(request.POST, instance=note)
                return render(request, "notepad/editor.html", {
                    "form": form,
                    "note": note,
                    "current_note_pk": note.pk,
                    "notes": notes,
                })

            copy_form = NoteForm({
                "title": new_title,
                "content": request.POST.get("content", note.content),
                "format_type": request.POST.get("format_type", note.format_type),
            })
            if not copy_form.is_valid():
                for field_errors in copy_form.errors.values():
                    for error_message in field_errors:
                        messages.error(request, error_message)
                form = NoteForm(request.POST, instance=note)
                return render(request, "notepad/editor.html", {
                    "form": form,
                    "note": note,
                    "current_note_pk": note.pk,
                    "notes": notes,
                })

            copy_form.save()
            messages.success(request, f"Saved as: {new_title}")
            return redirect("notepad:note_list")
        else:
            # Normal save (overwrite)
            form = NoteForm(request.POST, instance=note)
            if form.is_valid():
                form.save()
                messages.success(request, f"Saved: {note.filename}")
                return redirect("notepad:note_list")
            # Form has errors — re-render with messages
            for field in form.errors:
                for err in form.errors[field]:
                    messages.error(request, err)
    else:
        form = NoteForm(instance=note)
    # Populate sidebar notes list for editor page
    notes = Note.objects.all()
    return render(request, "notepad/editor.html", {
        "form": form, "note": note, "current_note_pk": note.pk,
        "notes": notes,
    })


def note_delete(request, pk):
    """Delete a note with confirmation."""
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        note.delete()
        messages.success(request, f"Deleted: {note.filename}")
        return redirect("notepad:note_list")
    return render(request, "notepad/delete_confirm.html", {"note": note})


def _available_import_title(title: str, format_type: str) -> tuple[str, bool]:
    """Return a collision-free title without overwriting an existing note."""
    candidate = title
    suffix = 2
    while Note.objects.filter(title__iexact=candidate, format_type=format_type).exists():
        candidate = f"{title} ({suffix})"
        suffix += 1
    return candidate, candidate != title


def note_import(request):
    """Import a .txt or .md file and open the resulting note."""
    if request.method != "POST":
        return redirect("notepad:note_list")

    form = ImportForm(request.POST, request.FILES)
    if form.is_valid():
        title, renamed = _available_import_title(
            form.derived_title, form.format_type
        )
        note = Note.objects.create(
            title=title,
            content=form.decoded_content,
            format_type=form.format_type,
        )
        if renamed:
            messages.success(
                request,
                f"Imported as {note.filename} because that filename already existed. "
                "Your existing note was not changed.",
            )
        else:
            messages.success(request, f"Imported and opened: {note.filename}")
        return redirect("notepad:note_edit", pk=note.pk)
    else:
        # Re-render the list page with errors so user can see what went wrong
        q = request.GET.get("q", "").strip()
        if q:
            from django.db.models import Q
            notes = Note.objects.filter(
                Q(title__icontains=q) | Q(content__icontains=q)
            )
        else:
            notes = Note.objects.all()
        return render(request, "notepad/list.html", {
            "notes": notes,
            "q": q,
            "import_form": form,
        })


def note_download(request, pk):
    """Download a note as a .txt or .md file attachment."""
    import io
    note = get_object_or_404(Note, pk=pk)

    # Derive a safe filename — strip path separators and dangerous characters
    safe_title = note.title.replace("/", "_").replace("\\", "_")
    ext = "md" if note.format_type == "md" else "txt"
    filename = f"{safe_title}.{ext}"

    # Return the raw content as an attachment; do not modify the note.
    response = FileResponse(
        io.BytesIO(note.content.encode("utf-8")),
        as_attachment=True,
        filename=filename,
        content_type=f"text/{ext}; charset=utf-8",
    )
    return response


# Allowed HTML tags after markdown rendering — minimal safe allowlist.
ALLOWED_TAGS = [
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "blockquote",
    "code", "pre",
    "em", "strong", "del", "s",
    "a",
    "table", "thead", "tbody", "tr", "th", "td",
    "hr",
]
ALLOWED_ATTRS = {
    "a": ["href", "rel", "target"],
    "table": ["class"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}

def _sanitize_markdown_html(raw_html: str) -> str:
    """Sanitize markdown-rendered HTML using bleach.
    
    bleach.clean() with strip=True removes all tags not in ALLOWED_TAGS.
    For allowed tags, only attributes in ALLOWED_ATTRS are preserved.
    Bleach natively rejects javascript: and data: URL schemes on <a href>.
    """
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def markdown_preview_raw(request):
    """Preview raw markdown content without saving to the database.
    
    Accepts POST with JSON body: {"content": "..."}
    Returns rendered, sanitized HTML.
    """
    if request.method != "POST":
        return render(request, "notepad/preview.html", {"html": ""})
    
    try:
        import json
        data = json.loads(request.body)
        raw_content = data.get("content", "")
    except (json.JSONDecodeError, AttributeError):
        raw_content = ""
    
    import markdown
    raw_html = markdown.markdown(
        raw_content, extensions=["extra", "codehilite", "tables"]
    )
    html = _sanitize_markdown_html(raw_html)
    return render(request, "notepad/preview.html", {"html": html})


def markdown_preview(request, pk):
    """AJAX endpoint — returns rendered markdown HTML."""
    note = get_object_or_404(Note, pk=pk)
    if note.format_type == "md":
        import markdown
        raw_html = markdown.markdown(
            note.content, extensions=["extra", "codehilite", "tables"]
        )
        html = _sanitize_markdown_html(raw_html)
        return render(request, "notepad/preview.html", {"html": html})
    return render(request, "notepad/preview.html", {"html": note.content})
