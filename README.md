# ghubMacroEditor

<img width="1676" height="1007" alt="ghubMacroEditor screenshot" src="https://github.com/user-attachments/assets/5a6707e3-6d71-4b16-b51c-a24351110047" />

## Warning

**Use at your own risk.**
Before editing `settings.db`, make a backup of:

`%localappdata%\LGHUB\settings.db`

Logitech G Hub can overwrite changes if it is still running when you save. It also won't update unless you completely exit out of lghub and relaunch.

## Requirements

- Python 3.10+ recommended
- Windows
- Tkinter available in your Python install

## Run

From the project folder run this code to launch:

```python ghub_macro_browser.py```

Or download the exe zip file if you are less technically inclined.

## What This Does

I made this because editing larger sets of macros directly in G Hub is slow and tedious, especially when you want to make the same kind of changes across many macros.

This tool reads macro data from G Hub and lets you:

- open and edit existing macros
- create new macros
- edit sequence components directly
- replace keys across one macro or many filtered macros
- change delays in one macro or in bulk
- change sequence default delays in bulk
- assign macros to G keys and memory profiles
- record keystrokes into new or existing sequence macros
- inspect and edit the raw JSON behind a macro

It works directly with G Hub macro data and, in my testing, G Hub accepts the changes after writing them back.

## Main Features

- Macro browser with filtering by application, type, and search text
- Sequence summary line for quick viewing
- Sequence component editor
- Drag-and-drop component reordering
- Bulk delay editing
- Bulk key replacement for sequence macros - example changing WASD to ARROW keys on all filtered macros
- Macro duplication and creation
- G-key assignment tools
- Keystroke recording for sequence macros
- Raw JSON view for advanced inspection

## Important Notes

- Close G Hub before saving to `settings.db`
- Back up `settings.db` before using this tool
- This tool edits existing G Hub data structures directly
- Some macro ordering behavior inside the G Hub UI still appears to be controlled internally by G Hub

## About Macro Ordering In G Hub

One of the reasons I made this was frustration with macro ordering in the official G Hub app.

From what I have seen, macro ordering inside G Hub does **not** appear to be controlled in any obvious or reliable way by:

- JSON order
- UUID
- creation order
- alphabetical name order
- cards index
- simple reformatting of the data

Assigned macros tend to float toward the top, but the rest often appear in an arbitrary order. I spent quite a while trying to reverse-engineer this and did not find a dependable ordering rule.

So while this editor can help you manage and bulk-edit macros more easily, it probably cannot fully fix how G Hub itself chooses to display macro ordering.

## Before Saving To `settings.db`

Make sure these G Hub processes are closed before writing changes:

<img width="375" height="332" alt="Processes to close before saving" src="https://github.com/user-attachments/assets/efef6777-c368-4fa8-a3cc-47093d66d801" />

If G Hub is open while you save, it may overwrite your edits.

## Typical Workflow

1. Close G Hub completely
2. Back up `%localappdata%\LGHUB\settings.db`
3. Open `settings.db` in this tool
4. Filter to the application or macros you want
5. Make your edits
6. Save
7. Reopen G Hub and verify the changes

## Limitations

- Built around Logitech G Hub macro data
- Tested against my own usage; not guaranteed for every G Hub version
- G Hub may change its internal format in future updates
- Macro ordering in the G Hub UI is still largely outside this tool’s control

## Why I Made It

This is not meant to replace G Hub entirely.
It is mainly for people who already use G Hub macros and want a faster way to inspect, batch-edit, and manage them without fighting the official UI.

If you already hate editing macros in G Hub, this may still be easier.
