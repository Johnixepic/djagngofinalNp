from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
import re
import json
from django.urls import reverse
from .models import Note
import uuid


class MarkdownPreviewSanitizationTests(TestCase):
    """Verify that the markdown preview endpoint sanitizes dangerous HTML."""

    def setUp(self):
        self.client = Client()
        self.md_note = Note.objects.create(
            title="xss-test",
            content="",
            format_type="md",
        )
        self.txt_note = Note.objects.create(
            title="plain-test",
            content="hello world",
            format_type="txt",
        )

    def _preview_url(self, note):
        return reverse("notepad:markdown_preview", kwargs={"pk": note.pk})

    # --- Ordinary markdown renders correctly ---

    def test_headings_render(self):
        self.md_note.content = "# Heading 1\n## Heading 2\n### Heading 3"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<h1>")
        self.assertContains(resp, "<h2>")
        self.assertContains(resp, "<h3>")

    def test_paragraphs_and_emphasis_render(self):
        self.md_note.content = "Plain paragraph.\n\n**bold** and *italic*"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<p>")
        self.assertContains(resp, "<strong>")
        self.assertContains(resp, "<em>")

    def test_lists_render(self):
        self.md_note.content = "- Item one\n- Item two\n\n1. First\n2. Second"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        # The "extra" extension may render numbered lists inside <ul> too
        self.assertContains(resp, "<li>")

    def test_links_render(self):
        self.md_note.content = "[Click here](https://example.com)"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'href="https://example.com"')

    def test_blockquotes_render(self):
        self.md_note.content = "> This is a quote"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<blockquote>")

    def test_code_blocks_render(self):
        # Use indented code block (4 spaces) which works reliably with all extensions
        self.md_note.content = "    code here"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<pre>")
        self.assertContains(resp, "<code>")

    def test_tables_render(self):
        self.md_note.content = "| A | B |\n|---|---|\n| 1 | 2 |"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<table>")
        self.assertContains(resp, "<td>")

    # --- XSS vectors are stripped ---

    def test_script_injection_stripped(self):
        self.md_note.content = '<script>alert("xss")</script>'
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("<script>", decoded)

    def test_onerror_handler_stripped(self):
        self.md_note.content = "![evil](image.png)<img src=x onerror=\"alert(1)\" />"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("onerror", decoded)
        self.assertNotIn("alert", decoded)

    def test_javascript_link_stripped(self):
        self.md_note.content = "[click](javascript:alert(1))"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("javascript:", decoded)

    def test_data_url_link_stripped(self):
        self.md_note.content = "[click](data:text/html,<script>alert(1)</script>)"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("data:", decoded)

    def test_onclick_attribute_stripped(self):
        self.md_note.content = "<div onclick=\"alert(1)\">hello</div>"
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("onclick", decoded)

    # --- Plain text notes pass through unchanged ---

    def test_plain_text_passthrough(self):
        resp = self.client.get(self._preview_url(self.txt_note))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "hello world")


    def test_empty_input(self):
        """Empty markdown content should render without errors."""
        self.md_note.content = ""
        self.md_note.save()
        resp = self.client.get(self._preview_url(self.md_note))
        self.assertEqual(resp.status_code, 200)
        # Should not crash; output may be empty or contain minimal markup
        self.assertIsInstance(resp.content.decode(), str)


class NoteCRUDTests(TestCase):
    """Basic CRUD tests to ensure Save / Save As / Delete still work."""

    def setUp(self):
        self.client = Client()

    def test_create_note(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "Test Note",
            "content": "Hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 1)

    def test_save_as_creates_copy(self):
        note = Note.objects.create(title="Original", content="content", format_type="md")
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": note.pk}),
            {"action": "saveas", "new_title": "Copy", "content": "content"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 2)
        copied = Note.objects.get(title="Copy")
        self.assertEqual(copied.content, "content")

    def test_delete_note(self):
        note = Note.objects.create(title="To Delete", content="x", format_type="txt")
        resp = self.client.post(
            reverse("notepad:note_delete", kwargs={"pk": note.pk}),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 0)

    def test_delete_nonexistent_returns_404(self):
        fake_pk = uuid.uuid4()
        resp = self.client.post(
            reverse("notepad:note_delete", kwargs={"pk": fake_pk}),
        )
        self.assertEqual(resp.status_code, 404)


class TitleValidationTests(TestCase):
    """Validate title rules for create, edit, and Save As."""

    def setUp(self):
        self.client = Client()

    def test_empty_title_rejected_on_create(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "empty")

    def test_whitespace_only_title_rejected_on_create(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "   ",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "empty")

    def test_title_over_255_chars_rejected(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "x" * 256,
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        # Django error message says "at most 255 characters"
        self.assertContains(resp, "255")

    def test_forward_slash_in_title_rejected(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "bad/title",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/")

    def test_backslash_in_title_rejected(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "bad\\title",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "\\")

    def test_leading_trailing_whitespace_trimmed_on_create(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "  Hello World  ",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 302)
        note = Note.objects.get()
        self.assertEqual(note.title, "Hello World")

    def test_valid_title_accepted_on_create(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "My Note",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 1)


class SaveAsValidationTests(TestCase):
    """Validate Save As behavior."""

    def setUp(self):
        self.client = Client()
        self.original = Note.objects.create(
            title="Original", content="original content", format_type="md"
        )

    def test_save_as_creates_distinct_note(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "Copy", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 2)
        copy = Note.objects.get(title="Copy")
        self.assertNotEqual(copy.pk, self.original.pk)
        self.assertEqual(copy.content, "original content")

    def test_save_as_preserves_original(self):
        original_pk = self.original.pk
        self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": original_pk}),
            {"action": "saveas", "new_title": "Copy", "content": "original content"},
        )
        self.original.refresh_from_db()
        self.assertEqual(self.original.title, "Original")
        self.assertEqual(Note.objects.filter(pk=original_pk).count(), 1)

    def test_save_as_empty_title_rejected(self):
        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)

    def test_save_as_whitespace_title_rejected(self):
        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "   ", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)

    def test_save_as_slash_in_title_rejected(self):
        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "bad/name", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)

    def test_save_as_trims_whitespace(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "  Copied  ", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 302)
        copy = Note.objects.get(title="Copied")
        self.assertEqual(copy.title, "Copied")

    def test_duplicate_titles_permitted(self):
        Note.objects.create(title="Original", content="other", format_type="txt")
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "Original", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 3)


class CRUDStabilityTests(TestCase):
    """Regression tests for normal CRUD behavior."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(title="To Edit", content="old", format_type="txt")

    def test_save_updates_existing_note(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "save", "title": "Updated", "content": "new content", "format_type": "md"},
        )
        self.assertEqual(resp.status_code, 302)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Updated")
        self.assertEqual(self.note.content, "new content")
        self.assertEqual(self.note.format_type, "md")
        self.assertEqual(Note.objects.count(), 1)

    def test_delete_removes_note(self):
        resp = self.client.post(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 0)

    def test_delete_confirmation_page_renders(self):
        resp = self.client.get(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Are you sure")

    def test_invalid_save_renders_form(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "save", "title": "", "content": "x", "format_type": "txt"},
        )
        self.assertEqual(resp.status_code, 200)



class MarkdownNoteCreationTests(TestCase):
    """Verify creating and loading Markdown-format notes."""

    def setUp(self):
        self.client = Client()

    def test_create_valid_markdown_note(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "Markdown Note",
            "content": "# Hello\n**bold**",
            "format_type": "md",
        })
        self.assertEqual(resp.status_code, 302)
        note = Note.objects.get(title="Markdown Note")
        self.assertEqual(note.format_type, "md")
        self.assertEqual(note.content, "# Hello\n**bold**")

    def test_open_existing_note_loads_saved_values(self):
        note = Note.objects.create(
            title="Loaded Note",
            content="saved content here",
            format_type="md",
        )
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Loaded Note")
        self.assertContains(resp, "saved content here")
        self.assertContains(resp, 'value="md"')


class InvalidSaveDoesNotAlterNoteTests(TestCase):
    """Invalid Save must not mutate the database record."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(
            title="Original", content="original content", format_type="txt"
        )

    def test_invalid_normal_save_does_not_alter_note(self):
        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "save", "title": "", "content": "x", "format_type": "txt"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Original")
        self.assertEqual(self.note.content, "original content")

    def test_invalid_save_as_does_not_create_copy_or_alter_original(self):
        original_pk = self.note.pk
        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": original_pk}),
            {"action": "saveas", "new_title": "", "content": "original content"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Original")
        self.assertEqual(self.note.content, "original content")


class SaveAsPreservesFormatTests(TestCase):
    """Save As must preserve the source note's content and format."""

    def setUp(self):
        self.client = Client()
        self.original = Note.objects.create(
            title="Source", content="# heading\n- item", format_type="md"
        )

    def test_save_as_preserves_source_content_and_format(self):
        # Save As copies the ORIGINAL note content, not POST data
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.original.pk}),
            {"action": "saveas", "new_title": "Copy"},
        )
        self.assertEqual(resp.status_code, 302)
        copy = Note.objects.get(title="Copy")
        # Copy must match the original's content and format
        self.assertEqual(copy.content, "# heading\n- item")
        self.assertEqual(copy.format_type, "md")
        # Source must be unchanged
        self.original.refresh_from_db()
        self.assertEqual(self.original.content, "# heading\n- item")


class DeleteGetDoesNotDeleteTests(TestCase):
    """GET on the delete endpoint must not delete the note."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(
            title="To Keep", content="x", format_type="txt"
        )

    def test_get_delete_does_not_delete(self):
        count_before = Note.objects.count()
        resp = self.client.get(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.note.filename)
        self.assertEqual(Note.objects.count(), count_before)


class CsrfProtectedDeleteTests(TestCase):
    """POST deletion with CSRF token when CSRF enforcement is enabled."""

    def setUp(self):
        # enforce_csrf_checks=True makes the test client reject missing/invalid CSRF tokens
        self.client = Client(enforce_csrf_checks=True)
        self.note = Note.objects.create(
            title="CSRF Test", content="x", format_type="txt"
        )

    def test_post_delete_without_csrf_fails(self):
        # Without a valid CSRF token, POST to delete should fail
        resp = self.client.post(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
            {},
        )
        # Django returns 403 for missing/invalid CSRF
        self.assertEqual(resp.status_code, 403)

    def test_post_delete_with_csrf_succeeds(self):
        # Get the delete confirm page first to obtain the CSRF token
        resp = self.client.get(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(resp.status_code, 200)
        # Extract CSRF token from the response HTML
        import re
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.content.decode())
        self.assertIsNotNone(match, "CSRF token not found in delete confirmation page")
        csrf_token = match.group(1)

        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
            {"csrfmiddlewaretoken": csrf_token},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before - 1)


class UnsupportedHttpMethodsTests(TestCase):
    """Unsupported HTTP methods must not trigger server errors (500)."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(
            title="Method Test", content="x", format_type="txt"
        )

    def test_put_on_edit_no_server_error(self):
        resp = self.client.put(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
        )
        self.assertNotEqual(resp.status_code, 500)

    def test_patch_on_edit_no_server_error(self):
        resp = self.client.patch(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
        )
        self.assertNotEqual(resp.status_code, 500)

    def test_delete_on_edit_no_server_error(self):
        resp = self.client.delete(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
        )
        self.assertNotEqual(resp.status_code, 500)

    def test_put_on_new_no_server_error(self):
        resp = self.client.put(reverse("notepad:note_new"))
        self.assertNotEqual(resp.status_code, 500)

    def test_patch_on_new_no_server_error(self):
        resp = self.client.patch(reverse("notepad:note_new"))
        self.assertNotEqual(resp.status_code, 500)

    def test_put_on_delete_no_server_error(self):
        resp = self.client.put(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertNotEqual(resp.status_code, 500)


class FormValidationFeedbackTests(TestCase):
    """Missing or invalid form fields return useful validation feedback."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(
            title="Validator", content="x", format_type="txt"
        )

    def test_empty_title_on_create_shows_error(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("This field is required", resp.content.decode())

    def test_missing_title_on_create_shows_error(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("This field is required", resp.content.decode())

    def test_invalid_title_on_edit_shows_error(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "save", "title": "", "content": "x", "format_type": "txt"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("This field is required", resp.content.decode())

    def test_control_chars_in_title_rejected_on_create(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "bad\x01title",
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "control")

    def test_control_chars_in_title_rejected_on_save_as(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "saveas", "new_title": "bad\x01title", "content": "x"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "control")

    def test_long_title_rejected_on_create(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "x" * 300,
            "content": "hello",
            "format_type": "txt",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "255")

    def test_delete_confirmation_shows_correct_note(self):
        resp = self.client.get(
            reverse("notepad:note_delete", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.note.filename)


class GetDoesNotDeleteTests(TestCase):
    """Verify that GET requests to CRUD endpoints do not mutate state."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(
            title="Get Safe", content="x", format_type="txt"
        )

    def test_get_edit_does_not_delete(self):
        count_before = Note.objects.count()
        resp = self.client.get(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)

    def test_get_list_does_not_delete(self):
        count_before = Note.objects.count()
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)


class LivePreviewRawEndpointTests(TestCase):
    """Tests for the markdown_preview_raw endpoint that renders unsaved content."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse("notepad:markdown_preview_raw")
        # Obtain a CSRF token from the new note page which has {% csrf_token %}
        resp = self.client.get(reverse("notepad:note_new"))
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.content.decode())
        self.csrf_token = match.group(1) if match else ""

    def _post(self, content):
        return self.client.post(
            self.url,
            json.dumps({"content": content}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

    def test_render_headings(self):
        resp = self._post("# Heading 1\n## Heading 2")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<h1>")
        self.assertContains(resp, "<h2>")

    def test_render_paragraphs_and_emphasis(self):
        resp = self._post("Para\n\n**bold** and *italic*")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<p>")
        self.assertContains(resp, "<strong>")
        self.assertContains(resp, "<em>")

    def test_render_lists(self):
        resp = self._post("- Item one\n- Item two")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<li>")

    def test_render_links(self):
        resp = self._post("[link](https://example.com)")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'href="https://example.com"')

    def test_render_blockquotes(self):
        resp = self._post("> quote")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<blockquote>")

    def test_render_fenced_code(self):
        resp = self._post("```\ncode\n```")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<pre>")
        self.assertContains(resp, "<code>")

    def test_render_tables(self):
        resp = self._post("| A | B |\n|---|---|\n| 1 | 2 |")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<table>")

    def test_xss_script_stripped(self):
        resp = self._post('<script>alert(1)</script>')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("<script>", resp.content.decode())

    def test_xss_onerror_stripped(self):
        resp = self._post('![img](x) <img src=x onerror="alert(1)">')
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("onerror", decoded)

    def test_javascript_link_stripped(self):
        resp = self._post("[x](javascript:alert(1))")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("javascript:", resp.content.decode())

    def test_empty_content_returns_200(self):
        resp = self._post("")
        self.assertEqual(resp.status_code, 200)

    def test_missing_content_key_returns_200(self):
        resp = self.client.post(
            self.url, json.dumps({}), content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(resp.status_code, 200)

    def test_preview_does_not_modify_database(self):
        note = Note.objects.create(title="LivePreview", content="old", format_type="md")
        count_before = Note.objects.count()
        self._post("new content")
        self.assertEqual(Note.objects.count(), count_before)
        note.refresh_from_db()
        self.assertEqual(note.content, "old")

    def test_csrf_required(self):
        resp = self.client.post(
            self.url, json.dumps({"content": "x"}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

class LivePreviewIntegrationTests(TestCase):
    """Verify the editor page renders split-pane for MD notes and not for TXT."""

    def setUp(self):
        self.client = Client()

    def test_md_note_editor_has_split_pane(self):
        note = Note.objects.create(title="MD Note", content="# Hello", format_type="md")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'split-mode')
        self.assertContains(resp, 'id="preview-pane"')

    def test_txt_note_editor_no_split_pane(self):
        note = Note.objects.create(title="TXT Note", content="hello", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        # Check the editor-wrapper div specifically does not have split-mode class
        # (split-mode may appear in CSS static file, so check the element itself)
        m = re.search(r'id="editor-wrapper"[^>]*class="([^"]*)"', resp.content.decode())
        if m:
            classes = m.group(1).split()
            self.assertNotIn('split-mode', classes)
        else:
            # Fallback: check that the specific pattern editor-wrapper with split-mode is absent
            self.assertNotIn('editor-wrapper split-mode', resp.content.decode())


class NoteSearchTests(TestCase):
    """Verify search by title and content on the note list page."""

    def setUp(self):
        self.client = Client()
        self.note_a = Note.objects.create(title="Alpha", content="alpha content here", format_type="txt")
        self.note_b = Note.objects.create(title="Beta", content="beta content here", format_type="md")
        self.note_c = Note.objects.create(title="Gamma", content="gamma content here", format_type="txt")

    def test_search_by_title(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "Alpha"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Alpha", html)
        self.assertNotIn("Beta", html)
        self.assertNotIn("Gamma", html)

    def test_search_by_content(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "beta content"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Beta", html)
        self.assertNotIn("Alpha", html)

    def test_case_insensitive(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "ALPHA"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Alpha", html)

    def test_partial_phrase_match(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "alpha content"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Alpha", html)

    def test_multiple_matching_notes(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "content"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Alpha", html)
        self.assertIn("Beta", html)
        self.assertIn("Gamma", html)

    def test_empty_query_shows_full_list(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": ""})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Alpha", html)
        self.assertIn("Beta", html)
        self.assertIn("Gamma", html)

    def test_whitespace_only_query_shows_full_list(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "   "})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Alpha", html)
        self.assertIn("Beta", html)
        self.assertIn("Gamma", html)

    def test_no_match_shows_message(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "zzznonexistentzzz"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("No notes match", html)

    def test_result_links_point_to_edit_pages(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "Alpha"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn(f'href="/notes/{self.note_a.pk}/edit/"', html)

    def test_search_does_not_modify_notes(self):
        count_before = Note.objects.count()
        self.client.get(reverse("notepad:note_list"), {"q": "Alpha"})
        self.assertEqual(Note.objects.count(), count_before)

    def test_search_query_preserved_in_input(self):
        resp = self.client.get(reverse("notepad:note_list"), {"q": "Beta"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('value="Beta"', html)


class ImportTests(TestCase):
    """Tests for the file import feature."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.txt_content = b"Hello, this is plain text."
        self.md_content = b"# Hello\n\nThis is **markdown**."

    def _get_csrf_token(self):
        resp = self.client.get(reverse("notepad:note_list"))
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.content.decode())
        return match.group(1) if match else ""

    def test_valid_txt_import(self):
        """Valid .txt file import creates a note and redirects."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("test.txt", self.txt_content, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.title, "test")
        self.assertEqual(note.format_type, "txt")
        self.assertEqual(note.content, "Hello, this is plain text.")

    def test_valid_md_import(self):
        """Valid .md file import creates a note and redirects."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("readme.md", self.md_content, content_type="text/markdown")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.title, "readme")
        self.assertEqual(note.format_type, "md")
        self.assertEqual(note.content, "# Hello\n\nThis is **markdown**.")

    def test_import_derives_title_from_filename(self):
        """Title is derived from the filename without extension."""
        csrf = self._get_csrf_token()
        self.client.post(
            reverse("notepad:note_import"),
            {
                "csrfmiddlewaretoken": csrf,
                "file": SimpleUploadedFile("my notes (2024).txt", self.txt_content, content_type="text/plain"),
            },
        )
        note = Note.objects.last()
        self.assertEqual(note.title, "my notes (2024)")

    def test_import_empty_file(self):
        """Empty file import creates a note with empty content."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("empty.txt", b"", content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.content, "")

    def test_unsupported_extension_rejected(self):
        """Files with unsupported extensions are rejected."""
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("script.py", b"print('hello')", content_type="text/x-python")},
        )
        self.assertEqual(resp.status_code, 200)  # re-renders list with error
        self.assertContains(resp, "Unsupported file type")
        self.assertEqual(Note.objects.count(), 0)

    def test_oversized_file_rejected(self):
        """Files exceeding 1 MiB are rejected."""
        csrf = self._get_csrf_token()
        large_content = b"x" * (1 * 1024 * 1024 + 1)
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("big.txt", large_content, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "too large")
        self.assertEqual(Note.objects.count(), 0)

    def test_invalid_encoding_rejected(self):
        """Binary content that cannot be decoded as text is rejected."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        # Bytes that fail UTF-8-sig and CP1252; Latin-1 decodes them but C1
        # control characters (U+0080-U+009F) trigger the binary heuristic.
        bad_bytes = b"\xff\xfe\x80\x81"
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("bad.txt", bad_bytes, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)

    def test_latin1_fallback_accepts_valid_text(self):
        """Latin-1 fallback accepts files with bytes 0x80-0xFF that are printable."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        # Bytes 0xC0-0xFF are all printable in Latin-1 (accents, etc.)
        latin1_text = bytes(range(0xC0, 0xFF + 1))
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("latin1.txt", latin1_text, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.content, latin1_text.decode("latin-1"))

    def test_latin1_fallback_rejects_c1_controls(self):
        """Latin-1-decoded C1 control characters (U+0080-U+009F) are rejected."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        # Bytes 0x80-0x9F decode to C1 control chars in Latin-1 — never valid in text.
        c1_bytes = bytes(range(0x80, 0xA0))
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("c1.txt", c1_bytes, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)

    def test_high_nonprintable_ratio_rejected(self):
        """Content with >5\% non-printable chars (excl. whitespace) is rejected."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        # Mix printable and null/control bytes so non-printable ratio exceeds 5%.
        # 10 null bytes + 100 printable = 110 total, 10 non-printable = 9.1%
        payload = b"\x00" * 10 + b"x" * 100
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("noisy.txt", payload, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)

    def test_failed_encoding_import_creates_no_note(self):
        """When import fails due to encoding, no Note is created."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {
                "csrfmiddlewaretoken": csrf,
                "file": SimpleUploadedFile("bad.txt", b"\xff\xfe\x80\x81", content_type="text/plain"),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)

    def test_invalid_derived_title_rejected(self):
        """Filename that yields an invalid title is rejected."""
        csrf = self._get_csrf_token()
        # Filename with only extension and no stem
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile(".txt", self.txt_content, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "valid title")
        self.assertEqual(Note.objects.count(), 0)

    def test_csrf_enforcement(self):
        """Import requires a valid CSRF token."""
        resp = self.client.post(
            reverse("notepad:note_import"),
            {
                "file": SimpleUploadedFile("test.txt", self.txt_content, content_type="text/plain"),
            },
        )
        self.assertEqual(resp.status_code, 403)


    def test_valid_utf8_import(self):
        """Valid UTF-8 text imports successfully."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("utf8.txt", b"Hello world", content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.content, "Hello world")

    def test_valid_utf8_non_english_import(self):
        """UTF-8 with non-English characters (Japanese, etc.) imports successfully."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        japanese = "こんにちは世界"
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("japanese.txt", japanese.encode("utf-8"), content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.content, japanese)

    def test_utf8_bom_import(self):
        """UTF-8 with BOM imports successfully and BOM is stripped."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        bom_content = b"\xef\xbb\xbfHello BOM"
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("bom.txt", bom_content, content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        note = Note.objects.last()
        self.assertEqual(Note.objects.count(), count_before + 1)
        # BOM should be stripped by utf-8-sig
        self.assertEqual(note.content, "Hello BOM")

    def test_cp1252_legacy_text_import(self):
        """CP1252-encoded legacy text imports successfully."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        german = "Über Straße jäger"
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("german.txt", german.encode("cp1252"), content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), count_before + 1)
        note = Note.objects.last()
        self.assertEqual(note.content, german)

    def test_binary_null_bytes_rejected(self):
        """Binary content with null bytes is rejected."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("binary.txt", b"\x00\x01\x02\x03", content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)

    def test_high_control_char_ratio_rejected(self):
        """Content with excessive control characters is rejected."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        # 2 control chars in 11 bytes = 18% > 10% threshold
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("control.txt", b"Hello\x01\x02World", content_type="text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)

    def test_failed_import_creates_no_note(self):
        """When import fails due to encoding, no Note is created."""
        count_before = Note.objects.count()
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {
                "csrfmiddlewaretoken": csrf,
                "file": SimpleUploadedFile("binary.txt", b"\x00\x01\x02\x03", content_type="text/plain"),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "binary data")
        self.assertEqual(Note.objects.count(), count_before)


class ExportTests(TestCase):
    """Tests for the file export/download feature."""

    def setUp(self):
        self.client = Client()
        self.txt_note = Note.objects.create(
            title="Test Note", content="Hello world", format_type="txt"
        )
        self.md_note = Note.objects.create(
            title="Markdown Note", content="# Header\n\nParagraph", format_type="md"
        )

    def test_txt_downloads_with_correct_extension(self):
        """TXT notes download with .txt extension."""
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": self.txt_note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/txt; charset=utf-8")
        self.assertEqual(resp["Content-Disposition"], 'attachment; filename="Test Note.txt"')

    def test_markdown_downloads_with_correct_extension(self):
        """MD notes download with .md extension and raw Markdown."""
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": self.md_note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/md; charset=utf-8")
        self.assertEqual(resp["Content-Disposition"], 'attachment; filename="Markdown Note.md"')

    def test_download_returns_raw_content(self):
        """Download returns raw content, not rendered HTML."""
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": self.md_note.pk}))
        content = b"".join(resp.streaming_content).decode("utf-8")
        self.assertEqual(content, "# Header\n\nParagraph")
        self.assertNotIn("<h1>", content)

    def test_downloading_does_not_modify_note(self):
        """Downloading a note does not alter its content or timestamps."""
        updated_before = self.txt_note.updated_at
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": self.txt_note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.txt_note.refresh_from_db()
        self.assertEqual(self.txt_note.content, "Hello world")
        self.assertEqual(self.txt_note.updated_at, updated_before)

    def test_unsafe_title_characters_safe_in_filename(self):
        """Path separators and dangerous chars in title are sanitized."""
        dangerous = Note.objects.create(title="bad/name\\test", content="x", format_type="txt")
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": dangerous.pk}))
        self.assertEqual(resp.status_code, 200)
        # Should not contain path separators in the filename
        fd = resp["Content-Disposition"]
        self.assertNotIn("/", fd)
        self.assertNotIn("\\", fd)

    def test_nonexistent_note_returns_404(self):
        """Download for a nonexistent note returns 404."""
        fake_pk = uuid.uuid4()
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": fake_pk}))
        self.assertEqual(resp.status_code, 404)

    def test_download_preserves_content_exactly(self):
        """Download content matches stored content byte-for-byte."""
        original = "Line 1\nLine 2\nLine 3"
        note = Note.objects.create(title="Multi-line", content=original, format_type="txt")
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": note.pk}))
        self.assertEqual(b"".join(resp.streaming_content).decode("utf-8"), original)


class ImportExportIntegrationTests(TestCase):
    """End-to-end tests for import and export together."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _get_csrf_token(self):
        resp = self.client.get(reverse("notepad:note_list"))
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.content.decode())
        return match.group(1) if match else ""

    def test_import_then_export_roundtrip(self):
        """Import a file, then export it — content should match."""
        original_content = "# Round Trip\n\nThis is **test** content."
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("roundtrip.md", original_content.encode(), content_type="text/markdown")},
        )
        self.assertEqual(resp.status_code, 302)

        note = Note.objects.get(title="roundtrip")
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content).decode("utf-8"), original_content)

    def test_import_shown_on_list_page(self):
        """Import form is present on the list page."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="file"')
        self.assertContains(resp, "Import File")

    def test_download_button_on_editor(self):
        """Download button is present on the editor page."""
        note = Note.objects.create(title="Editor Test", content="x", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Download")
        self.assertIn(str(note.pk), resp.content.decode())

    def test_import_error_message_shown_on_list(self):
        """Import errors are displayed on the list page."""
        csrf = self._get_csrf_token()
        resp = self.client.post(
            reverse("notepad:note_import"),
            {"csrfmiddlewaretoken": csrf, "file": SimpleUploadedFile("bad.py", b"x", content_type="text/x-python")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unsupported file type")


class UnsavedChangesEditorTests(TestCase):
    """Regression tests for unsaved-changes tracking on the editor page."""

    def setUp(self):
        self.client = Client()

    def test_editor_page_contains_dirty_tracking_script(self):
        """The editor HTML must include the beforeunload/dirty-state JS."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("isDirty", html)
        self.assertIn("beforeunload", html)

    def test_existing_note_editor_contains_dirty_tracking_script(self):
        """An existing note editor must also include dirty-state JS."""
        note = Note.objects.create(title="Existing", content="hello", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("isDirty", html)
        self.assertIn("beforeunload", html)

    def test_editor_renders_with_initial_clean_state_for_existing_note(self):
        """Loading an existing note should not mark it dirty by default."""
        note = Note.objects.create(title="Load Test", content="saved text", format_type="md")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # The initialTitle and initialContent variables should be set from the loaded values
        self.assertIn("initialTitle", html)
        self.assertIn("initialContent", html)

    def test_save_as_button_triggers_form_submission(self):
        """Save As button must still submit the form normally."""
        note = Note.objects.create(title="SA Test", content="content", format_type="txt")
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": note.pk}),
            {"action": "saveas", "new_title": "Copy SA", "content": "content"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 2)

    def test_save_button_triggers_form_submission(self):
        """Save button must still submit the form normally."""
        note = Note.objects.create(title="Save Test", content="old", format_type="txt")
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": note.pk}),
            {"action": "save", "title": "Updated", "content": "new", "format_type": "txt"},
        )
        self.assertEqual(resp.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.title, "Updated")
        self.assertEqual(note.content, "new")

    def test_validation_errors_do_not_alter_database(self):
        """Failed save must preserve the original note content (dirty state preserved)."""
        note = Note.objects.create(title="Error Test", content="original", format_type="txt")
        count_before = Note.objects.count()
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": note.pk}),
            {"action": "save", "title": "", "content": "changed", "format_type": "txt"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Note.objects.count(), count_before)
        note.refresh_from_db()
        self.assertEqual(note.content, "original")

    def test_save_as_does_not_modify_source_note(self):
        """Save As must create a copy without altering the original."""
        note = Note.objects.create(title="Source", content="source content", format_type="md")
        pk = note.pk
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": pk}),
            {"action": "saveas", "new_title": "Copy SA", "content": "source content"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 2)
        note.refresh_from_db()
        self.assertEqual(note.title, "Source")
        self.assertEqual(note.content, "source content")




class KeyboardShortcutTests(TestCase):
    """Verify keyboard shortcut markup and script are present on the editor page."""

    def setUp(self):
        self.client = Client()

    def test_editor_contains_keyboard_shortcut_hint(self):
        """The editor page must render a shortcut-hint element."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="shortcut-hint"', html)

    def test_editor_contains_keyboard_shortcut_script(self):
        """The editor page must include the keyboard shortcut event listener."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("keydown", html)
        self.assertIn("_isSaving", html)
        self.assertIn("saveas-modal", html)

    def test_editor_contains_ctrl_s_handler(self):
        """Ctrl+S handler must be present in the editor script."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('value="save"]', html)
        self.assertIn("key === 's' && !e.shiftKey", html)

    def test_editor_contains_ctrl_shift_s_handler(self):
        """Ctrl+Shift+S handler must be present in the editor script."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('value="saveas"]', html)
        self.assertIn("key === 's' && e.shiftKey", html)

    def test_editor_contains_escape_handler(self):
        """Escape handler must be present in the editor script."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("key === 'escape'", html)

    def test_existing_note_editor_contains_shortcut_hint(self):
        """An existing note editor must also render the shortcut hint."""
        note = Note.objects.create(title="Shortcut Test", content="x", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="shortcut-hint"', html)

    def test_list_page_has_no_shortcut_hint(self):
        """The list page must not contain the shortcut hint (editor-only)."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertNotIn('id="shortcut-hint"', html)

    def test_save_button_still_present(self):
        """The Save button must still exist alongside the new shortcut hint."""
        note = Note.objects.create(title="Btn Test", content="x", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('name="action" value="save"', html)

    def test_saveas_button_still_present(self):
        """The Save As button must still exist alongside the new shortcut hint."""
        note = Note.objects.create(title="Btn Test", content="x", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('name="action" value="saveas"', html)

    def test_shortcut_hint_uses_platform_modifier(self):
        """The script must detect platform and use Cmd or Ctrl in the hint."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("_platformModifier", html)
        self.assertIn("navigator.userAgent", html)


class KeyboardShortcutNoInterferenceTests(TestCase):
    """Verify keyboard shortcuts do not break normal editor behavior."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(title="Interference Test", content="hello", format_type="md")

    def test_editor_renders_with_all_expected_elements(self):
        """All expected UI elements must be present on the editor page."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="editor"', html)
        self.assertIn('id="title-input"', html)
        self.assertIn('id="format-select"', html)
        self.assertIn('id="preview-btn"', html)
        self.assertIn('id="saveas-modal"', html)
        self.assertIn('id="shortcut-hint"', html)

    def test_save_as_modal_still_present(self):
        """Save As modal must still be present on the page."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="saveas-modal"', html)
        self.assertIn('id="saveas-confirm"', html)
        self.assertIn('id="saveas-cancel"', html)

    def test_dirty_tracking_still_present(self):
        """Unsaved-changes tracking must still be present alongside shortcuts."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("isDirty", html)
        self.assertIn("beforeunload", html)
        self.assertIn("initialTitle", html)
        self.assertIn("initialContent", html)

    def test_preview_js_still_present(self):
        """Live preview JavaScript must still be present alongside shortcuts."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("debouncedPreview", html)
        self.assertIn("_previewSeq", html)
        # The URL name resolves to /notes/preview/raw/ in the rendered HTML
        self.assertIn("preview/raw", html)

    def test_save_still_works_via_button(self):
        """Manual Save button click must still work."""
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "save", "title": "Updated", "content": "new content", "format_type": "md"},
        )
        self.assertEqual(resp.status_code, 302)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Updated")
        self.assertEqual(self.note.content, "new content")

    def test_save_as_still_works_via_button(self):
        """Manual Save As button click must still work."""
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "saveas", "new_title": "Copy", "content": "hello"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.count(), 2)


class ManualBrowserChecks:
    """
    Browser-specific behaviors that cannot be tested with Django's test client.
    Run these checks manually in a browser after deploying the changes.

    1. Unsaved-changes warning on page unload:
       - Open any note editor (existing or new).
       - Type something in the title or content area.
       - Attempt to navigate away (click a sidebar link, close the tab, reload the page).
       - Expected: browser shows an unsaved-changes confirmation dialog.
       - Click "Cancel" / "Stay on page" — user remains on the editor.
       - Click "Leave" / "Discard changes" — navigation proceeds.

    2. No warning when clean:
       - Open a note editor without making any edits.
       - Attempt to navigate away.
       - Expected: no warning dialog; navigation proceeds normally.

    3. Warning clears after successful Save:
       - Edit a note, then click "Save".
       - After redirect to the list page and re-opening the same note,
         editing it again should trigger the warning as expected.
       - (The warning is per-session; after a successful save the user leaves
         the editor page, so the state resets on reload.)

    4. Warning preserved after failed save (validation error):
       - Edit a note, change the title to empty, click "Save".
       - The page re-renders with the validation error.
       - Attempt to navigate away.
       - Expected: warning dialog still appears (dirty state preserved).

    5. Save As does not trigger warning:
       - Edit a note, then click "Save As" and confirm.
       - Expected: no unsaved-changes warning; the form submits normally.

    6. Markdown live preview continues to work:
       - Open a Markdown note editor.
       - Type markdown content in the editor.
       - Expected: the preview pane updates within ~300ms of typing stopping.
       - The dirty-state tracking must not interfere with the debounced preview.

    7. In-app navigation interception:
       - While on the editor page with unsaved changes, click a sidebar note link.
       - Expected: browser shows the unsaved-changes warning (via beforeunload).
       - If confirmed, navigation proceeds to the selected note.
    """
    pass


class RootURLTests(TestCase):
    """Verify the root URL redirects to /notes/ and other routes are preserved."""

    def setUp(self):
        self.client = Client()

    def test_root_redirects_to_notes_list(self):
        """GET / should return a redirect (302) to /notes/."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/notes/")

    def test_root_redirect_follows_to_note_list_page(self):
        """Following the root redirect should display the Notepad list page."""
        resp = self.client.get("/", follow=True)
        self.assertEqual(resp.status_code, 200)
        # The list page should render without error (may be empty of notes).
        self.assertNotEqual(resp.content.decode(), "")

    def test_notes_list_still_accessible(self):
        """GET /notes/ continues to work."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)

    def test_admin_route_still_registered(self):
        """GET /admin/ is still reachable (returns redirect to login on unauth)."""
        resp = self.client.get("/admin/")
        # Without credentials Django redirects to the login page.
        self.assertIn(resp.status_code, [302, 200])

    def test_unknown_path_returns_404(self):
        """Unknown URLs still return 404."""
        resp = self.client.get("/nonexistent-path-12345/")
        self.assertEqual(resp.status_code, 404)


class UXRedesignTests(TestCase):
    """Tests for the NP-019 UX redesign acceptance criteria."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(title="Test Note", content="hello", format_type="txt")

    # ── 1. Workspace fills viewport (no unused gray area) ──────────────────────

    def test_editor_page_has_full_height_layout(self):
        """The editor page must use app-container with full viewport height."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('class="app-container"', html)
        self.assertIn('class="editor-area"', html)

    def test_editor_page_has_title_bar(self):
        """The editor page must have a title-bar section."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('class="title-bar"', html)

    def test_editor_page_has_toolbar(self):
        """The editor page must have a toolbar section."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('class="toolbar"', html)

    # ── 2. First-time user can identify create/import ───────────────────────────

    def test_list_page_has_new_note_button(self):
        """The list page must show a prominent New Note button."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('btn-new', html)
        self.assertIn('New Note', html)

    def test_list_page_has_import_action(self):
        """The list page must have an Import Notes action."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('Import Notes', html)
        self.assertIn('import-area', html)

    # ── 3. First-time user can identify save/export ─────────────────────────────

    def test_editor_has_save_button(self):
        """The editor must have a primary Save button."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('btn-primary', html)
        self.assertIn('value="save"', html)

    def test_editor_has_save_as_button(self):
        """The editor must have a Save As button."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('value="saveas"', html)

    def test_editor_has_download_button(self):
        """The editor must have a Download button for existing notes."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('btn-download', html)
        self.assertIn('Download', html)

    # ── 4. Plain Text and Markdown are visually distinguishable ─────────────────

    def test_format_selector_present_on_editor(self):
        """The editor must have a format selector."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="format-select"', html)
        self.assertIn('Plain Text', html)
        self.assertIn('Markdown', html)

    def test_format_selector_present_on_new_note(self):
        """The new-note editor must also have a format selector."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="format-select"', html)

    def test_markdown_note_has_preview_button(self):
        """Markdown notes must show a preview button."""
        md_note = Note.objects.create(title="MD Note", content="# Hello", format_type="md")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": md_note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="preview-btn"', html)

    def test_plain_text_note_preview_button_starts_hidden(self):
        """Plain text notes keep preview available for switching to Markdown, but hidden."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="preview-btn"', html)
        self.assertRegex(html, r'id="preview-btn"[^>]*class="[^"]*hidden')

    # ── 5. Markdown preview toggle is clear ─────────────────────────────────────

    def test_md_note_has_split_mode_by_default(self):
        """A Markdown note editor must start in split-mode."""
        md_note = Note.objects.create(title="Split Test", content="# Hi", format_type="md")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": md_note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('split-mode', html)

    def test_txt_note_has_no_preview_pane(self):
        """A plain text note must not render a visible preview pane."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # The preview-pane div should exist but be hidden for txt
        self.assertIn('id="preview-pane"', html)
        self.assertIn('hidden', html)

    # ── 6. Selected note is obvious in sidebar ──────────────────────────────────

    def test_active_note_has_active_class(self):
        """The currently selected note must have the 'active' class in the sidebar."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('class="file-item active"', html)

    def test_non_active_note_lacks_active_class(self):
        """Non-selected notes must not have the 'active' class."""
        other = Note.objects.create(title="Other", content="x", format_type="txt")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # The active note should be present and active
        self.assertIn(self.note.title, html)
        # Non-active notes should exist in sidebar but without active class
        import re
        items = re.findall(r'<li[^>]*class="file-item[^"]*"[^>]*>', html)
        active_items = [i for i in items if 'active' in i]
        self.assertEqual(len(active_items), 1)
        self.assertIn(str(self.note.pk), active_items[0])

    # ── 7. Empty states provide useful guidance ─────────────────────────────────

    def test_empty_list_has_helpful_message(self):
        """The empty list must show a helpful message with create/import guidance."""
        Note.objects.all().delete()
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('Ready for your next note?', html)
        self.assertIn('Import a file', html)

    def test_empty_search_has_guidance(self):
        """Empty search results must show a guidance message."""
        resp = self.client.get(reverse("notepad:note_list"), {"q": "zzznonexistentzzz"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("No notes match", html)

    # ── 8. Save status and unsaved changes are understandable ───────────────────

    def test_editor_has_save_status_indicator(self):
        """The editor must include a save-status element."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="save-status"', html)
        self.assertIn('status-dot', html)

    def test_editor_has_unsaved_changes_tracking(self):
        """The editor must include unsaved-changes tracking JS."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('isDirty', html)
        self.assertIn('beforeunload', html)

    def test_new_note_editor_has_unsaved_changes_tracking(self):
        """The new-note editor must also include unsaved-changes tracking."""
        resp = self.client.get(reverse("notepad:note_new"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('isDirty', html)
        self.assertIn('beforeunload', html)

    # ── 9. Desktop and mobile layouts ───────────────────────────────────────────

    def test_list_page_has_mobile_sidebar_toggle(self):
        """The list page must include a mobile sidebar toggle button."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="sidebar-toggle"', html)
        self.assertIn('sidebar-overlay', html)

    def test_editor_page_has_mobile_sidebar_toggle(self):
        """The editor page must include a mobile sidebar toggle button."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="sidebar-toggle"', html)

    def test_list_page_has_app_container(self):
        """The list page must use app-container for layout."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('class="app-container"', html)

    # ── 10. All existing functionality continues working ────────────────────────

    def test_create_note_via_new_endpoint(self):
        resp = self.client.post(reverse("notepad:note_new"), {
            "title": "UX Test", "content": "hello", "format_type": "txt"
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.filter(title="UX Test").count(), 1)

    def test_save_via_edit_endpoint(self):
        resp = self.client.post(
            reverse("notepad:note_edit", kwargs={"pk": self.note.pk}),
            {"action": "save", "title": "Updated UX", "content": "new content", "format_type": "md"}
        )
        self.assertEqual(resp.status_code, 302)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Updated UX")
        self.assertEqual(self.note.format_type, "md")

    def test_delete_via_delete_endpoint(self):
        other = Note.objects.create(title="Delete Me", content="x", format_type="txt")
        resp = self.client.post(reverse("notepad:note_delete", kwargs={"pk": other.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Note.objects.filter(pk=other.pk).count(), 0)

    def test_download_txt_note(self):
        txt_note = Note.objects.create(title="DL Test", content="download me", format_type="txt")
        resp = self.client.get(reverse("notepad:note_download", kwargs={"pk": txt_note.pk}))
        self.assertEqual(resp.status_code, 200)
        body = b"".join(resp.streaming_content).decode()
        self.assertIn("download me", body)

    def test_import_txt_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("import_test.txt", b"imported content", content_type="text/plain")
        resp = self.client.post(reverse("notepad:note_import"), {"file": f})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Note.objects.filter(title="import_test").exists())

    def test_import_md_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("import_test.md", b"# Imported", content_type="text/markdown")
        resp = self.client.post(reverse("notepad:note_import"), {"file": f})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Note.objects.filter(title="import_test").exists())

    def test_search_works(self):
        Note.objects.create(title="Searchable", content="find me", format_type="txt")
        resp = self.client.get(reverse("notepad:note_list"), {"q": "Searchable"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Searchable.txt")

    def test_markdown_preview_toggle_present(self):
        md_note = Note.objects.create(title="Preview Test", content="# Hello", format_type="md")
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": md_note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="preview-btn"', html)

    def test_save_as_modal_present(self):
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="saveas-modal"', html)

    def test_csrf_protection_present(self):
        """CSRF token must be present on all forms."""
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('csrfmiddlewaretoken', html)

    def test_delete_confirmation_page_renders(self):
        resp = self.client.get(reverse("notepad:note_delete", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Are you sure")


class MobileLayoutTests(TestCase):
    """Verify mobile-responsive HTML structure is present."""

    def setUp(self):
        self.client = Client()
        self.note = Note.objects.create(title="Mobile Test", content="x", format_type="txt")

    def test_list_has_sidebar_overlay(self):
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('sidebar-overlay', html)

    def test_editor_has_sidebar_overlay(self):
        resp = self.client.get(reverse("notepad:note_edit", kwargs={"pk": self.note.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('sidebar-overlay', html)

    def test_list_has_import_form_in_editor_area(self):
        """Import form must be inside the editor-area main element."""
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Import form should be inside <main class="editor-area">
        self.assertIn('import-area', html)

    def test_empty_state_has_helpful_text(self):
        """Empty state on list page must guide the user."""
        Note.objects.all().delete()
        resp = self.client.get(reverse("notepad:note_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('Ready for your next note?', html)
        self.assertIn('+ New Note', html)
        self.assertIn('Import a file', html)

class NP019CoreFunctionalityRegressionTests(TestCase):
    """Regression coverage for editor submission and Save As fixes."""

    def setUp(self):
        self.note = Note.objects.create(
            title="Original",
            content="database version",
            format_type="txt",
        )
        self.edit_url = reverse("notepad:note_edit", kwargs={"pk": self.note.pk})

    def test_save_button_is_associated_with_editor_form(self):
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="editor-form"', html)
        self.assertIn('form="editor-form" name="action" value="save"', html)

    def test_save_as_copies_current_unsaved_editor_values(self):
        response = self.client.post(self.edit_url, {
            "action": "saveas",
            "new_title": "Current Copy",
            "title": "Unsaved title",
            "content": "latest text from the editor",
            "format_type": "md",
        })
        self.assertRedirects(response, reverse("notepad:note_list"))
        copy = Note.objects.get(title="Current Copy")
        self.assertEqual(copy.content, "latest text from the editor")
        self.assertEqual(copy.format_type, "md")
        self.note.refresh_from_db()
        self.assertEqual(self.note.content, "database version")
        self.assertEqual(self.note.title, "Original")

    def test_save_as_invalid_title_preserves_editor_values_and_sidebar(self):
        response = self.client.post(self.edit_url, {
            "action": "saveas",
            "new_title": "   ",
            "title": "Edited title",
            "content": "unsaved body",
            "format_type": "md",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("notes", response.context)
        self.assertContains(response, "Edited title")
        self.assertContains(response, "unsaved body")
        self.assertContains(response, 'id="sidebar"')
        self.assertEqual(Note.objects.count(), 1)

    def test_save_as_rejects_invalid_format_without_creating_copy(self):
        response = self.client.post(self.edit_url, {
            "action": "saveas",
            "new_title": "Bad Format Copy",
            "title": "Original",
            "content": "text",
            "format_type": "html",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Note.objects.count(), 1)

    def test_import_navigation_targets_list_page_anchor(self):
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/notes/#import-area"')



class NP020ReleaseReadinessTests(TestCase):
    def setUp(self):
        self.import_url = reverse("notepad:note_import")

    def upload(self, name="meeting.md", content=b"# Meeting notes"):
        return SimpleUploadedFile(name, content, content_type="text/markdown")

    def test_successful_import_redirects_directly_to_new_note(self):
        response = self.client.post(self.import_url, {"file": self.upload()})
        note = Note.objects.get(title="meeting", format_type="md")
        self.assertRedirects(
            response, reverse("notepad:note_edit", kwargs={"pk": note.pk})
        )
        self.assertEqual(note.content, "# Meeting notes")

    def test_duplicate_import_gets_numbered_title_and_preserves_existing_note(self):
        original = Note.objects.create(
            title="meeting", content="do not overwrite", format_type="md"
        )
        response = self.client.post(self.import_url, {"file": self.upload()})
        imported = Note.objects.get(title="meeting (2)", format_type="md")
        self.assertEqual(original.content, "do not overwrite")
        self.assertEqual(imported.content, "# Meeting notes")
        self.assertRedirects(
            response, reverse("notepad:note_edit", kwargs={"pk": imported.pk})
        )
        self.assertContains(
            self.client.get(reverse("notepad:note_edit", kwargs={"pk": imported.pk})),
            "Imported as meeting (2).md",
        )

    def test_second_duplicate_import_uses_next_available_suffix(self):
        Note.objects.create(title="meeting", content="one", format_type="md")
        Note.objects.create(title="meeting (2)", content="two", format_type="md")
        self.client.post(self.import_url, {"file": self.upload()})
        self.assertTrue(Note.objects.filter(title="meeting (3)", format_type="md").exists())

    def test_import_page_does_not_show_success_before_an_import(self):
        response = self.client.get(reverse("notepad:note_list"))
        self.assertNotContains(response, "Import successful.")

    def test_import_page_explains_supported_types_and_size(self):
        response = self.client.get(reverse("notepad:note_list"))
        self.assertContains(response, "TXT or MD")
        self.assertContains(response, "Maximum 1 MiB")
        self.assertContains(response, 'id="import-file"')
        self.assertContains(response, 'id="import-submit"')

    def test_import_error_is_visible_without_success_message(self):
        bad_file = SimpleUploadedFile("archive.pdf", b"%PDF-1.4", content_type="application/pdf")
        response = self.client.post(self.import_url, {"file": bad_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only .txt and .md files are accepted")
        self.assertNotContains(response, "Import successful.")

    def test_new_note_preview_control_is_present_but_hidden_for_txt(self):
        response = self.client.get(reverse("notepad:note_new"))
        self.assertContains(response, 'id="preview-btn"')
        self.assertRegex(
            response.content.decode(),
            r'id="preview-btn"[^>]*class="[^"]*hidden',
        )

    def test_editor_switches_preview_when_markdown_is_selected(self):
        response = self.client.get(reverse("notepad:note_new"))
        self.assertContains(response, "formatSelect.addEventListener('change'")
        self.assertContains(response, "previewBtn.classList.toggle('hidden', !isMarkdown)")
        self.assertContains(response, "debouncedPreview()")


class NP020NavigationPolishTests(TestCase):
    def test_empty_search_offers_clear_search_action(self):
        response = self.client.get(reverse("notepad:note_list"), {"q": "missing-note"})
        self.assertContains(response, "No notes found")
        self.assertContains(response, "Clear search")
        self.assertContains(response, 'href="/notes/"')

    def test_mobile_navigation_exposes_accessible_state(self):
        response = self.client.get(reverse("notepad:note_list"))
        self.assertContains(response, 'aria-controls="sidebar"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, "event.key === 'Escape'")

class NP020AccessibilityPolishTests(TestCase):
    def test_note_delete_action_is_visible_and_has_accessible_name(self):
        note = Note.objects.create(title="accessible-note", content="text", format_type="txt")
        response = self.client.get(reverse("notepad:note_list"))
        self.assertContains(response, 'class="delete-form"')
        self.assertContains(response, f'aria-label="Delete {note.filename}"')
        self.assertNotContains(response, 'class="delete-form" data-confirm="Delete accessible-note.txt?" style="display:none;"')

    def test_save_as_dialog_exposes_dialog_semantics_and_keyboard_support(self):
        note = Note.objects.create(title="dialog-note", content="text", format_type="txt")
        response = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, 'aria-modal="true"')
        self.assertContains(response, 'aria-labelledby="saveas-heading"')
        self.assertContains(response, "if (modalIsOpen && e.key === 'Escape')")
        self.assertContains(response, "if (modalIsOpen && e.key === 'Tab')")

    def test_format_change_marks_editor_as_unsaved(self):
        note = Note.objects.create(title="format-note", content="text", format_type="txt")
        response = self.client.get(reverse("notepad:note_edit", kwargs={"pk": note.pk}))
        self.assertContains(response, "formatSelect.addEventListener('change', () => setDirty(true))")
