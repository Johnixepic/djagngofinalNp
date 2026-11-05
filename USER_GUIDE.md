# User Guide — Django Notepad Application

A simple, powerful note-taking application for plain text and Markdown documents.

---

## Getting Started

### First Login

1. Open http://localhost:8000 (or your deployment URL)
2. You'll see an empty notes list with a **+ New Note** button
3. Click the button to create your first note

---

## Creating Notes

### Basic Creation
1. Click **+ New Note** in the sidebar
2. Enter a filename in the title field (e.g., `meeting-notes`)
3. Choose format: **Plain Text** or **Markdown**
4. Type your content in the editor
5. Click **Save** or press `Ctrl+S` / `Cmd+S`

### Filename Rules
- No spaces (use hyphens or underscores)
- No forward slashes (`/`) or backslashes (`\`)
- Max 255 characters
- Leading/trailing whitespace is trimmed

---

## Editing Notes

1. Click any note in the sidebar to open it
2. Edit the title or content as needed
3. Click **Save** to persist changes
4. Changes are automatic on save — no auto-save

### Unsaved Changes Warning
If you try to leave the page with unsaved edits, the browser will prompt you to confirm.

---

## Save As

Create a copy of a note with a new name:

1. Open the note you want to copy
2. Click **Save As**
3. Enter a new filename in the modal
4. Click **Save As** again
5. You're redirected to the new note; the original remains unchanged

---

## Deleting Notes

1. Open the note you want to delete
2. Click **Delete**
3. Confirm deletion in the dialog
4. The note is removed immediately and cannot be recovered

**Warning:** Deletion is permanent. There is no trash or recycle bin.

---

## Searching

The sidebar includes a search box that filters notes by:
- Title (primary)
- Content (secondary)

Search is case-insensitive and partial-match. Results update as you type.

---

## Importing Files

Import TXT or Markdown files into the editor:

1. Create a new note or open an existing one
2. Use the import control in the editor toolbar
3. Select your file (TXT or MD only)
4. File content loads into the editor
5. Save to persist as a note

### Supported Formats
- Plain text (`.txt`)
- Markdown (`.md`)

### Encoding
UTF-8 is preferred. The app attempts fallback encodings for legacy files.

---

## Downloading Notes

1. Open any note
2. Click **Download** in the toolbar
3. A file with the correct extension downloads to your computer

Downloaded files contain raw content (not HTML previews).

---

## Markdown Preview

### Viewing Preview
- MD notes open with a split-pane layout by default
- The right pane shows rendered HTML
- Preview updates as you type (with slight delay)

### Toggling Preview
Click the **Preview** button to hide or show the preview pane.

### Sanitization
All Markdown output is sanitized to prevent XSS attacks. HTML tags in your Markdown are escaped.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` / `Cmd+S` | Save current note |
| `Ctrl+Shift+S` / `Cmd+Shift+S` | Open Save As dialog |
| `Escape` | Close Save As modal |

### Editor Shortcuts
Standard text editing shortcuts work in the editor:
- `Ctrl+A` — Select all
- `Ctrl+C` — Copy
- `Ctrl+V` — Paste
- `Ctrl+X` — Cut
- `Ctrl+Z` — Undo
- `Ctrl+Y` — Redo

---

## Mobile Usage

The app is responsive and works on mobile devices:
- Sidebar collapses to a top bar on narrow screens
- Editor takes full width
- Touch-friendly buttons and inputs

---

## Supported Formats

| Format | Extension | Features |
|--------|-----------|----------|
| Plain Text | `.txt` | Basic text, no formatting |
| Markdown | `.md` | Rich formatting, live preview |

### Markdown Support
- Headings (`#`, `##`, etc.)
- Emphasis (`**bold**`, `*italic*`)
- Lists (ordered and unordered)
- Code blocks with syntax highlighting
- Tables
- Links and images

---

## File Size Limits

There is no hard limit on note content size. However:
- Very large files may take longer to load
- Browser memory limits apply to client-side processing
- Consider splitting very large documents into multiple notes

---

## Tips

1. **Use descriptive filenames** — they appear in the sidebar and downloads
2. **Choose format wisely** — use Markdown for formatted notes, TXT for simple text
3. **Save regularly** — browser crashes can lose unsaved work
4. **Backup your database** — use `./scripts/backup.sh` for production deployments
5. **Use search effectively** — partial matches work; "meeting" finds "team-meeting-notes"

---

## Troubleshooting

### Can't Save a Note
- Check the title field for errors (red border indicates issue)
- Ensure you have a valid filename
- Check browser console for JavaScript errors

### Preview Not Showing
- Ensure the note format is set to Markdown
- Check that JavaScript is enabled in your browser
- Try refreshing the page

### Import Fails
- Verify the file is TXT or MD format
- Check file encoding (UTF-8 recommended)
- Ensure the file is not corrupted

### Search Returns Nothing
- Verify the note exists and hasn't been deleted
- Check spelling in the search box
- Try a shorter search term

---

## Security Note

This application is designed for single-user, trusted environments. There is no authentication. Do not deploy without additional security measures if exposed to untrusted users.
