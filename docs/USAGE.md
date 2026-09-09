# Using Notryn

Workspace reference for 0.2.0-beta.8. See [installation](INSTALL.md) for package availability.

## Your workspace

- Library with the current folder name, a back arrow, New note and New folder buttons, drag-and-drop, filtering and recent notes.
- Remove notes, folders or Brains from Notryn while keeping their files, with optional recoverable Trash and a searchable Removed items space.
- Visual note writing with selection-based formatting, an optional Markdown view, preview and explicit saving.
- Note on the left by default, a saved preference for swapping sides, and a full-width focus mode.
- Searchable command palette and a keyboard reference with clickable actions.
- Connections from `[[note-name]]`, shortest unique wikilink paths such as `[[topics/Guide]]`, and Markdown links to `.md` files. Ambiguous shortened paths are never guessed.
- A glass brain with translucent hemispheres, layered filaments, luminous notes and pulses along real note connections.
- Each opened folder lists its direct subfolders and Markdown filenames, matching the files on disk. The Brain uses the same filenames; opening a note keeps sibling dots and labels visible. Dense layers use compact, non-overlapping labels where space permits.
- Hover a label or browse with the keyboard to highlight its direct connections and gently fade unrelated items. Emphasis transitions smoothly in both directions, including quick moves between labels; dimmed names remain faintly readable. Moving the pointer away restores the open note's emphasis. Translucent highlights replace hover summaries; opening a note also brings its linked notes from other folders into the map, while the Library keeps the current folder's contents.
- Search covers every indexed note, regardless of the open folder. It matches words in filenames, paths and document titles across spaces, hyphens and accents, with exact filenames first. Search results are no longer capped at 30; the reader retains the original document title.
- Quiet glass panels, a full-width immersive brain mode, optional motion and keyboard zoom.
- Mobile navigation for Brain and Notes; creation buttons stay in the current folder.
- Brain creation includes a required location picker and shows the complete destination before creating anything.

Version `0.2.0-beta.8` supports narrow and short tiled windows. Below 900 pixels, Brain and Notes use compact navigation; resizing preserves your open note and unsaved draft. On macOS, drag an empty area of the top bar to move the window; buttons and fields remain interactive. Save confirms disk persistence before refreshing the Brain. The A and Shift A shortcuts remain unassigned.

Shortcuts use the same letters on macOS, Windows and Linux. They work outside text fields. While writing, press **Esc** first to leave the field without closing or changing the note, then use an action. **P → search an action → Enter** reaches every command; **?** searches the keyboard reference. Frequent actions also have direct keys. In a dialog, Tab/Shift Tab move between controls, arrows navigate choices and Enter confirms. No letter shortcut runs while you type.

| Action | Key |
| --- | --- |
| Notes and commands | P |
| Commands and shortcuts | ? |
| Show / hide brain (keep the open note) | H |
| Show full Brain and clear filters | Shift H |
| Choose theme | T |
| Show / hide interface hints | Shift T |
| Swap note and brain | Shift L |
| Focus note / exit focus | F |
| Immersive brain / return | Shift G |
| Create a Brain | Shift B |
| Switch Brain | B |
| Open an existing folder | O |
| New folder | Shift N |
| New note | N |
| Rename the focused note or folder | F2 |
| Move the focused note or folder | M |
| Open its actions menu | Shift M |
| Show the open note in its computer folder | Shift O |
| Review removal of the focused note or folder | D |
| Removed items: restore or remove an entry | Shift D, then Tab to the action and Enter |
| Preview note | V |
| Switch pane | W / Shift W |
| Save | S |
| Edit / finish editing | E |
| Save and return to reading | Shift S |
| Switch Write / Markdown | Shift E |
| Open formatting controls | Shift F |
| Toggle library | L |
| Filter notes | Q |
| All notes: clear filters, keep the draft | Shift Q |
| Choose a category | C, arrows, Enter; Home selects All |
| Refresh notes | R |
| Recent notes | Shift R |
| Close panel / leave field | Esc |

Swapping panes preserves unsaved text, the cursor and the reading position. Esc inside a text field leaves it while keeping the draft; outside fields it leaves focus mode or closes the current panel, asking before discarding unsaved writing. On mobile, the note already uses the full width and the layout controls are hidden.

Global NOTRYN commands do not bind Ctrl, Cmd, Alt, AltGr or Super combinations. F2 uses the familiar file-manager action to rename the focused note or folder; other function keys stay native. Browser and window-manager commands keep their native bindings outside the editor. Inside an editable note, **Ctrl/Cmd+S saves without leaving writing** and **Ctrl/Cmd+Enter toggles Preview**. The Save button and Shift S save and return to reading; Done returns when there are no changes. A failed save or newer unsaved edits keep the editor open. No autosave is enabled. Ctrl/Cmd plus scrolling keeps browser zoom; ordinary scrolling over the brain zooms the brain. Tab and Shift Tab keep native focus navigation, including in Markdown.

Buttons work without learning shortcuts. Hover over an action to see its name and, where available, its shortcut from the same command catalog used by the keyboard. Brain camera hints specify that the Brain must be focused. Turning off single-key shortcuts removes those key hints; hiding interface hints keeps the action names while removing shortcut hints. The **?** menu remains the complete searchable reference.

Tab/Shift Tab follow the visible control order, including buttons on mobile WebKit. Modal dialogs keep focus inside; at workspace edges, browser navigation remains available. Escape closes a search dialog even when its search field contains text, while respecting any operation that temporarily blocks cancellation.

Inside Write mode, standard text shortcuts are scoped to the editable field:

| Action | Key |
| --- | --- |
| Bold / italic | Ctrl/Cmd B / I |
| Insert or edit a link | Ctrl/Cmd K |
| Strikethrough | Ctrl/Cmd Shift X |
| Undo / redo | Ctrl/Cmd Z / Shift Z (also Ctrl/Cmd Y for redo) |
| Copy / cut / paste / select all | Ctrl/Cmd C / X / V / A (native) |
| Line break | Shift Enter |

For headings, lists, quotes and code: select text, then **Esc → P → action name → Enter**. Selection stays in the visual editor while the palette has focus. The same actions appear in **?** under Formatting. **Esc → Shift F** opens the compact formatting toolbar; use Tab, arrows and Enter there. These formatting commands require Write mode; Markdown remains a plain text editor.

Open **Commands and shortcuts** and turn off **Single-key shortcuts** if they overlap with your keyboard extensions or assistive tools. The choice is saved in this browser. Buttons, the palette, Tab/Enter and arrow navigation remain available. You can always reach the keyboard icon with Tab to re-enable shortcuts. Custom browser, extension or desktop configurations may reserve additional keys.

### Brain and library without a mouse

Use **Shift H** to show the complete Brain, close the note and center the view; unsaved writing asks for a decision first. **H** only shows/hides the Brain and keeps your draft. **All** at the beginning of the categories, or **Shift Q**, clears filters without closing the note. **C** focuses the category choices, arrows move between them and Enter applies one; Home followed by Enter returns to All. **0** only centers the camera and resets zoom.

Press **G** outside text fields to focus the brain. While it has focus:

| Action | Key |
| --- | --- |
| Rotate / tilt | Arrow keys |
| Zoom in / out | + (or =) / − |
| Center and reset zoom | 0 |
| Pause / resume motion | Space |
| Next / previous note | J / K, or Page Down / Page Up |
| Open the highlighted note | Enter |
| Leave brain controls | Tab or W |

Use **Shift G** outside text fields, or **Immersive brain / return** in the command palette, to hide the library and note pane without closing your draft. **Esc** restores the previous layout and writing focus. Opening a note from the immersive brain brings its pane back. On mobile, this command opens the brain view.

Selecting a note gives its label a translucent theme accent. Directly connected notes use a softer shade of the same color; other labels and folder colors remain visible. Selected connections carry up to three brighter travelling points per line, with a bounded particle count for dense Brains.

Pausing freezes rotation, pulses and ambient effects. The pause preference is saved in the browser, and reduced-motion preferences are respected. Automatic rotation is suspended while the brain has focus to make selection easier. J/K navigation respects the current filter and orders notes alphabetically.

In the library, ↑/↓ move between rows, ←/→ collapse or expand folders, Home/End move to the first/last row, and Enter opens a note. After filtering with Q, use ↓ or Enter to reach the results. The Brain picker also supports arrows and Enter. Forms use Tab, Shift Tab and Enter; confirm a selection with Enter before moving on with Tab.

W cycles through visible panes and Shift W reverses direction outside text fields. Esc first leaves an input; Tab moves forward and Shift Tab backward through controls. Arrow keys in text fields retain selection behavior. Global commands ignore modifiers and IME composition; the editor handles only its documented save, preview and formatting combinations. Selecting text in the reader also suppresses global letter commands.

All actions remain in the P command palette, including actions without a dedicated key. Type an action name, navigate with arrows and press Enter. Typed characters in the palette, theme picker and forms are handled locally and do not trigger workspace commands.

Less frequent flows share that same route: **Manage Brain access**, **Remove this Brain from Notryn**, **Expand all folders**, **Collapse all folders**, and **Configure keyboard shortcuts**. Permissions, restoration and removal still require choosing an item and confirming in their dialogs with Tab/Enter. When creating a Brain, enter its name, choose the parent location and verify the complete **Brain folder** path before confirming. Open the folder browser with **O**, Tab to **Choose**, Enter; arrows/Enter browse directories and Tab reaches **Choose this location** or **Use this folder**. The Brain picker uses the same **Shift B** and **O** bindings as the workspace. Themes use T, arrows and Enter.

### Organizing files

The Library shows just the current folder name, or your Brain name at the root. Use the **back arrow** to return to its parent. **New note** and **New folder** are always visible below the name (beside it when there is room); nothing needs to be selected first. A new folder appears immediately and receives focus. Choosing a different destination in the creation dialog also opens that destination. Read-only Brains show the same navigation with creation disabled.

Drag a note onto a folder to move it. Drag a folder onto another folder to move its entire contents, including subfolders and attachments. Inside a folder, drop an item onto the **back arrow** to move it up one level. A highlighted target shows the destination. Use the Move picker to choose any other folder, including the Brain root.

For keyboard or touch, use the item's **⋯** menu. It shows **N** for a new note, **Shift N** for a new folder, **F2** for rename, **M** for move and **D** for removal. With a library row focused, press **F2** to rename it; `.md` stays attached automatically. Press **M** to open the destination picker, type to filter folders, use ↑/↓ to choose and **Enter** to move. **Esc** cancels. The command palette and **?** reference include both actions. The Library buttons and N/Shift N use the **currently open folder**, even when a note elsewhere is open or a child folder is focused. New note/New folder in an item menu use that specific folder instead.

Save an open draft before renaming or moving files. The open note follows its new path and revision. Neither action can replace an existing item or change a read-only Brain. A move also cannot leave the current Brain or place a folder inside itself or its descendants. Folders containing symbolic links or app data cannot be moved or renamed through this feature.

Ordinary wiki links, Markdown inline/reference links and local attachment links are updated when their resolved targets change name or location. Labels, anchors, titles and unrelated source bytes are retained. Frontmatter, code examples, comments and custom HTML/plugin syntax are not rewritten. Relative Markdown links resolve from the containing note. Renames and moves save recovery manifests and copies of changed notes under the private state's `backups/` directory and restore the original location if a link update fails. A process or disk interruption can require manual recovery from those copies. The link update limit is 2,000 notes of at most 1 MB each.

### Removing and restoring

Choose **Remove from Notryn…** in a note or folder's **⋯** menu, or press **D** with its library row focused. The command palette also includes **Remove this Brain from Notryn**. Each Brain in the top picker has a removal button.

The default **Remove from Notryn** keeps every file on the device. A note or folder disappears from this installation's library, searches and Brain view; a whole Brain is disconnected. These choices live in Notryn's private state, so other applications and the original Markdown files are unaffected. Read-only Brains support this default operation too.

The review shows the affected location. The separate **Also move files to Notryn Trash** checkbox starts unchecked. Select it to move the item, including a folder's contents and attachments, out of its original location into recoverable storage. Removing an entire Brain this way also requires typing its exact name. Notryn Trash is managed by the app, not the operating system's Trash, and does not permanently erase files or free their disk space. Read-only, protected and overlapping Brain folders cannot be moved to Trash.

Open **Removed items** from the library's trash icon, the Brain picker or the command palette. Search, use ↑/↓ to reach **Restore**, and press **Enter** to bring an item back. Restore its Brain and parent folder first if they were also removed. Restoration never overwrites a file already at the original location; resolve that conflict before retrying. Save any open draft before removing or restoring items.

Removed records survive restarts. Preserve the private state and recovery storage until everything you need is restored. On the same filesystem, Trash is under the private state's `trash/` directory; another filesystem uses a hidden `.notryn-trash/` beside the Brain, or inside its root when needed. Each recovery slot includes its original location. There is no permanent-delete or Empty Trash action in this preview.

### Write naturally

**Write** is the default editing view. Select text to open the nearby formatting bar, or use **Format** for keyboard access. Choose Text, Heading 1–6, Quote or Code block; apply bold, italic, strikethrough, bullet/numbered lists and links. Enter continues a list; an empty item followed by Enter returns to normal writing. Undo and redo are also available in the bar. Tab retains normal focus movement.

The text-style menu keeps the selected range and stays in place until a choice is applied. Selected text uses the theme's accent background with contrasting black or white lettering in reading, writing and input fields.

**Add a link** accepts a web address or lets you search and choose another note, without typing paths. Note links are saved as `[[target|text]]`, so the Brain shows their connections after saving. External links and note links work in the reader.

Use **Markdown** for direct source editing. Switching views does not save automatically. **Save** is explicit and retains the existing revision/conflict and backup protections. Frontmatter and unchanged blocks keep their source. Tables, task lists, callouts, HTML and other unsupported extensions remain preserved blocks; use Markdown to change those blocks. The reader displays simple tables. Images stay as inert placeholders, and embedded HTML is never executed. The editor does not send note content to another service.

### Appearance and Omarchy

Use the appearance icon or **T** outside text fields. While writing, press **Esc**, then **T**. **↑/↓** choose a theme, **Enter** applies it and **Esc** cancels. Home/End jump to the first/last option; typing a theme name selects it. The command palette and shortcut reference include **Choose theme**. Your preference is saved in this browser, including after restarting NOTRYN. Changing themes preserves unsaved writing, the cursor, scroll and brain position.

| Theme | Atmosphere |
| --- | --- |
| Glass | Deep blue space, translucent surfaces and mint light |
| Daylight | Frosted white glass and calm green ink |
| Matrix | Dark phosphor green with soft neural light |
| Command | Amber signals, precise panels and a subtle spatial grid |
| Dusk | Warm dark surfaces and rose light |
| Follow Omarchy | Live colors from the local Linux desktop |


Omarchy does not automatically color arbitrary web applications. NOTRYN includes a read-only bridge to its active `colors.toml`, covering the newer `~/.local/state/omarchy/current/theme/` location and the older `~/.config/omarchy/current/theme/` location. XDG state/config locations and legacy theme symlinks are also supported. Light mode is read from `mode = "light"` or the older `light.mode` marker. Background, foreground, accent and palette colors style both the interface and the brain, with text adjusted for legibility.

On a first visit, an available Omarchy palette is selected automatically. Choosing a NOTRYN preset stops following the desktop; choose **Follow Omarchy** to resume. The app checks about every two seconds while visible and following. No reload, theme hook, desktop configuration edit or extension is needed. If Omarchy is not detected, follow mode uses Glass and waits for a palette; a server connection failure keeps the last colors. The colors come from the computer running the local server.

The bridge follows the [Omarchy theme configuration](https://github.com/omacom/omarchy/blob/quattro/manual/43-making-your-own-theme.md) and [active-theme staging paths](https://github.com/omacom/omarchy/blob/quattro/bin/omarchy-theme-set). Legacy/new-path fixtures and a live dark-to-light palette change have been tested locally. The private Linux package has also been installed and opened successfully in a native Omarchy session; a broader palette-switching review there is still pending.
