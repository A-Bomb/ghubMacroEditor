# Logitech G Hub Macro Browser - User Guide

A refresher for browsing, editing, recording, organizing, and assigning G Hub macros. This guide describes the supplied version of the program, including a few places where the buttons behave differently than you might expect.

## Quick start: edit a macro in G Hub

1. Fully close G Hub before editing its database, so it cannot overwrite your changes. Keep a separate backup copy of `settings.db` before your first edit.
2. Launch the Macro Browser and click **Open settings.db**. The file picker defaults to `%LOCALAPPDATA%\LGHUB\settings.db`.
3. Choose an **Application**, then use **Search** to find your macro.
4. Select the macro in the left list.
5. Make your changes. For a sequence row, click **Update Component**. For the macro name or sequence options, click **Apply Current Changes**.
6. Click **Save** or press **Ctrl+S** to write the changes to the database.
7. Reopen G Hub and check the macro and its assignment there.

The browser edits settings; it does not run or test macros itself.

## What does Open JSON open?

**Yes - it can open the JSON extracted from G Hub's `settings.db`.** More precisely, it expects a G Hub settings JSON document containing macro records, typically together with applications, profiles, and assignments. It is not an importer for an arbitrary list of keystrokes or a bare `macro` object.

The two Open buttons load the same kind of data through different routes:

| Button | What it reads | Where Save writes |
| --- | --- | --- |
| **Open JSON** | A standalone UTF-8 JSON file, such as `ghub.json` or an export created with Save As | Back to that JSON file |
| **Open settings.db** | The JSON stored in the first `DATA` row's `FILE` field inside the SQLite database | Back to that database row |

To make a standalone JSON copy, open **settings.db**, then click **Save As** and choose a `.json` filename. You can reopen that file later with **Open JSON**. The name does not have to be `ghub.json`.

Opening a JSON file replaces the currently loaded dataset. It does not merge macros into an already open database. This version has no button to import an edited JSON file back into `settings.db`; use the database workflow above when you want changes applied directly to G Hub.

If a bundled `ghub.json` exists, the program loads it automatically at startup. Check the status line to see which source is actually open.

## Applying, saving, and reverting

There are two stages: applying edits to the program's working data, then saving that data to disk.

| Control | What it does |
| --- | --- |
| **Update Component** | Applies the selected keyboard, delay, or mouse row's editor values |
| **Update Keystroke Macro** | Applies the key code and modifiers on the Keystroke tab; also updates Action name from the Known key field |
| **Apply Current Changes** | Applies Macro name, Action name, sequence options, and keystroke fields; does not apply the selected component editor or Raw JSON text |
| **Save / Ctrl+S** | Applies the main macro form, then writes the working dataset to its current source |
| **Save As** | Writes the working dataset to a JSON file; click the relevant Update/Apply buttons first |
| **Revert Current View** | Refills the form from working data, discarding un-applied form changes; does not undo changes already applied |
| **Undo / Redo** | Steps backward or forward through tracked edits in memory; up to 50 undo snapshots are kept |
| **Reload** | Reads the current source from disk again, discarding unsaved edits and clearing undo/redo history |

**Apply changes before switching macros, changing filters, or using another tool.** Those actions can refresh the form and discard text you have typed but not applied. The `Save*` indicator tracks applied changes, so its absence does not prove every visible edit has been saved.

### Save As has two important quirks

- When a JSON source is open, **Save As** makes the new JSON file the target of future saves.
- When a database is open, **Save As** exports a JSON copy but keeps the database as the active source. It also clears the modified indicator even though the database has not been updated. Click **Save** separately if you want those changes written to the database.

Opening another file or clicking Reload does not prompt before discarding changes. Save first if you want to keep them.

Database saves also insert a snapshot containing the **newly edited data** into `SNAPSHOTS`. That is not a backup of the data from before the save, and this browser has no snapshot restore interface.

## Finding your macros

- **Application:** choose an application or type part of its name/ID. Use **All Applications** to remove the restriction.
- **Search:** matches macro name, application name/ID, macro ID, macro type, or its location in the JSON. Matching is case-insensitive.
- **Type:** show All, SEQUENCE, KEYSTROKE, or ACTION.
- **Shown count:** tells you how many macros match your filters.

**Filtered means every macro currently shown, not just the one you selected.** Check that count before using a bulk operation.

Macro types:

- **SEQUENCE:** multiple keyboard events, mouse-button events, and delays. Most editing tools target this type.
- **KEYSTROKE:** a single key plus optional modifiers, such as Ctrl+C.
- **ACTION:** an existing G Hub action. This version provides no dedicated action editor beyond the shared name fields and JSON inspection.

The details panel shows IDs, source indexes, onboardable status, and assigned slots as read-only information. JSON index is the browser's zero-based macro discovery number; Cards index is its zero-based position in `cards.cards`, when applicable. Neither is a G-key number. Onboardable reports a stored flag; it is not a hardware compatibility test.

## Editing a sequence

1. Select a **SEQUENCE** macro and open **Sequence**.
2. Select a row in the component list.
3. Change the fields under **Selected Component**.
4. Click **Update Component**.
5. Save when finished.

### Keyboard rows

Choose a **Known key** to populate its display name and HID usage code. The HID usage identifies the actual key; Display name is its label.

- **Key down event checked:** press the key.
- **Key down event unchecked:** release the key.

A normal key tap generally needs both a down and an up event. For example, a Ctrl+C sequence could contain Ctrl down, C down, C up, Ctrl up, with delays where needed. Recording is usually easier than constructing these rows manually.

### Adding, moving, and copying rows

- **Add Keyboard** inserts an A-down event. Edit it afterward.
- **Add Delay** inserts a 50 ms delay. Edit its Duration ms afterward.
- New rows go after the selected row, or at the end if no row is selected.
- **Move Up**, **Move Down**, or dragging a row changes its position.
- **Delete Component** removes the current row.
- **Ctrl+C**, then **Ctrl+V** with the component list focused copies a row **over** another row. Paste replaces; it does not insert.
- Clicking an already selected row again can deselect it.

With **Paste includes up/down state** checked, paste copies the press/release state too. Uncheck it to preserve the destination's state when copying keyboard-to-keyboard or mouse-to-mouse. This is useful for changing a key without turning an up event into a down event.

Mouse-button rows can be edited using their HID usage and down/up state. There is no Add Mouse button, but you can add a row, change **Component type** to `mouse`, fill in its fields, and click **Update Component**.

### Sequence options

- **Default delay:** the sequence's default timing value in milliseconds; 1,000 ms is one second.
- **Use default delay:** saves G Hub's default-delay setting and makes the recorder use that value between events.
- **Use simple actions:** saves G Hub's simple-action setting.
- **Show up/down:** saves G Hub's show-up/down setting. The browser's own component list displays individual events regardless.

Click **Apply Current Changes** after changing these options. The browser stores the playback flags; it does not simulate G Hub playback.

The **Sequence summary** lists only key/button down events. It omits releases and delays. A `+` between names is a summary separator, not proof that the keys are held together.

## Recording keys

Recording is available for SEQUENCE macros through **Record Keys** or the Sequence tab's **Record Replace / Record Append** buttons.

1. Choose the timing settings described below.
2. Start a replace or append recording.
3. Type in the capture window. Recognized modifier keys are recorded too.
4. Release the keys you pressed, then press **Escape** to finish.
5. Inspect the recorded rows and save.

**Replace** replaces the existing sequence. **Append** actually inserts after the current row when one is selected, rather than always adding at the end. In this version, starting recording refreshes the form and can reset the selection to the first row, so check the insertion position afterward.

Timing priority:

| Use default delay | Use actual input timing | Recorded delays |
| --- | --- | --- |
| On | Either | The Default delay value |
| Off | On | Your actual time between captured events |
| Off | Off | The Default delay value |

For real timing, uncheck **Use default delay** and check **Use actual input timing**.

The recorder captures recognized keys in its own window, not global keyboard activity or mouse clicks. Escape ends recording and is not captured as a key. Closing the recording window also finishes and inserts the captured input; it is not Cancel. Use Undo if you want to discard the result.

## Editing a simple keystroke

1. Select a **KEYSTROKE** macro.
2. Open **Keystroke**.
3. Choose a Known key or enter its Code / HID usage.
4. Check the desired modifiers: Ctrl, Shift, Alt, GUI, or their right-side equivalents. GUI is the Windows key on Windows.
5. Click **Update Keystroke Macro**, then **Save**.

## Replacing keys and changing delays in bulk

The **Replace / Delay Tools** section only affects SEQUENCE macros.

- Set **From** and **To**, then choose **Replace In Current Macro** or **Replace In Filtered Macros**. It changes matching key identities in both down and up rows while retaining their states.
- Enter **New delay ms**, then use **Set All Delays...** to change existing explicit delay rows. It does not create missing delays.
- Use **Set Sequence Default Delay** or **Set Default Delay In Filtered Macros** to change the default timing field. This does not rewrite explicit delay rows or enable Use default delay.

For example, to replace A with B only in one application's sequences: filter to that application and SEQUENCE, check the shown count, set From A / To B, then click **Replace In Filtered Macros** and save.

## Creating, duplicating, deleting, and organizing macros

### New Macro

Select an editable macro in the intended application, then click **New Macro**. The program creates an empty SEQUENCE beside it with a fresh ID and a name such as New Macro or New Macro 2. Its starting default delay is 50 ms, with Use default delay and Use simple actions enabled.

Rename it, apply the name, then record or add components. Creation requires an existing editable macro as an anchor; this is not a blank-settings-file creator.

### Duplicate Filtered

Duplicates all matching macros within their existing source lists, using fresh IDs but keeping their names. Copies are sorted using the A-Z / Z-A choice. Button assignments are not copied to the new IDs.

With **Delete originals** checked, the originals are removed and their assignments are deleted. The replacements need to be assigned again. Leave this unchecked when you just want extra copies.

### Delete Macro

Deletes the selected editable macro after confirmation and removes assignments pointing to it. The deletion reaches disk when you save.

### Reorder versus Compact

The **Sort** dropdown sets the direction for these operations; it does not itself sort the visible list.

- **Reorder Filtered:** sorts matching macros within their existing positions in each source list. Entries between those positions stay where they are.
- **Compact Filtered:** gathers matching macros into a consecutive sorted block starting at their earliest position in each source list. Other entries can shift position.

These change storage order. The left list is independently organized by application, type, and name, so it may look unchanged. Use the index fields to inspect the result, then save if wanted.

## Assigning a macro to a G key

1. Select the macro.
2. Check **Device**. It is a device identifier such as `g910`, not a friendly device name. The program tries to infer it and falls back to `g910` if it cannot.
3. Enter a **G key**, such as `2` or `g2`.
4. Select **M1**, **M2**, and/or **M3**.
5. Enable **G-Shift** if the assignment should use the shifted layer.
6. Click **Assign Selected Macro**, then save.

This replaces any existing assignment on the targeted slots. It uses the first profile matching the macro's application; there is no separate profile picker. If an application has multiple profiles, verify the result in G Hub.

**Clear Macro Assignments** removes all profile assignments pointing to the selected macro, not just the slots currently checked. The macro itself remains.

## Raw JSON and supported sequences

**Treat Raw JSON as a viewer in this version.** Although the text box allows typing, Apply and Save never read that text back. Edits there are not saved and disappear when the view refreshes.

The sequence editor operates on `macro.sequence.simpleSequence.components`. Other sequence structures, such as separate hold/release or toggle sections, do not have dedicated editors here. An empty component list does not necessarily mean the full macro contains no other actions.

## Shortcut reference

| Shortcut | Action |
| --- | --- |
| Ctrl+S | Save to the current source |
| Ctrl+C | Copy the current component when the component list has focus |
| Ctrl+V | Replace the current component with the copied one |
| Delete | Delete the selected macro or current component, depending on which list has focus |
| Ctrl+Z | Undo a tracked edit when focus is outside a text-entry field |
| Ctrl+Y | Redo a tracked edit when focus is outside a text-entry field |
| Escape | Finish recording in the capture window |

Hover over buttons and checkboxes for short reminders.

## If something seems wrong

- **G Hub did not change:** check that you opened settings.db and used Save. Saving a standalone JSON or exporting with Save As does not update G Hub's database.
- **A typed edit disappeared:** use Update Component or Apply Current Changes before changing selection or running another tool.
- **The macro is missing from the list:** clear Search, select All Applications, and set Type to All.
- **New Macro says there is no editable anchor:** select an existing editable macro in the desired application first.
- **A duplicated macro no longer has a G-key assignment:** copies receive new IDs; assign them again, especially after using Delete originals.
- **An assignment went to an unexpected place:** check Device, G key, memory bank, G-Shift, and the application's profile in G Hub.
- **Save says the database cannot be written:** fully close G Hub and confirm the selected database has the DATA and SNAPSHOTS tables expected by this version.

If running the source script, it uses Python 3.10+ syntax and standard-library modules, including Tkinter. This guide was checked against the supplied source; actual device playback was not tested.
