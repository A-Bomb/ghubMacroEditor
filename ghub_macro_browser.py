import copy
import json
import sqlite3
import sys
import tkinter as tk
import time
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def bundled_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent
    return base / name


def app_state_path(name: str) -> Path:
    return Path(__file__).resolve().parent / name


class HoverToolTip:
    """Show a small delayed tooltip for a widget while the pointer is over it."""

    def __init__(self, widget, text: str, delay_ms: int = 450) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip_window = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._hide()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self) -> None:
        if self._tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip_window = tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tip,
            text=self.text,
            justify="left",
            relief="solid",
            borderwidth=1,
            background="#fff8d7",
            foreground="#202020",
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None


KEYBOARD_USAGE_TO_NAME = {
    4: "A",
    5: "B",
    6: "C",
    7: "D",
    8: "E",
    9: "F",
    10: "G",
    11: "H",
    12: "I",
    13: "J",
    14: "K",
    15: "L",
    16: "M",
    17: "N",
    18: "O",
    19: "P",
    20: "Q",
    21: "R",
    22: "S",
    23: "T",
    24: "U",
    25: "V",
    26: "W",
    27: "X",
    28: "Y",
    29: "Z",
    30: "1",
    31: "2",
    32: "3",
    33: "4",
    34: "5",
    35: "6",
    36: "7",
    37: "8",
    38: "9",
    39: "0",
    40: "Enter",
    41: "Escape",
    42: "Backspace",
    43: "Tab",
    44: "Space",
    45: "-",
    46: "=",
    47: "[",
    48: "]",
    49: "\\",
    51: ";",
    52: "'",
    53: "`",
    54: ",",
    55: ".",
    56: "/",
    57: "Caps Lock",
    58: "F1",
    59: "F2",
    60: "F3",
    61: "F4",
    62: "F5",
    63: "F6",
    64: "F7",
    65: "F8",
    66: "F9",
    67: "F10",
    68: "F11",
    69: "F12",
    70: "Print Screen",
    71: "Scroll Lock",
    72: "Pause",
    73: "Insert",
    74: "Home",
    75: "Page Up",
    76: "Delete",
    77: "End",
    78: "Page Down",
    79: "Right",
    80: "Left",
    81: "Down",
    82: "Up",
    83: "Num Lock",
    84: "Numpad /",
    85: "Numpad *",
    86: "Numpad -",
    87: "Numpad +",
    88: "Numpad Enter",
    89: "Numpad 1",
    90: "Numpad 2",
    91: "Numpad 3",
    92: "Numpad 4",
    93: "Numpad 5",
    94: "Numpad 6",
    95: "Numpad 7",
    96: "Numpad 8",
    97: "Numpad 9",
    98: "Numpad 0",
    99: "Numpad .",
    224: "Ctrl",
    225: "Shift",
    226: "Alt",
    227: "GUI",
    228: "Right Ctrl",
    229: "Right Shift",
    230: "Right Alt",
    231: "Right GUI",
}

KEYBOARD_NAME_TO_USAGE = {
    name.upper(): usage for usage, name in KEYBOARD_USAGE_TO_NAME.items()
}
KEYBOARD_NAME_TO_USAGE.update(
    {
        "CONTROL": 224,
        "LEFT CTRL": 224,
        "LEFT CONTROL": 224,
        "LEFT SHIFT": 225,
        "LEFT ALT": 226,
        "LEFT GUI": 227,
        "LEFT WINDOWS": 227,
        "WIN": 227,
        "WINDOWS": 227,
        "ESC": 41,
        "RETURN": 40,
        "PGUP": 75,
        "PGDN": 78,
        "UP ARROW": 82,
        "DOWN ARROW": 81,
        "LEFT ARROW": 80,
        "RIGHT ARROW": 79,
    }
)

COMMON_MODIFIERS = [
    ("Ctrl", 224),
    ("Shift", 225),
    ("Alt", 226),
    ("GUI", 227),
    ("Right Ctrl", 228),
    ("Right Shift", 229),
    ("Right Alt", 230),
    ("Right GUI", 231),
]

SUMMARY_ARROW_SYMBOLS = {
    "Up": "⮝",
    "Down": "⮟",
    "Left": "⮜",
    "Right": "⮞",
}


class GHubMacroBrowserApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Logitech G Hub Macro Browser")
        self.root.geometry("1680x1080")

        self.file_path: Path | None = None
        self.source_kind = "json"
        self.settings_db_path: Path | None = None
        self.settings_db_row_id: int | None = None
        self.data = {}
        self.applications_by_id = {}
        self.profile_assignments_by_card_id = {}
        self.macro_records = []
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.is_dirty = False
        self.component_clipboard = None
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50
        self.recording_window = None
        self.recording_mode = None
        self.recorded_components = []
        self.record_last_event_time = None
        self.record_pressed_usages = set()
        self.component_drag_start_row = None
        self.component_drag_active = False
        self.component_press_selection = ()
        self.preferences_path = app_state_path("ghub_macro_browser_prefs.json")
        self.preferences = self._load_preferences()

        self.vars = {
            "application_filter": tk.StringVar(value="All Applications"),
            "type_filter": tk.StringVar(value="All"),
            "sort_mode": tk.StringVar(value="A-Z"),
            "delete_originals_after_duplicate": tk.BooleanVar(value=False),
            "search": tk.StringVar(),
            "macro_name": tk.StringVar(),
            "json_index": tk.StringVar(),
            "cards_index": tk.StringVar(),
            "onboardable": tk.StringVar(),
            "assigned_slots": tk.StringVar(),
            "assignment_device_prefix": tk.StringVar(),
            "assignment_button_slot": tk.StringVar(),
            "application_name": tk.StringVar(),
            "application_id": tk.StringVar(),
            "macro_type": tk.StringVar(),
            "macro_id": tk.StringVar(),
            "sequence_default_delay": tk.StringVar(),
            "sequence_use_default_delay": tk.BooleanVar(value=True),
            "sequence_use_simple_actions": tk.BooleanVar(value=False),
            "show_up_down": tk.BooleanVar(value=False),
            "component_kind": tk.StringVar(),
            "component_key_name": tk.StringVar(),
            "component_display_name": tk.StringVar(),
            "component_hid_usage": tk.StringVar(),
            "component_is_down": tk.BooleanVar(value=False),
            "component_delay": tk.StringVar(),
            "component_mouse_usage": tk.StringVar(),
            "paste_include_state": tk.BooleanVar(value=True),
            "record_use_actual_delay": tk.BooleanVar(value=True),
            "replace_from": tk.StringVar(),
            "replace_to": tk.StringVar(),
            "replace_delay": tk.StringVar(),
            "keystroke_key_name": tk.StringVar(),
            "keystroke_code": tk.StringVar(),
            "action_name": tk.StringVar(),
            "sequence_summary": tk.StringVar(),
        }
        self.keystroke_modifier_vars = {
            usage: tk.BooleanVar(value=False) for _, usage in COMMON_MODIFIERS
        }
        self.assignment_memory_vars = {
            "m1": tk.BooleanVar(value=True),
            "m2": tk.BooleanVar(value=False),
            "m3": tk.BooleanVar(value=False),
        }
        self.assignment_shifted_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="No file loaded")
        self.sequence_info_var = tk.StringVar(value="")
        self.component_info_var = tk.StringVar(value="")
        self.assignment_status_var = tk.StringVar(value="")
        self.filtered_count_var = tk.StringVar(value="")

        self._build_ui()
        self._bind_change_tracking()
        self._bind_shortcuts()

        default_path = bundled_path("ghub.json")
        if default_path.exists():
            self.load_file(default_path)

    def _load_preferences(self) -> dict:
        """Load small UI preferences stored beside the script."""
        try:
            if self.preferences_path.exists():
                return json.loads(self.preferences_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def _save_preferences(self) -> None:
        """Persist lightweight UI preferences without interrupting the user on failure."""
        try:
            self.preferences_path.write_text(
                json.dumps(self.preferences, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _confirm_settings_db_write(self) -> bool:
        """Warn before writing directly into G Hub's sqlite database."""
        if self.preferences.get("skip_settings_db_write_warning"):
            return True

        result = {"confirmed": False}
        win = tk.Toplevel(self.root)
        win.title("Write settings.db")
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()

        container = ttk.Frame(win, padding=14)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        ttk.Label(
            container,
            text=(
                "This writes directly to LG Hub settings.db.\n\n"
                "Make sure G Hub is fully closed first, or it may overwrite the change.\n\n"
                "Continue?"
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        dont_remind_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            container,
            text="Don't remind me again",
            variable=dont_remind_var,
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))

        buttons = ttk.Frame(container)
        buttons.grid(row=2, column=0, sticky="e", pady=(12, 0))

        def close_dialog(confirmed: bool) -> None:
            result["confirmed"] = confirmed
            if confirmed and dont_remind_var.get():
                self.preferences["skip_settings_db_write_warning"] = True
                self._save_preferences()
            win.destroy()

        ttk.Button(buttons, text="Yes", command=lambda: close_dialog(True)).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="No", command=lambda: close_dialog(False)).pack(side="left")

        win.protocol("WM_DELETE_WINDOW", lambda: close_dialog(False))
        win.update_idletasks()
        x = self.root.winfo_rootx() + max((self.root.winfo_width() - win.winfo_width()) // 2, 0)
        y = self.root.winfo_rooty() + max((self.root.winfo_height() - win.winfo_height()) // 2, 0)
        win.geometry(f"+{x}+{y}")
        self.root.wait_window(win)
        return result["confirmed"]

    def _add_tooltip(self, widget, text: str) -> None:
        """Attach a hover tooltip to a widget and keep the helper alive."""
        widget._hover_tooltip = HoverToolTip(widget, text)

    def _build_ui(self) -> None:
        """Build the main window layout, top controls, and the detail panes."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        action_row = ttk.Frame(top)
        action_row.grid(row=0, column=0, sticky="w")

        open_json_button = ttk.Button(action_row, text="Open JSON", command=self.open_file)
        open_json_button.grid(row=0, column=0, padx=(0, 4), pady=2)
        self._add_tooltip(open_json_button, "Open a ghub.json export for browsing and editing.")

        open_db_button = ttk.Button(action_row, text="Open settings.db", command=self.open_settings_db)
        open_db_button.grid(row=0, column=1, padx=4, pady=2)
        self._add_tooltip(open_db_button, "Open Logitech G Hub's live settings.db database.")

        self.save_button = ttk.Button(top, text="Save", command=self.save_file)
        self.save_button.grid(in_=action_row, row=0, column=2, padx=4, pady=2)
        self._add_tooltip(self.save_button, "Save the current data back to the loaded JSON file or settings.db.")

        save_as_button = ttk.Button(action_row, text="Save As", command=self.save_file_as)
        save_as_button.grid(row=0, column=3, padx=4, pady=2)
        self._add_tooltip(save_as_button, "Write the current JSON data to a new file.")

        reload_button = ttk.Button(action_row, text="Reload", command=self.reload_file)
        reload_button.grid(row=0, column=4, padx=4, pady=2)
        self._add_tooltip(reload_button, "Reload the current source from disk and discard unsaved edits.")

        undo_button = ttk.Button(action_row, text="Undo", command=self.undo)
        undo_button.grid(row=0, column=5, padx=4, pady=2)
        self._add_tooltip(undo_button, "Undo the last in-app edit.")

        redo_button = ttk.Button(action_row, text="Redo", command=self.redo)
        redo_button.grid(row=0, column=6, padx=(4, 0), pady=2)
        self._add_tooltip(redo_button, "Redo the last undone edit.")

        new_macro_button = ttk.Button(action_row, text="New Macro", command=self.create_new_macro)
        new_macro_button.grid(row=0, column=7, padx=(8, 0), pady=2)
        self._add_tooltip(new_macro_button, "Create a new macro near the current editable macro selection.")

        delete_macro_button = ttk.Button(action_row, text="Delete Macro", command=self.delete_selected_macro)
        delete_macro_button.grid(row=0, column=8, padx=(8, 0), pady=2)
        self._add_tooltip(delete_macro_button, "Delete the selected macro and any assignments that point to it.")

        filter_row = ttk.Frame(top)
        filter_row.grid(row=1, column=0, sticky="ew")
        filter_row.columnconfigure(1, weight=2)
        filter_row.columnconfigure(3, weight=3)

        ttk.Label(filter_row, text="Application").grid(row=0, column=0, padx=(0, 4), pady=2, sticky="w")
        self.application_filter = ttk.Combobox(
            filter_row,
            textvariable=self.vars["application_filter"],
            state="normal",
            width=24,
        )
        self.application_filter.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.application_filter.bind("<<ComboboxSelected>>", lambda *_: self.refresh_macro_list())
        self.application_filter.bind("<KeyRelease>", self.on_application_filter_typed)
        self.application_filter.bind("<FocusIn>", lambda *_: self._update_application_filter_options())

        ttk.Label(filter_row, text="Search").grid(row=0, column=2, padx=(8, 4), pady=2, sticky="e")
        search_entry = ttk.Entry(filter_row, textvariable=self.vars["search"])
        search_entry.grid(row=0, column=3, sticky="ew", padx=4, pady=2)

        ttk.Label(filter_row, text="Type").grid(row=0, column=4, padx=(8, 4), pady=2)
        self.type_filter = ttk.Combobox(
            filter_row,
            textvariable=self.vars["type_filter"],
            values=["All", "SEQUENCE", "KEYSTROKE", "ACTION"],
            state="readonly",
            width=11,
        )
        self.type_filter.grid(row=0, column=5, padx=4, pady=2)
        self.type_filter.bind("<<ComboboxSelected>>", lambda *_: self.refresh_macro_list())
        ttk.Label(filter_row, text="Sort").grid(row=0, column=6, padx=(8, 4), pady=2)
        sort_box = ttk.Combobox(
            filter_row,
            textvariable=self.vars["sort_mode"],
            values=["A-Z", "Z-A"],
            state="readonly",
            width=7,
        )
        sort_box.grid(row=0, column=7, padx=4, pady=2)
        reorder_button = ttk.Button(filter_row, text="Reorder Filtered", command=self.reorder_filtered_macros)
        reorder_button.grid(row=0, column=8, padx=(8, 4), pady=2)
        self._add_tooltip(reorder_button, "Sort the filtered macros by name within their existing JSON lists.")

        compact_button = ttk.Button(filter_row, text="Compact Filtered", command=self.compact_filtered_macros)
        compact_button.grid(row=0, column=9, padx=4, pady=2)
        self._add_tooltip(compact_button, "Remove gaps left by filtered macros and renumber JSON indexes.")

        duplicate_button = ttk.Button(filter_row, text="Duplicate Filtered", command=self.duplicate_filtered_macros)
        duplicate_button.grid(row=0, column=10, padx=4, pady=2)
        self._add_tooltip(duplicate_button, "Duplicate every currently filtered macro.")
        delete_originals_check = ttk.Checkbutton(
            filter_row,
            text="Delete originals",
            variable=self.vars["delete_originals_after_duplicate"],
        )
        delete_originals_check.grid(row=0, column=11, padx=(8, 0), pady=2)
        self._add_tooltip(
            delete_originals_check,
            "When duplicating filtered macros, remove the originals after the copies are created.",
        )

        ttk.Label(top, textvariable=self.status_var).grid(
            row=2, column=0, columnspan=12, sticky="w", pady=(6, 0)
        )

        content = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        content.grid(row=1, column=0, sticky="nsew")

        left = ttk.Frame(content, padding=(8, 0, 4, 8))
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=0)
        left.rowconfigure(1, weight=1)

        list_header = ttk.Frame(left)
        list_header.grid(row=0, column=0, sticky="ew")
        list_header.columnconfigure(0, weight=1)
        list_header.columnconfigure(1, weight=0)
        ttk.Label(list_header, text="Macros").grid(row=0, column=0, sticky="w")
        ttk.Label(list_header, textvariable=self.filtered_count_var).grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.macro_listbox = tk.Listbox(left, width=54, exportselection=False)
        self.macro_listbox.grid(row=1, column=0, sticky="nsew")
        self.macro_listbox.bind("<<ListboxSelect>>", self.on_macro_select)

        list_scroll = ttk.Scrollbar(left, orient="vertical", command=self.macro_listbox.yview)
        list_scroll.grid(row=1, column=1, sticky="ns")
        self.macro_listbox.configure(yscrollcommand=list_scroll.set)

        right = ttk.Frame(content, padding=(4, 0, 8, 8))
        right.columnconfigure(1, weight=1)
        right.columnconfigure(3, weight=1)
        right.rowconfigure(6, weight=1)

        content.add(left, weight=0)
        content.add(right, weight=1)

        fields = [
            ("Macro name", "macro_name", 0, 0),
            ("Application", "application_name", 0, 2),
            ("Macro type", "macro_type", 1, 0),
            ("Application ID", "application_id", 1, 2),
            ("Macro ID", "macro_id", 2, 0),
            ("JSON index", "json_index", 2, 2),
            ("Action name", "action_name", 3, 0),
            ("Cards index", "cards_index", 3, 2),
            ("Onboardable", "onboardable", 4, 0),
            ("Assigned slots", "assigned_slots", 4, 2),
        ]

        for label, key, row, col in fields:
            ttk.Label(right, text=label).grid(row=row, column=col, sticky="w", padx=4, pady=4)
            entry = ttk.Entry(right, textvariable=self.vars[key])
            if key in {
                "json_index",
                "cards_index",
                "onboardable",
                "assigned_slots",
                "application_name",
                "application_id",
                "macro_type",
                "macro_id",
            }:
                entry.configure(state="readonly")
            entry.grid(row=row, column=col + 1, sticky="ew", padx=4, pady=4)
            if key == "macro_name":
                self.macro_name_entry = entry

        ttk.Label(right, text="Sequence summary").grid(row=5, column=0, sticky="w", padx=4, pady=(4, 4))
        self.summary_entry = ttk.Entry(
            right,
            textvariable=self.vars["sequence_summary"],
            state="readonly",
            font=("Segoe UI Symbol", 14, "bold"),
        )
        self.summary_entry.grid(row=5, column=1, columnspan=3, sticky="ew", padx=4, pady=(4, 4))

        notebook = ttk.Notebook(right)
        notebook.grid(row=6, column=0, columnspan=4, sticky="nsew", padx=4, pady=(8, 6))

        self.sequence_tab = ttk.Frame(notebook, padding=6)
        self.keystroke_tab = ttk.Frame(notebook, padding=6)
        self.record_tab = ttk.Frame(notebook, padding=6)
        self.raw_tab = ttk.Frame(notebook, padding=6)

        notebook.add(self.sequence_tab, text="Sequence")
        notebook.add(self.keystroke_tab, text="Keystroke")
        notebook.add(self.record_tab, text="Record Keys")
        notebook.add(self.raw_tab, text="Raw JSON")

        self._build_sequence_tab()
        self._build_keystroke_tab()
        self._build_record_tab()
        self._build_raw_tab()

        buttons = ttk.Frame(right)
        buttons.grid(row=7, column=0, columnspan=4, sticky="ew")
        apply_button = ttk.Button(buttons, text="Apply Current Changes", command=self.apply_current_edits)
        apply_button.pack(side="left", padx=4)
        self._add_tooltip(apply_button, "Apply the values shown in the form to the selected macro.")

        revert_button = ttk.Button(buttons, text="Revert Current View", command=self.reload_current)
        revert_button.pack(side="left", padx=4)
        self._add_tooltip(revert_button, "Reload the selected macro from the in-memory data and discard form edits.")

        assignment_tools = ttk.Frame(right)
        assignment_tools.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Label(
            assignment_tools,
            textvariable=self.assignment_status_var,
        ).pack(side="top", anchor="w", padx=4, pady=(0, 4))

        assignment_controls = ttk.Frame(assignment_tools)
        assignment_controls.pack(side="top", fill="x")
        ttk.Label(assignment_controls, text="Device").pack(side="left", padx=(4, 4))
        ttk.Entry(
            assignment_controls,
            textvariable=self.vars["assignment_device_prefix"],
            width=10,
        ).pack(side="left", padx=4)
        ttk.Label(assignment_controls, text="G key").pack(side="left", padx=(4, 4))
        ttk.Entry(
            assignment_controls,
            textvariable=self.vars["assignment_button_slot"],
            width=8,
        ).pack(side="left", padx=4)
        m1_check = ttk.Checkbutton(
            assignment_controls,
            text="M1",
            variable=self.assignment_memory_vars["m1"],
        )
        m1_check.pack(side="left", padx=2)
        self._add_tooltip(m1_check, "Assign the selected macro to the M1 memory profile.")

        m2_check = ttk.Checkbutton(
            assignment_controls,
            text="M2",
            variable=self.assignment_memory_vars["m2"],
        )
        m2_check.pack(side="left", padx=2)
        self._add_tooltip(m2_check, "Assign the selected macro to the M2 memory profile.")

        m3_check = ttk.Checkbutton(
            assignment_controls,
            text="M3",
            variable=self.assignment_memory_vars["m3"],
        )
        m3_check.pack(side="left", padx=2)
        self._add_tooltip(m3_check, "Assign the selected macro to the M3 memory profile.")

        gshift_check = ttk.Checkbutton(
            assignment_controls,
            text="G-Shift",
            variable=self.assignment_shifted_var,
        )
        gshift_check.pack(side="left", padx=(8, 2))
        self._add_tooltip(gshift_check, "Assign the selected macro to the G-Shift layer for the chosen slot.")
        assign_button = ttk.Button(
            assignment_controls,
            text="Assign Selected Macro",
            command=self.assign_selected_macro_to_slots,
        )
        assign_button.pack(side="left", padx=4)
        self._add_tooltip(assign_button, "Assign the selected macro to the specified device slot(s).")

        clear_assignments_button = ttk.Button(
            assignment_controls,
            text="Clear Macro Assignments",
            command=self.clear_selected_macro_assignments,
        )
        clear_assignments_button.pack(side="left", padx=4)
        self._add_tooltip(clear_assignments_button, "Remove slot assignments that point at the selected macro.")

    def _build_sequence_tab(self) -> None:
        """Build the sequence editor, component list, and bulk sequence tools."""
        frame = self.sequence_tab
        frame.columnconfigure(0, weight=3)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(2, weight=1)

        meta = ttk.Frame(frame)
        meta.grid(row=0, column=0, columnspan=2, sticky="ew")
        for col in range(6):
            meta.columnconfigure(col, weight=1 if col % 2 else 0)

        ttk.Label(meta, text="Default delay").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(meta, textvariable=self.vars["sequence_default_delay"], width=10).grid(
            row=0, column=1, sticky="w", padx=4, pady=4
        )
        use_default_delay_check = ttk.Checkbutton(
            meta,
            text="Use default delay",
            variable=self.vars["sequence_use_default_delay"],
        )
        use_default_delay_check.grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self._add_tooltip(
            use_default_delay_check,
            "Use the sequence default delay value when the macro runs and when recording with default timing.",
        )

        use_simple_actions_check = ttk.Checkbutton(
            meta,
            text="Use simple actions",
            variable=self.vars["sequence_use_simple_actions"],
        )
        use_simple_actions_check.grid(row=0, column=3, sticky="w", padx=4, pady=4)
        self._add_tooltip(use_simple_actions_check, "Set the sequence to use G Hub simple action playback mode.")

        show_up_down_check = ttk.Checkbutton(
            meta,
            text="Show up/down",
            variable=self.vars["show_up_down"],
        )
        show_up_down_check.grid(row=0, column=4, sticky="w", padx=4, pady=4)
        self._add_tooltip(show_up_down_check, "Tell G Hub to show key/button up and down events in the sequence.")

        paste_state_check = ttk.Checkbutton(
            meta,
            text="Paste includes up/down state",
            variable=self.vars["paste_include_state"],
        )
        paste_state_check.grid(row=0, column=5, sticky="w", padx=4, pady=4)
        self._add_tooltip(
            paste_state_check,
            "When pasting over a component, include the copied up/down press state instead of preserving the target state.",
        )
        ttk.Label(meta, textvariable=self.sequence_info_var).grid(
            row=1, column=0, columnspan=6, sticky="w", padx=4, pady=(0, 4)
        )

        self.component_tree = ttk.Treeview(
            frame,
            columns=("index", "type", "summary", "state"),
            show="headings",
            height=20,
        )
        self.component_tree.grid(row=2, column=0, rowspan=2, sticky="nsew", padx=(0, 8))
        for col, text, width in [
            ("index", "#", 50),
            ("type", "Type", 90),
            ("summary", "Summary", 260),
            ("state", "State / Value", 200),
        ]:
            self.component_tree.heading(col, text=text)
            self.component_tree.column(col, width=width, stretch=(col == "summary"))
        self.component_tree.bind("<ButtonPress-1>", self.on_component_tree_press, add="+")
        self.component_tree.bind("<B1-Motion>", self.on_component_tree_drag, add="+")
        self.component_tree.bind("<ButtonRelease-1>", self.on_component_tree_release, add="+")
        self.component_tree.bind("<<TreeviewSelect>>", self.on_component_select)

        tree_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.component_tree.yview)
        tree_scroll.grid(row=2, column=0, rowspan=2, sticky="nse")
        self.component_tree.configure(yscrollcommand=tree_scroll.set)

        editor = ttk.LabelFrame(frame, text="Selected Component", padding=8)
        editor.grid(row=2, column=1, sticky="nsew")
        for col in range(2):
            editor.columnconfigure(col, weight=1)

        ttk.Label(editor, textvariable=self.component_info_var).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        ttk.Label(editor, text="Component type").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        type_box = ttk.Combobox(
            editor,
            textvariable=self.vars["component_kind"],
            state="readonly",
            values=["keyboard", "delay", "mouse"],
        )
        type_box.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        type_box.bind("<<ComboboxSelected>>", lambda *_: self._toggle_component_editor_sections())

        self.keyboard_editor = ttk.LabelFrame(editor, text="Keyboard", padding=6)
        self.keyboard_editor.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        for col in range(2):
            self.keyboard_editor.columnconfigure(col, weight=1)

        ttk.Label(self.keyboard_editor, text="Known key").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.key_name_box = ttk.Combobox(
            self.keyboard_editor,
            textvariable=self.vars["component_key_name"],
            values=sorted(KEYBOARD_USAGE_TO_NAME.values(), key=str.upper),
        )
        self.key_name_box.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self.key_name_box.bind("<<ComboboxSelected>>", self.on_known_key_selected)

        ttk.Label(self.keyboard_editor, text="Display name").grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Entry(
            self.keyboard_editor,
            textvariable=self.vars["component_display_name"],
        ).grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(self.keyboard_editor, text="HID usage").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(
            self.keyboard_editor,
            textvariable=self.vars["component_hid_usage"],
        ).grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        key_down_check = ttk.Checkbutton(
            self.keyboard_editor,
            text="Key down event",
            variable=self.vars["component_is_down"],
        )
        key_down_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        self._add_tooltip(key_down_check, "Checked means this keyboard component is a key-down event; unchecked means key-up.")

        self.delay_editor = ttk.LabelFrame(editor, text="Delay", padding=6)
        self.delay_editor.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        self.delay_editor.columnconfigure(1, weight=1)
        ttk.Label(self.delay_editor, text="Duration ms").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(self.delay_editor, textvariable=self.vars["component_delay"]).grid(
            row=0, column=1, sticky="ew", padx=4, pady=4
        )

        self.mouse_editor = ttk.LabelFrame(editor, text="Mouse Button", padding=6)
        self.mouse_editor.grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        self.mouse_editor.columnconfigure(1, weight=1)
        ttk.Label(self.mouse_editor, text="Button hidUsage").grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Entry(self.mouse_editor, textvariable=self.vars["component_mouse_usage"]).grid(
            row=0, column=1, sticky="ew", padx=4, pady=4
        )
        button_down_check = ttk.Checkbutton(
            self.mouse_editor,
            text="Button down event",
            variable=self.vars["component_is_down"],
        )
        button_down_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        self._add_tooltip(
            button_down_check,
            "Checked means this mouse component is a button-down event; unchecked means button-up.",
        )

        actions = ttk.Frame(editor)
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)

        action_row_1 = ttk.Frame(actions)
        action_row_1.grid(row=0, column=0, sticky="w")
        update_component_button = ttk.Button(action_row_1, text="Update Component", command=self.update_component)
        update_component_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(update_component_button, "Write the editor values back into the selected component.")

        add_keyboard_button = ttk.Button(action_row_1, text="Add Keyboard", command=self.add_keyboard_component)
        add_keyboard_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(add_keyboard_button, "Insert a new keyboard component after the current selection.")

        add_delay_button = ttk.Button(action_row_1, text="Add Delay", command=self.add_delay_component)
        add_delay_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(add_delay_button, "Insert a new delay component after the current selection.")

        delete_component_button = ttk.Button(action_row_1, text="Delete Component", command=self.delete_component)
        delete_component_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(delete_component_button, "Delete the selected component from the sequence.")

        action_row_2 = ttk.Frame(actions)
        action_row_2.grid(row=1, column=0, sticky="w")
        move_up_button = ttk.Button(action_row_2, text="Move Up", command=lambda: self.move_component(-1))
        move_up_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(move_up_button, "Move the selected component one row earlier.")

        move_down_button = ttk.Button(action_row_2, text="Move Down", command=lambda: self.move_component(1))
        move_down_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(move_down_button, "Move the selected component one row later.")

        record_replace_button = ttk.Button(
            action_row_2,
            text="Record Replace",
            command=lambda: self.start_keystroke_recording("replace"),
        )
        record_replace_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(record_replace_button, "Record keys and replace the current sequence components.")

        record_append_button = ttk.Button(
            action_row_2,
            text="Record Append",
            command=lambda: self.start_keystroke_recording("append"),
        )
        record_append_button.pack(side="left", padx=4, pady=2)
        self._add_tooltip(record_append_button, "Record keys and append them to the current sequence.")

        tools = ttk.LabelFrame(frame, text="Replace / Delay Tools", padding=8)
        tools.grid(row=3, column=1, sticky="new", pady=(10, 0))
        for col in range(4):
            tools.columnconfigure(col, weight=1)

        ttk.Label(tools, text="Replace keyboard key in sequence macros").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 6)
        )
        ttk.Label(tools, text="From").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        from_box = ttk.Combobox(
            tools,
            textvariable=self.vars["replace_from"],
            values=sorted(KEYBOARD_USAGE_TO_NAME.values(), key=str.upper),
        )
        from_box.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(tools, text="To").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        to_box = ttk.Combobox(
            tools,
            textvariable=self.vars["replace_to"],
            values=sorted(KEYBOARD_USAGE_TO_NAME.values(), key=str.upper),
        )
        to_box.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        replace_current_button = ttk.Button(
            tools,
            text="Replace In Current Macro",
            command=lambda: self.replace_key_in_scope(filtered_only=False),
        )
        replace_current_button.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=6)
        self._add_tooltip(replace_current_button, "Replace one keyboard key everywhere in the selected macro.")

        replace_filtered_button = ttk.Button(
            tools,
            text="Replace In Filtered Macros",
            command=lambda: self.replace_key_in_scope(filtered_only=True),
        )
        replace_filtered_button.grid(row=2, column=2, columnspan=2, sticky="w", padx=4, pady=6)
        self._add_tooltip(replace_filtered_button, "Replace one keyboard key across all filtered macros.")

        ttk.Separator(tools, orient="horizontal").grid(row=3, column=0, columnspan=4, sticky="ew", padx=4, pady=8)

        ttk.Label(tools, text="Delay utilities").grid(
            row=4, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 6)
        )
        ttk.Label(tools, text="New delay ms").grid(row=5, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(tools, textvariable=self.vars["replace_delay"]).grid(
            row=5, column=1, sticky="ew", padx=4, pady=4
        )
        set_current_delays_button = ttk.Button(
            tools, text="Set All Delays In Current Macro", command=self.set_all_delays_current
        )
        set_current_delays_button.grid(row=6, column=0, sticky="w", padx=4, pady=6)
        self._add_tooltip(set_current_delays_button, "Set every delay component in the selected macro to the new value.")

        set_filtered_delays_button = ttk.Button(
            tools,
            text="Set All Delays In Filtered Macros",
            command=lambda: self.set_all_delays_in_scope(filtered_only=True),
        )
        set_filtered_delays_button.grid(row=6, column=1, sticky="w", padx=4, pady=6)
        self._add_tooltip(set_filtered_delays_button, "Set every delay component across the filtered macros.")

        set_default_delay_button = ttk.Button(
            tools, text="Set Sequence Default Delay", command=self.set_sequence_default_delay
        )
        set_default_delay_button.grid(row=6, column=2, sticky="w", padx=4, pady=6)
        self._add_tooltip(set_default_delay_button, "Update the selected macro's sequence default delay field.")

        set_filtered_default_delay_button = ttk.Button(
            tools,
            text="Set Default Delay In Filtered Macros",
            command=lambda: self.set_sequence_default_delay_in_scope(filtered_only=True),
        )
        set_filtered_default_delay_button.grid(row=6, column=3, sticky="w", padx=4, pady=6)
        self._add_tooltip(
            set_filtered_default_delay_button,
            "Update the sequence default delay field across all filtered macros.",
        )

        ttk.Label(
            tools,
            text=(
                "These tools only operate on SEQUENCE macros. Filter first if you want to target a specific subset."
            ),
            wraplength=1100,
            justify="left",
        ).grid(row=7, column=0, columnspan=4, sticky="w", padx=4, pady=(8, 0))

    def _build_keystroke_tab(self) -> None:
        """Build the simple keystroke macro editor."""
        frame = self.keystroke_tab
        for col in range(2):
            frame.columnconfigure(col, weight=1)

        ttk.Label(
            frame,
            text="For simple G Hub keystrokes, edit the key code and modifier list here.",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(frame, text="Known key").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.keystroke_key_box = ttk.Combobox(
            frame,
            textvariable=self.vars["keystroke_key_name"],
            values=sorted(KEYBOARD_USAGE_TO_NAME.values(), key=str.upper),
        )
        self.keystroke_key_box.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        self.keystroke_key_box.bind("<<ComboboxSelected>>", self.on_keystroke_key_selected)

        ttk.Label(frame, text="Code / HID usage").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(frame, textvariable=self.vars["keystroke_code"]).grid(
            row=2, column=1, sticky="ew", padx=4, pady=4
        )

        modifier_frame = ttk.LabelFrame(frame, text="Modifiers", padding=6)
        modifier_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=8)
        for col in range(4):
            modifier_frame.columnconfigure(col, weight=1)
        for idx, (name, usage) in enumerate(COMMON_MODIFIERS):
            modifier_check = ttk.Checkbutton(
                modifier_frame,
                text=f"{name} ({usage})",
                variable=self.keystroke_modifier_vars[usage],
            )
            modifier_check.grid(row=idx // 4, column=idx % 4, sticky="w", padx=4, pady=4)
            self._add_tooltip(modifier_check, f"Include {name} as a modifier in the keystroke macro.")

        update_keystroke_button = ttk.Button(frame, text="Update Keystroke Macro", command=self.update_keystroke_macro)
        update_keystroke_button.grid(row=4, column=0, sticky="w", padx=4, pady=8)
        self._add_tooltip(update_keystroke_button, "Apply the keystroke fields to the selected keystroke macro.")

    def _build_record_tab(self) -> None:
        """Build the guided key-recording tab for sequence macros."""
        frame = self.record_tab
        for col in range(2):
            frame.columnconfigure(col, weight=1)

        ttk.Label(
            frame,
            text=(
                "Record physical key presses into SEQUENCE components. Press Start, type in the capture "
                "window, then press Escape to finish."
            ),
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        start_replace_button = ttk.Button(
            frame,
            text="Start Recording And Replace Sequence",
            command=lambda: self.start_keystroke_recording("replace"),
        )
        start_replace_button.grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self._add_tooltip(start_replace_button, "Record live key input and replace the selected sequence.")

        start_append_button = ttk.Button(
            frame,
            text="Start Recording And Append To Sequence",
            command=lambda: self.start_keystroke_recording("append"),
        )
        start_append_button.grid(row=1, column=1, sticky="w", padx=4, pady=6)
        self._add_tooltip(start_append_button, "Record live key input and append it to the selected sequence.")
        record_actual_timing_check = ttk.Checkbutton(
            frame,
            text="Use actual input timing",
            variable=self.vars["record_use_actual_delay"],
        )
        record_actual_timing_check.grid(row=2, column=0, sticky="w", padx=4, pady=(4, 0))
        self._add_tooltip(
            record_actual_timing_check,
            "When enabled, recording uses your real key timing unless Use default delay is checked on the sequence.",
        )

        ttk.Label(
            frame,
            text=(
                "Notes: only keys that can be mapped to known HID usages are recorded. Modifier keys are "
                "recorded too. When actual timing is off, the recorder uses the current sequence default delay "
                "value for inserted delay rows."
            ),
            wraplength=900,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0))

    def _build_raw_tab(self) -> None:
        """Build the raw JSON viewer/editor tab for the selected macro node."""
        frame = self.raw_tab
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.raw_text = tk.Text(frame, wrap="none", height=24)
        self.raw_text.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.raw_text.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.raw_text.configure(yscrollcommand=y_scroll.set)

    def _bind_change_tracking(self) -> None:
        """Hook variable changes that should immediately refresh visible lists."""
        self.vars["search"].trace_add("write", lambda *_: self.refresh_macro_list())

    def _bind_shortcuts(self) -> None:
        """Register application-wide keyboard shortcuts for common editing actions."""
        self.root.bind_all("<Control-s>", self.on_save_shortcut, add="+")
        self.root.bind_all("<Control-S>", self.on_save_shortcut, add="+")
        self.root.bind_all("<Control-c>", self.on_copy_shortcut, add="+")
        self.root.bind_all("<Control-C>", self.on_copy_shortcut, add="+")
        self.root.bind_all("<Control-v>", self.on_paste_shortcut, add="+")
        self.root.bind_all("<Control-V>", self.on_paste_shortcut, add="+")
        self.root.bind_all("<Delete>", self.on_delete_shortcut, add="+")
        self.root.bind_all("<Control-z>", self.on_undo_shortcut, add="+")
        self.root.bind_all("<Control-Z>", self.on_undo_shortcut, add="+")
        self.root.bind_all("<Control-y>", self.on_redo_shortcut, add="+")
        self.root.bind_all("<Control-Y>", self.on_redo_shortcut, add="+")

    def _focused_widget(self):
        return self.root.focus_get()

    def _focus_is_macro_list(self) -> bool:
        return self._focused_widget() == self.macro_listbox

    def _focus_is_component_tree(self) -> bool:
        return self._focused_widget() == self.component_tree

    def _focus_is_text_input(self) -> bool:
        widget = self._focused_widget()
        return isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Text))

    def on_copy_shortcut(self, event=None):
        if self._focus_is_component_tree():
            self.copy_component()
            return "break"
        return None

    def on_save_shortcut(self, event=None):
        self.save_file()
        return "break"

    def on_paste_shortcut(self, event=None):
        if self._focus_is_component_tree():
            self.paste_component_over_selection()
            return "break"
        return None

    def on_delete_shortcut(self, event=None):
        if self._focus_is_macro_list():
            self.delete_selected_macro()
            return "break"
        if self._focus_is_component_tree():
            self.delete_component()
            return "break"
        return None

    def on_undo_shortcut(self, event=None):
        if self._focus_is_text_input():
            return None
        self.undo()
        return "break"

    def on_redo_shortcut(self, event=None):
        if self._focus_is_text_input():
            return None
        self.redo()
        return "break"

    def mark_dirty(self) -> None:
        self.is_dirty = True
        self._update_status()

    def _selection_state(self) -> dict:
        record = self.current_record()
        macro_id = record["id"] if record else None
        return {
            "macro_id": macro_id,
            "component_index": self.current_component_index,
        }

    def _push_undo_state(self) -> None:
        """Capture the current data and selection so the edit can be undone later."""
        if not self.data:
            return
        snapshot = {
            "data": copy.deepcopy(self.data),
            "selection": self._selection_state(),
        }
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _restore_history_state(self, snapshot: dict) -> None:
        """Restore a previously captured undo/redo snapshot and reselect the same macro."""
        self.data = copy.deepcopy(snapshot["data"])
        self.applications_by_id = self._build_application_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self._refresh_application_filter_values()
        self.refresh_macro_list()

        macro_id = snapshot.get("selection", {}).get("macro_id")
        component_index = snapshot.get("selection", {}).get("component_index")
        if macro_id:
            for real_index, record in enumerate(self.macro_records):
                if record["id"] == macro_id:
                    self.current_real_index = real_index
                    break
        if self.current_real_index is not None:
            self.refresh_macro_list()
            self.current_component_index = component_index
            record = self.current_record()
            if record:
                self.populate_form(record)
        else:
            self.clear_form()
        self._update_status()

    def undo(self) -> None:
        """Revert the most recent edit tracked in the undo stack."""
        if not self.undo_stack:
            return
        self.redo_stack.append({"data": copy.deepcopy(self.data), "selection": self._selection_state()})
        snapshot = self.undo_stack.pop()
        self._restore_history_state(snapshot)
        self.is_dirty = True
        self._update_status()

    def redo(self) -> None:
        """Reapply the most recently undone edit."""
        if not self.redo_stack:
            return
        self.undo_stack.append({"data": copy.deepcopy(self.data), "selection": self._selection_state()})
        snapshot = self.redo_stack.pop()
        self._restore_history_state(snapshot)
        self.is_dirty = True
        self._update_status()

    def reorder_filtered_macros(self) -> None:
        """Sort currently filtered macros by name within each source JSON list."""
        if not self.filtered_indices:
            messagebox.showinfo("No macros", "There are no filtered macros to reorder.")
            return

        selected_record = self.current_record()
        selected_macro_id = selected_record["id"] if selected_record else None
        reverse = self.vars["sort_mode"].get().strip().upper() == "Z-A"

        groups = {}
        for real_index in self.filtered_indices:
            record = self.macro_records[real_index]
            parent_list = record.get("parent_list")
            parent_list_index = record.get("parent_list_index")
            if parent_list is None or parent_list_index is None:
                continue
            bucket = groups.setdefault(
                id(parent_list),
                {"parent_list": parent_list, "records": []},
            )
            bucket["records"].append(record)

        if not groups:
            messagebox.showinfo("Unsupported location", "The filtered macros could not be reordered in place.")
            return

        self._push_undo_state()
        moved = 0
        for group in groups.values():
            records = group["records"]
            if len(records) < 2:
                continue
            parent_list = group["parent_list"]
            target_indices = sorted(record["parent_list_index"] for record in records)
            sorted_nodes = [
                copy.deepcopy(record["node"])
                for record in sorted(
                    records,
                    key=lambda item: (item.get("name", "").lower(), item.get("id", "")),
                    reverse=reverse,
                )
            ]
            for index, node in zip(target_indices, sorted_nodes):
                parent_list[index] = node
                moved += 1

        if moved == 0:
            messagebox.showinfo("No changes", "The filtered macros are already fixed in place or too few to reorder.")
            return

        self.mark_dirty()
        self.applications_by_id = self._build_application_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        if selected_macro_id:
            for real_index, record in enumerate(self.macro_records):
                if record["id"] == selected_macro_id:
                    self.current_real_index = real_index
                    break
            if self.current_real_index is not None:
                self.refresh_macro_list()

        direction_label = "A-Z" if not reverse else "Z-A"
        messagebox.showinfo(
            "Reordered",
            f"Reordered {moved} filtered macros by name ({direction_label}) within their JSON lists.",
        )

    def compact_filtered_macros(self) -> None:
        """Remove filtered macros from their original lists and reinsert them compactly."""
        if not self.filtered_indices:
            messagebox.showinfo("No macros", "There are no filtered macros to compact.")
            return

        selected_record = self.current_record()
        selected_macro_id = selected_record["id"] if selected_record else None
        reverse = self.vars["sort_mode"].get().strip().upper() == "Z-A"

        groups = {}
        for real_index in self.filtered_indices:
            record = self.macro_records[real_index]
            parent_list = record.get("parent_list")
            parent_list_index = record.get("parent_list_index")
            if parent_list is None or parent_list_index is None:
                continue
            bucket = groups.setdefault(
                id(parent_list),
                {"parent_list": parent_list, "records": []},
            )
            bucket["records"].append(record)

        if not groups:
            messagebox.showinfo("Unsupported location", "The filtered macros could not be compacted in place.")
            return

        self._push_undo_state()
        moved = 0
        for group in groups.values():
            records = group["records"]
            if len(records) < 2:
                continue

            parent_list = group["parent_list"]
            selected_indices = sorted(record["parent_list_index"] for record in records)
            selected_index_set = set(selected_indices)
            insert_at = selected_indices[0]
            sorted_nodes = [
                record["node"]
                for record in sorted(
                    records,
                    key=lambda item: (item.get("name", "").lower(), item.get("id", "")),
                    reverse=reverse,
                )
            ]
            remaining_nodes = [
                node for idx, node in enumerate(parent_list) if idx not in selected_index_set
            ]
            parent_list[:] = (
                remaining_nodes[:insert_at]
                + sorted_nodes
                + remaining_nodes[insert_at:]
            )
            moved += len(records)

        if moved == 0:
            messagebox.showinfo("No changes", "The filtered macros are already too isolated to compact.")
            return

        self.mark_dirty()
        self.applications_by_id = self._build_application_map()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        if selected_macro_id:
            for real_index, record in enumerate(self.macro_records):
                if record["id"] == selected_macro_id:
                    self.current_real_index = real_index
                    break
            if self.current_real_index is not None:
                self.refresh_macro_list()

        direction_label = "A-Z" if not reverse else "Z-A"
        messagebox.showinfo(
            "Compacted",
            f"Compacted {moved} filtered macros into contiguous JSON blocks and sorted them by name ({direction_label}).",
        )

    def _collect_existing_ids(self) -> set[str]:
        ids = set()

        def walk(node) -> None:
            if isinstance(node, dict):
                value = node.get("id")
                if isinstance(value, str) and value:
                    ids.add(value)
                for child in node.values():
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(self.data)
        return ids

    def _generate_unique_id(self, existing_ids: set[str]) -> str:
        while True:
            candidate = str(uuid.uuid4())
            if candidate not in existing_ids:
                existing_ids.add(candidate)
                return candidate

    def _remove_assignments_for_card_ids(self, card_ids: set[str]) -> int:
        if not card_ids:
            return 0

        removed = 0
        profiles = self.data.get("profiles", {}).get("profiles", [])
        for profile in profiles:
            assignments = profile.get("assignments")
            if not isinstance(assignments, list):
                continue

            kept_assignments = []
            for assignment in assignments:
                if assignment.get("cardId") in card_ids:
                    removed += 1
                    continue
                kept_assignments.append(assignment)
            profile["assignments"] = kept_assignments

        return removed

    def _find_profile_for_application(self, application_id: str) -> dict | None:
        profiles = self.data.get("profiles", {}).get("profiles", [])
        for profile in profiles:
            if profile.get("applicationId") == application_id:
                return profile
        return None

    def _detect_device_prefix_from_lighting(self, profile_id: str) -> str | None:
        detected = None

        def walk(node) -> None:
            nonlocal detected
            if detected is not None:
                return
            if isinstance(node, dict):
                if (
                    node.get("attribute") == "SOFTWARE_LIGHTING_SETTINGS"
                    and node.get("profileId") == profile_id
                ):
                    devices = node.get("softwareLightingSettings", {}).get("devices", {})
                    if isinstance(devices, dict):
                        for device_name in devices.keys():
                            if isinstance(device_name, str) and device_name:
                                detected = device_name
                                return
                for child in node.values():
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(self.data)
        return detected

    def _default_assignment_device_prefix(self, application_id: str) -> str:
        profile = self._find_profile_for_application(application_id)
        if profile is not None:
            detected = self._detect_device_prefix_from_lighting(profile.get("id", ""))
            if detected:
                return detected
            assignments = profile.get("assignments", [])
            if isinstance(assignments, list):
                for assignment in assignments:
                    slot_id = assignment.get("slotId", "")
                    if isinstance(slot_id, str) and "_" in slot_id:
                        return slot_id.split("_", 1)[0]

        record = self.current_record()
        if record:
            for slot_id in record.get("assigned_slots", []):
                if isinstance(slot_id, str) and "_" in slot_id:
                    return slot_id.split("_", 1)[0]

        return "g910"

    def _infer_assignment_device_prefix(self, application_id: str) -> str:
        explicit_value = self.vars["assignment_device_prefix"].get().strip().lower()
        if explicit_value:
            return explicit_value
        return self._default_assignment_device_prefix(application_id)

    def _normalize_assignment_button(self, raw_value: str) -> str:
        value = raw_value.strip().lower()
        if not value:
            return ""
        if value.startswith("g") and value[1:].isdigit():
            return value
        if value.isdigit():
            return f"g{value}"
        return value

    def _selected_memory_suffixes(self) -> list[str]:
        selected = [
            memory_name
            for memory_name, var in self.assignment_memory_vars.items()
            if var.get()
        ]
        return selected

    def _populate_assignment_controls(self, record: dict) -> None:
        self.vars["assignment_device_prefix"].set(
            self._default_assignment_device_prefix(record.get("application_id", ""))
        )
        button_value = ""
        selected_memories = set()
        shifted = False
        for slot_id in record.get("assigned_slots", []):
            parts = str(slot_id).split("_")
            if len(parts) not in {3, 4}:
                continue
            button_part = parts[1]
            memory_part = parts[2]
            if not button_value:
                button_value = button_part
            if memory_part in self.assignment_memory_vars:
                selected_memories.add(memory_part)
            if len(parts) == 4 and parts[3] == "shifted":
                shifted = True

        self.vars["assignment_button_slot"].set(button_value)
        self.assignment_shifted_var.set(shifted)
        if selected_memories:
            for memory_name, var in self.assignment_memory_vars.items():
                var.set(memory_name in selected_memories)
        else:
            self.assignment_memory_vars["m1"].set(True)
            self.assignment_memory_vars["m2"].set(False)
            self.assignment_memory_vars["m3"].set(False)

    def assign_selected_macro_to_slots(self) -> None:
        """Assign the current macro to one or more G-key slots in the profile data."""
        record = self.current_record()
        if not record:
            messagebox.showinfo("No macro", "Select a macro first.")
            return

        button_id = self._normalize_assignment_button(self.vars["assignment_button_slot"].get())
        if not button_id:
            messagebox.showinfo("Missing key", "Enter a G key like 2 or g2.")
            return

        memory_suffixes = self._selected_memory_suffixes()
        if not memory_suffixes:
            messagebox.showinfo("Missing memory", "Select at least one memory slot.")
            return

        application_id = record.get("application_id", "")
        profile = self._find_profile_for_application(application_id)
        if profile is None:
            messagebox.showerror(
                "Profile not found",
                f"No profile was found for application {application_id}.",
            )
            return

        assignments = profile.setdefault("assignments", [])
        if not isinstance(assignments, list):
            messagebox.showerror("Invalid profile", "The profile assignments list is not editable.")
            return

        self._push_undo_state()
        macro_id = record["id"]
        device_prefix = self._infer_assignment_device_prefix(application_id)
        is_shifted = bool(self.assignment_shifted_var.get())
        target_slot_ids = set()
        for memory_name in memory_suffixes:
            slot_id = f"{device_prefix}_{button_id}_{memory_name}"
            if is_shifted:
                slot_id += "_shifted"
            target_slot_ids.add(slot_id)
        removed_existing = 0
        kept_assignments = []
        for assignment in assignments:
            if assignment.get("slotId") in target_slot_ids:
                removed_existing += 1
                continue
            kept_assignments.append(assignment)

        for slot_id in sorted(target_slot_ids):
            kept_assignments.append({"cardId": macro_id, "slotId": slot_id})
        profile["assignments"] = kept_assignments

        self.mark_dirty()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        selected_macro_id = macro_id
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        for real_index, refreshed_record in enumerate(self.macro_records):
            if refreshed_record["id"] == selected_macro_id:
                self.current_real_index = real_index
                break
        if self.current_real_index is not None:
            self.refresh_macro_list()

        replaced_text = (
            f" Replaced {removed_existing} existing assignment(s) on those slot(s)."
            if removed_existing
            else ""
        )
        assigned_list = ", ".join(sorted(target_slot_ids))
        self.assignment_status_var.set(
            f"Assigned {record['name']} to {assigned_list}.{replaced_text}"
        )

    def clear_selected_macro_assignments(self) -> None:
        """Remove any profile slot assignments that point at the selected macro."""
        record = self.current_record()
        if not record:
            messagebox.showinfo("No macro", "Select a macro first.")
            return

        macro_id = record["id"]
        existing_assignments = len(self.profile_assignments_by_card_id.get(macro_id, []))
        if existing_assignments == 0:
            messagebox.showinfo("No assignments", "The selected macro has no assignments to clear.")
            return

        self._push_undo_state()
        removed = self._remove_assignments_for_card_ids({macro_id})
        self.mark_dirty()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        selected_macro_id = macro_id
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        for real_index, refreshed_record in enumerate(self.macro_records):
            if refreshed_record["id"] == selected_macro_id:
                self.current_real_index = real_index
                break
        if self.current_real_index is not None:
            self.refresh_macro_list()

        self.assignment_status_var.set(
            f"Removed {removed} assignment(s) for {record['name']}."
        )

    def duplicate_filtered_macros(self) -> None:
        """Duplicate every macro in the current filtered result set."""
        if not self.filtered_indices:
            messagebox.showinfo("No macros", "There are no filtered macros to duplicate.")
            return

        selected_record = self.current_record()
        selected_macro_id = selected_record["id"] if selected_record else None
        selected_duplicate_id = None
        reverse = self.vars["sort_mode"].get().strip().upper() == "Z-A"
        delete_originals = bool(self.vars["delete_originals_after_duplicate"].get())

        groups = {}
        for real_index in self.filtered_indices:
            record = self.macro_records[real_index]
            parent_list = record.get("parent_list")
            parent_list_index = record.get("parent_list_index")
            if parent_list is None or parent_list_index is None:
                continue
            bucket = groups.setdefault(
                id(parent_list),
                {"parent_list": parent_list, "records": []},
            )
            bucket["records"].append(record)

        if not groups:
            messagebox.showinfo("Unsupported location", "The filtered macros could not be duplicated in place.")
            return

        self._push_undo_state()
        existing_ids = self._collect_existing_ids()
        created = 0
        removed = 0
        removed_assignments = 0
        for group in groups.values():
            records = group["records"]
            if not records:
                continue

            parent_list = group["parent_list"]
            sorted_records = sorted(
                records,
                key=lambda item: (item.get("name", "").lower(), item.get("id", "")),
                reverse=reverse,
            )
            duplicated_nodes = []
            for record in sorted_records:
                duplicate_node = copy.deepcopy(record["node"])
                duplicate_node["id"] = self._generate_unique_id(existing_ids)
                duplicated_nodes.append(duplicate_node)
                created += 1
                if record["id"] == selected_macro_id and selected_duplicate_id is None:
                    selected_duplicate_id = duplicate_node["id"]

            if delete_originals:
                old_ids = {record["id"] for record in records}
                selected_indices = sorted(record["parent_list_index"] for record in records)
                selected_index_set = set(selected_indices)
                insert_at = selected_indices[0]
                remaining_nodes = [
                    node for idx, node in enumerate(parent_list) if idx not in selected_index_set
                ]
                parent_list[:] = (
                    remaining_nodes[:insert_at]
                    + duplicated_nodes
                    + remaining_nodes[insert_at:]
                )
                removed += len(records)
                removed_assignments += self._remove_assignments_for_card_ids(old_ids)
            else:
                insert_at = max(record["parent_list_index"] for record in records) + 1
                parent_list[insert_at:insert_at] = duplicated_nodes

        if created == 0:
            messagebox.showinfo("No changes", "There were no filtered macros to duplicate.")
            return

        self.mark_dirty()
        self.applications_by_id = self._build_application_map()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        target_macro_id = selected_duplicate_id or (None if delete_originals else selected_macro_id)
        if target_macro_id:
            for real_index, record in enumerate(self.macro_records):
                if record["id"] == target_macro_id:
                    self.current_real_index = real_index
                    break
            if self.current_real_index is not None:
                self.refresh_macro_list()

        direction_label = "A-Z" if not reverse else "Z-A"
        if delete_originals:
            message = (
                f"Duplicated {created} filtered macros with fresh IDs, deleted {removed} originals, "
                f"removed {removed_assignments} stale assignments, and rebuilt them in "
                f"sorted order ({direction_label})."
            )
        else:
            message = (
                f"Duplicated {created} filtered macros with fresh IDs and inserted the copies in "
                f"sorted order ({direction_label})."
            )
        messagebox.showinfo("Duplicated", message)

    def _editable_anchor_record(self) -> dict | None:
        record = self.current_record()
        if (
            record
            and record.get("parent_list") is not None
            and record.get("parent_list_index") is not None
            and not record["node"].get("readOnly", False)
        ):
            return record

        candidates = []
        for real_index in self.filtered_indices:
            candidate = self.macro_records[real_index]
            if (
                candidate.get("parent_list") is not None
                and candidate.get("parent_list_index") is not None
                and not candidate["node"].get("readOnly", False)
            ):
                candidates.append(candidate)

        if candidates:
            return candidates[-1]
        return None

    def _generate_unique_macro_name(self, application_id: str, base_name: str = "New Macro") -> str:
        existing_names = {
            record.get("name", "")
            for record in self.macro_records
            if record.get("application_id") == application_id
        }
        if base_name not in existing_names:
            return base_name

        suffix = 2
        while True:
            candidate = f"{base_name} {suffix}"
            if candidate not in existing_names:
                return candidate
            suffix += 1

    def _build_new_macro_node(self, anchor_record: dict, existing_ids: set[str]) -> dict:
        application_id = anchor_record.get("application_id", "")
        category = anchor_record["node"].get("category", "Macros")
        return {
            "applicationId": application_id,
            "attribute": "MACRO_PLAYBACK",
            "category": category,
            "id": self._generate_unique_id(existing_ids),
            "macro": {
                "sequence": {
                    "components": [],
                    "defaultDelay": 50,
                    "useDefaultDelay": True,
                    "useSimpleActions": True,
                },
                "toggleSequence": {},
                "type": "SEQUENCE",
            },
            "name": self._generate_unique_macro_name(application_id),
        }

    def create_new_macro(self) -> None:
        """Create a new editable macro alongside the current editable context."""
        anchor_record = self._editable_anchor_record()
        if not anchor_record:
            messagebox.showinfo(
                "No editable anchor",
                "Select an editable macro, or filter to an application that already has editable macros.",
            )
            return

        parent_list = anchor_record.get("parent_list")
        parent_list_index = anchor_record.get("parent_list_index")
        if parent_list is None or parent_list_index is None:
            messagebox.showinfo(
                "Unsupported location",
                "The selected macro is not in an editable list location.",
            )
            return

        self._push_undo_state()
        existing_ids = self._collect_existing_ids()
        new_node = self._build_new_macro_node(anchor_record, existing_ids)
        insert_at = parent_list_index + 1
        parent_list.insert(insert_at, new_node)

        if self.vars["type_filter"].get().strip().upper() not in {"ALL", "SEQUENCE"}:
            self.vars["type_filter"].set("All")

        self.mark_dirty()
        self.applications_by_id = self._build_application_map()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        for real_index, record in enumerate(self.macro_records):
            if record["id"] == new_node["id"]:
                self.current_real_index = real_index
                break
        if self.current_real_index is not None:
            self.refresh_macro_list()
            record = self.current_record()
            if record:
                self.populate_form(record)
            self.root.after_idle(self._focus_macro_name_entry)

        self.assignment_status_var.set(
            f"Created {new_node['name']} in {anchor_record.get('application_name', '<unknown application>')}."
        )

    def _focus_macro_name_entry(self) -> None:
        """Focus the macro name field and select its contents for quick renaming."""
        entry = getattr(self, "macro_name_entry", None)
        if entry is None:
            return
        entry.focus_set()
        entry.selection_range(0, tk.END)
        entry.icursor(tk.END)

    def delete_selected_macro(self) -> None:
        """Delete the selected editable macro and remove any assignments pointing to it."""
        record = self.current_record()
        if not record:
            messagebox.showinfo("No macro", "Select a macro first.")
            return
        parent_list = record.get("parent_list")
        parent_list_index = record.get("parent_list_index")
        if (
            parent_list is None
            or parent_list_index is None
            or record["node"].get("readOnly", False)
        ):
            messagebox.showinfo("Cannot delete", "The selected macro is not in an editable location.")
            return

        macro_name = record.get("name", "<unnamed macro>")
        if not messagebox.askyesno(
            "Delete macro",
            f"Delete macro '{macro_name}'?\n\nAny assignments pointing to it will be removed too.",
        ):
            return

        selected_real_index = self.current_real_index
        self._push_undo_state()
        parent_list.pop(parent_list_index)
        removed_assignments = self._remove_assignments_for_card_ids({record["id"]})

        self.mark_dirty()
        self.applications_by_id = self._build_application_map()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.refresh_macro_list()

        if self.macro_records:
            target_index = 0
            if selected_real_index is not None:
                target_index = min(selected_real_index, len(self.macro_records) - 1)
            self.current_real_index = target_index
            self.refresh_macro_list()

        removed_text = f" Removed {removed_assignments} assignment(s)." if removed_assignments else ""
        self.assignment_status_var.set(f"Deleted {macro_name}.{removed_text}")

    def _update_status(self) -> None:
        """Refresh the window status line and save button state."""
        if self.source_kind == "settings_db" and self.settings_db_path:
            file_part = f"settings.db: {self.settings_db_path}"
        else:
            file_part = str(self.file_path) if self.file_path else "No file loaded"
        macro_part = f"{len(self.macro_records)} macros"
        dirty_part = "modified" if self.is_dirty else "saved"
        self.status_var.set(f"{file_part} | {macro_part} | {dirty_part}")
        if hasattr(self, "save_button"):
            self.save_button.configure(text="Save*" if self.is_dirty else "Save")

    def open_file(self) -> None:
        """Prompt for and load a ghub.json-style export file."""
        path = filedialog.askopenfilename(
            title="Open G Hub JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path(__file__).resolve().parent),
        )
        if path:
            self.load_file(Path(path))

    def open_settings_db(self) -> None:
        """Prompt for and load G Hub's sqlite settings database."""
        default_path = Path.home() / "AppData" / "Local" / "LGHUB" / "settings.db"
        path = filedialog.askopenfilename(
            title="Open LG Hub settings.db",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
            initialdir=str(default_path.parent if default_path.parent.exists() else Path.home()),
            initialfile=default_path.name,
        )
        if path:
            self.load_settings_db(Path(path))

    def reload_file(self) -> None:
        """Reload the currently opened source from disk."""
        if self.source_kind == "settings_db" and self.settings_db_path:
            self.load_settings_db(self.settings_db_path)
        elif self.file_path:
            self.load_file(self.file_path)

    def load_file(self, path: Path) -> None:
        """Load macro data from a JSON file path."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Open failed", f"Could not load JSON:\n{exc}")
            return

        self.file_path = Path(path)
        self.source_kind = "json"
        self.settings_db_path = None
        self.settings_db_row_id = None
        self._load_data(data)

    def load_settings_db(self, path: Path) -> None:
        """Load macro data from the DATA row inside G Hub's sqlite database."""
        try:
            with sqlite3.connect(path) as conn:
                row = conn.execute(
                    "SELECT _id, FILE FROM DATA ORDER BY _id LIMIT 1"
                ).fetchone()
        except Exception as exc:
            messagebox.showerror("Open failed", f"Could not read settings.db:\n{exc}")
            return
        if not row:
            messagebox.showerror("Open failed", "settings.db does not contain a DATA row.")
            return
        row_id, blob = row
        try:
            data = json.loads(blob.decode("utf-8"))
        except Exception as exc:
            messagebox.showerror("Open failed", f"Could not decode DATA.FILE JSON:\n{exc}")
            return

        self.file_path = None
        self.source_kind = "settings_db"
        self.settings_db_path = Path(path)
        self.settings_db_row_id = int(row_id)
        self._load_data(data)

    def _load_data(self, data: dict) -> None:
        """Replace the in-memory dataset and rebuild all derived lookup structures."""
        self.data = data
        self.applications_by_id = self._build_application_map()
        self.profile_assignments_by_card_id = self._build_profile_assignment_map()
        self.macro_records = self._collect_macro_records()
        self.filtered_indices = []
        self.current_real_index = None
        self.current_component_index = None
        self.is_dirty = False
        self.undo_stack = []
        self.redo_stack = []
        self._refresh_application_filter_values()
        self.refresh_macro_list()
        self._update_status()

    def _build_application_map(self) -> dict[str, dict]:
        applications = self.data.get("applications", {}).get("applications", [])
        mapping = {}
        for app in applications:
            app_id = app.get("applicationId")
            if app_id:
                mapping[app_id] = app
        return mapping

    def _build_profile_assignment_map(self) -> dict[str, list[str]]:
        mapping = {}
        profiles = self.data.get("profiles", {}).get("profiles", [])
        for profile in profiles:
            for assignment in profile.get("assignments", []):
                card_id = assignment.get("cardId")
                slot_id = assignment.get("slotId")
                if not card_id or not slot_id:
                    continue
                mapping.setdefault(card_id, []).append(slot_id)
        return mapping

    def _collect_macro_records(self) -> list[dict]:
        results = []
        macro_counter = 0

        def walk(node, path_bits, parent_list=None, parent_list_index=None):
            nonlocal macro_counter
            if isinstance(node, dict):
                if node.get("attribute") == "MACRO_PLAYBACK" and isinstance(node.get("macro"), dict):
                    app_id = node.get("applicationId", "")
                    app_info = self.applications_by_id.get(app_id, {})
                    cards_index = ""
                    if len(path_bits) >= 3 and path_bits[0] == "cards" and path_bits[1] == "cards":
                        cards_index = path_bits[2]
                    assigned_slots = self.profile_assignments_by_card_id.get(node.get("id", ""), [])
                    results.append(
                        {
                            "json_index": macro_counter,
                            "cards_index": cards_index,
                            "node": node,
                            "path": "/".join(path_bits) or "<root>",
                            "application_id": app_id,
                            "application_name": app_info.get("name", "<unknown application>"),
                            "macro_type": node.get("macro", {}).get("type", ""),
                            "name": node.get("name", ""),
                            "id": node.get("id", ""),
                            "onboardable": bool(node.get("macro", {}).get("onboardable", False)),
                            "assigned_slots": assigned_slots,
                            "parent_list": parent_list,
                            "parent_list_index": parent_list_index,
                        }
                    )
                    macro_counter += 1
                for key, value in node.items():
                    walk(value, [*path_bits, str(key)])
            elif isinstance(node, list):
                for idx, value in enumerate(node):
                    walk(value, [*path_bits, str(idx)], node, idx)

        walk(self.data, [])
        results.sort(
            key=lambda item: (
                item["application_name"].lower(),
                item["macro_type"].lower(),
                item["name"].lower(),
            )
        )
        return results

    def _refresh_application_filter_values(self) -> None:
        names = ["All Applications"]
        for app_id, app in sorted(
            self.applications_by_id.items(),
            key=lambda item: item[1].get("name", "").lower(),
        ):
            names.append(self._app_filter_label(app_id, app.get("name", "<unknown application>")))
        self.application_filter_values = names
        self.application_filter["values"] = names
        if self.vars["application_filter"].get() not in names:
            self.vars["application_filter"].set("All Applications")

    def _app_filter_label(self, app_id: str, app_name: str) -> str:
        return f"{app_name} [{app_id}]"

    def _update_application_filter_options(self) -> None:
        query = self.vars["application_filter"].get().strip().lower()
        values = getattr(self, "application_filter_values", ["All Applications"])
        if not query or query == "all applications":
            matches = values
        else:
            matches = [value for value in values if query in value.lower()]
            if "All Applications".lower().startswith(query):
                matches = ["All Applications"] + [value for value in matches if value != "All Applications"]
        self.application_filter["values"] = matches or values

    def on_application_filter_typed(self, event=None) -> None:
        if event and event.keysym in {"Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next", "Tab"}:
            return
        self._update_application_filter_options()
        self.refresh_macro_list()

    def refresh_macro_list(self) -> None:
        """Rebuild the left macro list using the active filters and restore selection when possible."""
        selected_real = self.current_real_index
        self.macro_listbox.delete(0, tk.END)
        self.filtered_indices = []

        app_filter = self.vars["application_filter"].get().strip()
        type_filter = self.vars["type_filter"].get().strip().upper()
        search = self.vars["search"].get().strip().lower()
        app_filter_lower = app_filter.lower()
        exact_application_match = app_filter in getattr(self, "application_filter_values", ["All Applications"])

        for real_index, record in enumerate(self.macro_records):
            if app_filter != "All Applications":
                expected = self._app_filter_label(record["application_id"], record["application_name"])
                if exact_application_match:
                    if expected != app_filter:
                        continue
                elif app_filter_lower and app_filter_lower not in expected.lower():
                    continue

            if type_filter and type_filter != "ALL" and record["macro_type"].upper() != type_filter:
                continue

            haystack = " ".join(
                [
                    record["name"],
                    record["application_name"],
                    record["application_id"],
                    record["id"],
                    record["macro_type"],
                    record["path"],
                ]
            ).lower()
            if search and search not in haystack:
                continue

            label = f"{record['application_name']} | {record['name']} | {record['macro_type']}"
            self.filtered_indices.append(real_index)
            self.macro_listbox.insert(tk.END, label)

        self.filtered_count_var.set(f"{len(self.filtered_indices)} shown")

        if not self.filtered_indices:
            self.current_real_index = None
            self.clear_form()
            self._update_status()
            return

        target_filtered_index = 0
        if selected_real in self.filtered_indices:
            target_filtered_index = self.filtered_indices.index(selected_real)

        self.macro_listbox.selection_clear(0, tk.END)
        self.macro_listbox.selection_set(target_filtered_index)
        self.macro_listbox.see(target_filtered_index)
        self.on_macro_select()
        self._update_status()

    def on_macro_select(self, event=None) -> None:
        selection = self.macro_listbox.curselection()
        if not selection:
            self.current_real_index = None
            self.clear_form()
            return
        filtered_index = selection[0]
        if filtered_index >= len(self.filtered_indices):
            return
        self.current_real_index = self.filtered_indices[filtered_index]
        self.current_component_index = None
        self.populate_form(self.macro_records[self.current_real_index])

    def current_record(self) -> dict | None:
        if self.current_real_index is None:
            return None
        return self.macro_records[self.current_real_index]

    def populate_form(self, record: dict) -> None:
        """Fill the right-side editors using the selected macro record."""
        node = record["node"]
        macro = node.get("macro", {})
        macro_type = macro.get("type", "")
        action_name = macro.get("actionName", "")

        self.vars["macro_name"].set(node.get("name", ""))
        self.vars["json_index"].set(str(record.get("json_index", "")))
        self.vars["cards_index"].set(str(record.get("cards_index", "")))
        self.vars["onboardable"].set("Yes" if record.get("onboardable") else "No")
        self.vars["assigned_slots"].set(", ".join(record.get("assigned_slots", [])))
        self.vars["application_name"].set(record["application_name"])
        self.vars["application_id"].set(record["application_id"])
        self.vars["macro_type"].set(macro_type)
        self.vars["macro_id"].set(node.get("id", ""))
        self.vars["action_name"].set(action_name)
        self._populate_assignment_controls(record)
        self.assignment_status_var.set("")

        if macro_type == "SEQUENCE":
            sequence = macro.get("sequence", {})
            self.vars["sequence_default_delay"].set(str(sequence.get("defaultDelay", "")))
            self.vars["sequence_use_default_delay"].set(bool(sequence.get("useDefaultDelay", False)))
            self.vars["sequence_use_simple_actions"].set(bool(sequence.get("useSimpleActions", False)))
            self.vars["show_up_down"].set(bool(sequence.get("showUpDown", False)))
            self.refresh_component_tree()
        else:
            self.clear_sequence_form()

        if macro_type == "KEYSTROKE":
            self.populate_keystroke_form(macro)
        else:
            self.clear_keystroke_form()

        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert("1.0", json.dumps(node, indent=2, ensure_ascii=False))

    def clear_form(self) -> None:
        for key in [
            "macro_name",
            "json_index",
            "cards_index",
            "onboardable",
            "assigned_slots",
            "application_name",
            "application_id",
            "macro_type",
            "macro_id",
            "action_name",
        ]:
            self.vars[key].set("")
        self.vars["assignment_device_prefix"].set("")
        self.vars["assignment_button_slot"].set("")
        self.assignment_memory_vars["m1"].set(True)
        self.assignment_memory_vars["m2"].set(False)
        self.assignment_memory_vars["m3"].set(False)
        self.assignment_shifted_var.set(False)
        self.assignment_status_var.set("")
        self.clear_sequence_form()
        self.clear_keystroke_form()
        self.raw_text.delete("1.0", tk.END)

    def clear_sequence_form(self) -> None:
        self.vars["sequence_default_delay"].set("")
        self.vars["sequence_use_default_delay"].set(False)
        self.vars["sequence_use_simple_actions"].set(False)
        self.vars["show_up_down"].set(False)
        self.sequence_info_var.set("")
        self.component_info_var.set("")
        self.component_tree.delete(*self.component_tree.get_children())
        self._set_summary_text("")
        self.current_component_index = None
        self.clear_component_editor()

    def clear_keystroke_form(self) -> None:
        self.vars["keystroke_key_name"].set("")
        self.vars["keystroke_code"].set("")
        for var in self.keystroke_modifier_vars.values():
            var.set(False)

    def populate_keystroke_form(self, macro: dict) -> None:
        keystroke = macro.get("keystroke", {})
        code = keystroke.get("code", "")
        self.vars["keystroke_code"].set(str(code))
        self.vars["keystroke_key_name"].set(KEYBOARD_USAGE_TO_NAME.get(code, ""))
        modifier_set = set(keystroke.get("modifiers", []))
        for usage, var in self.keystroke_modifier_vars.items():
            var.set(usage in modifier_set)

    def refresh_component_tree(self) -> None:
        """Rebuild the sequence component tree and its summary counters."""
        record = self.current_record()
        if not record:
            return
        components = self.get_components(record)
        self.component_tree.delete(*self.component_tree.get_children())
        self._set_summary_text(self._format_sequence_summary(components))
        keyboard_count = 0
        delay_count = 0
        mouse_count = 0
        for index, component in enumerate(components):
            kind, summary, state = self.describe_component(component)
            if kind == "keyboard":
                keyboard_count += 1
            elif kind == "delay":
                delay_count += 1
            elif kind == "mouse":
                mouse_count += 1
            self.component_tree.insert("", "end", iid=str(index), values=(index, kind, summary, state))

        self.sequence_info_var.set(
            f"{len(components)} components | {keyboard_count} keyboard | {delay_count} delay | {mouse_count} mouse"
        )

        if not components:
            self.current_component_index = None
            self.clear_component_editor()
            return

        target = 0
        if self.current_component_index is not None and self.current_component_index < len(components):
            target = self.current_component_index
        self.component_tree.selection_set(str(target))
        self.component_tree.see(str(target))
        self.on_component_select()

    def get_components(self, record: dict) -> list:
        macro = record["node"].get("macro", {})
        sequence = macro.get("sequence", {})
        simple = sequence.setdefault("simpleSequence", {})
        components = simple.setdefault("components", [])
        if not isinstance(components, list):
            simple["components"] = []
            components = simple["components"]
        return components

    def describe_component(self, component: dict) -> tuple[str, str, str]:
        if "keyboard" in component:
            key = component["keyboard"]
            display = key.get("displayName") or KEYBOARD_USAGE_TO_NAME.get(key.get("hidUsage"), "")
            hid = key.get("hidUsage", "")
            state = "down" if key.get("isDown") else "up"
            return "keyboard", f"{display} ({hid}) [{state}]", state
        if "delay" in component:
            duration = component["delay"].get("durationMs", "")
            return "delay", f"Delay ({duration} ms)", f"{duration} ms"
        if "mouse" in component:
            button = component["mouse"].get("button", {})
            hid = button.get("hidUsage", "")
            state = "down" if button.get("isDown") else "up"
            return "mouse", f"Mouse button ({hid}) [{state}]", state
        return "unknown", json.dumps(component, ensure_ascii=False), ""

    def _summary_token_for_key(self, display: str) -> str:
        return SUMMARY_ARROW_SYMBOLS.get(display, display)

    def _summary_token_for_component(self, component: dict) -> str | None:
        if "keyboard" in component:
            key = component["keyboard"]
            if not key.get("isDown"):
                return None
            display = key.get("displayName") or KEYBOARD_USAGE_TO_NAME.get(key.get("hidUsage"), "")
            return self._summary_token_for_key(display or str(key.get("hidUsage", "")))
        if "mouse" in component:
            button = component["mouse"].get("button", {})
            if not button.get("isDown"):
                return None
            return f"Mouse {button.get('hidUsage', '')}"
        return None

    def _format_sequence_summary(self, components: list[dict]) -> str:
        tokens = []
        for component in components:
            token = self._summary_token_for_component(component)
            if token:
                tokens.append(token)

        if not tokens:
            return "No key/button press events to summarize."

        return " + ".join(tokens)

    def _set_summary_text(self, value: str) -> None:
        self.vars["sequence_summary"].set(value)

    def on_component_select(self, event=None) -> None:
        """Load the selected component into the component editor panel."""
        selection = self.component_tree.selection()
        if not selection:
            self.current_component_index = None
            self.clear_component_editor()
            return
        self.current_component_index = int(selection[0])
        record = self.current_record()
        if not record:
            return
        components = self.get_components(record)
        if self.current_component_index >= len(components):
            return
        component = components[self.current_component_index]
        self.populate_component_editor(component)

    def on_component_tree_press(self, event=None) -> None:
        if event is None:
            return
        self.component_drag_start_row = self.component_tree.identify_row(event.y) or None
        self.component_drag_active = False
        self.component_press_selection = tuple(self.component_tree.selection())

    def on_component_tree_drag(self, event=None) -> str | None:
        if event is None or not self.component_drag_start_row:
            return None
        target_row = self.component_tree.identify_row(event.y)
        if not target_row or target_row == self.component_drag_start_row:
            return None
        try:
            source_index = int(self.component_drag_start_row)
            target_index = int(target_row)
        except ValueError:
            return None
        if self._move_component_to_index(source_index, target_index, push_undo=not self.component_drag_active):
            self.component_drag_start_row = str(target_index)
            self.component_drag_active = True
            return "break"
        return None

    def on_component_tree_release(self, event=None) -> str | None:
        if event is None:
            return None
        pressed_selection = self.component_press_selection
        if self.component_drag_active:
            self.component_drag_start_row = None
            self.component_drag_active = False
            self.component_press_selection = ()
            return "break"
        row_id = self.component_tree.identify_row(event.y)
        selection = self.component_tree.selection()
        self.component_drag_start_row = None
        self.component_press_selection = ()
        if not row_id:
            if selection:
                self.component_tree.selection_remove(selection)
                self.current_component_index = None
                self.clear_component_editor()
                return "break"
            return None
        if len(selection) == 1 and selection[0] == row_id and tuple(selection) == pressed_selection:
            self.component_tree.selection_remove(row_id)
            self.current_component_index = None
            self.clear_component_editor()
            return "break"
        return None

    def populate_component_editor(self, component: dict) -> None:
        kind, summary, state = self.describe_component(component)
        self.vars["component_kind"].set(kind)
        self.component_info_var.set(f"{summary} | {state}")

        if kind == "keyboard":
            key = component["keyboard"]
            hid = key.get("hidUsage", "")
            display = key.get("displayName") or KEYBOARD_USAGE_TO_NAME.get(hid, "")
            self.vars["component_key_name"].set(KEYBOARD_USAGE_TO_NAME.get(hid, display))
            self.vars["component_display_name"].set(display)
            self.vars["component_hid_usage"].set(str(hid))
            self.vars["component_is_down"].set(bool(key.get("isDown", False)))
            self.vars["component_delay"].set("")
            self.vars["component_mouse_usage"].set("")
        elif kind == "delay":
            self.vars["component_key_name"].set("")
            self.vars["component_display_name"].set("")
            self.vars["component_hid_usage"].set("")
            self.vars["component_is_down"].set(False)
            self.vars["component_delay"].set(str(component["delay"].get("durationMs", "")))
            self.vars["component_mouse_usage"].set("")
        elif kind == "mouse":
            button = component["mouse"].get("button", {})
            self.vars["component_key_name"].set("")
            self.vars["component_display_name"].set("")
            self.vars["component_hid_usage"].set("")
            self.vars["component_is_down"].set(bool(button.get("isDown", False)))
            self.vars["component_delay"].set("")
            self.vars["component_mouse_usage"].set(str(button.get("hidUsage", "")))
        else:
            self.clear_component_editor()

        self._toggle_component_editor_sections()

    def clear_component_editor(self) -> None:
        self.vars["component_kind"].set("")
        self.vars["component_key_name"].set("")
        self.vars["component_display_name"].set("")
        self.vars["component_hid_usage"].set("")
        self.vars["component_is_down"].set(False)
        self.vars["component_delay"].set("")
        self.vars["component_mouse_usage"].set("")
        self.component_info_var.set("")
        self._toggle_component_editor_sections()

    def _toggle_component_editor_sections(self) -> None:
        kind = self.vars["component_kind"].get()
        if kind == "keyboard":
            self.keyboard_editor.grid()
            self.delay_editor.grid_remove()
            self.mouse_editor.grid_remove()
        elif kind == "delay":
            self.keyboard_editor.grid_remove()
            self.delay_editor.grid()
            self.mouse_editor.grid_remove()
        elif kind == "mouse":
            self.keyboard_editor.grid_remove()
            self.delay_editor.grid_remove()
            self.mouse_editor.grid()
        else:
            self.keyboard_editor.grid_remove()
            self.delay_editor.grid_remove()
            self.mouse_editor.grid_remove()

    def on_known_key_selected(self, event=None) -> None:
        name = self.vars["component_key_name"].get().strip()
        usage = KEYBOARD_NAME_TO_USAGE.get(name.upper())
        if usage is None:
            return
        self.vars["component_display_name"].set(KEYBOARD_USAGE_TO_NAME.get(usage, name))
        self.vars["component_hid_usage"].set(str(usage))

    def on_keystroke_key_selected(self, event=None) -> None:
        name = self.vars["keystroke_key_name"].get().strip()
        usage = KEYBOARD_NAME_TO_USAGE.get(name.upper())
        if usage is not None:
            self.vars["keystroke_code"].set(str(usage))

    def apply_current_edits(self) -> bool:
        """Apply the top-level macro form fields back into the selected macro node."""
        record = self.current_record()
        if not record:
            return True
        node = record["node"]
        macro = node.get("macro", {})
        macro_type = macro.get("type")
        if macro_type == "SEQUENCE":
            default_delay = self._parse_int(self.vars["sequence_default_delay"].get(), "default delay")
            if default_delay is None:
                return False
        elif macro_type == "KEYSTROKE":
            code = self._parse_int(self.vars["keystroke_code"].get(), "keystroke code")
            if code is None:
                return False

        self._push_undo_state()
        node["name"] = self.vars["macro_name"].get().strip()
        if self.vars["action_name"].get().strip():
            macro["actionName"] = self.vars["action_name"].get().strip()
        elif "actionName" in macro:
            macro["actionName"] = self.vars["action_name"].get().strip()

        if macro_type == "SEQUENCE":
            sequence = macro.setdefault("sequence", {})
            sequence["defaultDelay"] = default_delay
            sequence["useDefaultDelay"] = bool(self.vars["sequence_use_default_delay"].get())
            sequence["useSimpleActions"] = bool(self.vars["sequence_use_simple_actions"].get())
            if self.vars["show_up_down"].get():
                sequence["showUpDown"] = True
            elif "showUpDown" in sequence:
                sequence.pop("showUpDown", None)
        elif macro_type == "KEYSTROKE":
            if not self._apply_keystroke_values(macro):
                return False

        record["name"] = node.get("name", "")
        self.mark_dirty()
        self.refresh_macro_list()
        self.populate_form(record)
        return True

    def reload_current(self) -> None:
        record = self.current_record()
        if record:
            self.populate_form(record)

    def update_component(self) -> None:
        """Write the component editor values back into the selected sequence component."""
        record = self.current_record()
        if not record or self.current_component_index is None:
            return
        components = self.get_components(record)
        if self.current_component_index >= len(components):
            return

        updated = self._build_component_from_editor()
        if updated is None:
            return

        self._push_undo_state()
        components[self.current_component_index] = updated
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)

    def _build_component_from_editor(self) -> dict | None:
        kind = self.vars["component_kind"].get().strip()
        if kind == "keyboard":
            hid = self._parse_int(self.vars["component_hid_usage"].get(), "keyboard hidUsage")
            if hid is None:
                return None
            display = self.vars["component_display_name"].get().strip() or KEYBOARD_USAGE_TO_NAME.get(hid, str(hid))
            keyboard = {"displayName": display, "hidUsage": hid}
            if self.vars["component_is_down"].get():
                keyboard["isDown"] = True
            return {"keyboard": keyboard}
        if kind == "delay":
            duration = self._parse_int(self.vars["component_delay"].get(), "delay duration")
            if duration is None:
                return None
            return {"delay": {"durationMs": duration}}
        if kind == "mouse":
            hid = self._parse_int(self.vars["component_mouse_usage"].get(), "mouse hidUsage")
            if hid is None:
                return None
            button = {"hidUsage": hid}
            if self.vars["component_is_down"].get():
                button["isDown"] = True
            return {"mouse": {"button": button}}
        messagebox.showwarning("No component type", "Select a component type first.")
        return None

    def add_keyboard_component(self) -> None:
        record = self.current_record()
        if not record:
            return
        components = self.get_components(record)
        new_component = {"keyboard": {"displayName": "A", "hidUsage": 4, "isDown": True}}
        insert_at = len(components)
        if self.current_component_index is not None:
            insert_at = self.current_component_index + 1
        self._push_undo_state()
        components.insert(insert_at, new_component)
        self.current_component_index = insert_at
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)

    def add_delay_component(self) -> None:
        record = self.current_record()
        if not record:
            return
        components = self.get_components(record)
        new_component = {"delay": {"durationMs": 50}}
        insert_at = len(components)
        if self.current_component_index is not None:
            insert_at = self.current_component_index + 1
        self._push_undo_state()
        components.insert(insert_at, new_component)
        self.current_component_index = insert_at
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)

    def delete_component(self) -> None:
        record = self.current_record()
        if not record or self.current_component_index is None:
            return
        components = self.get_components(record)
        if self.current_component_index >= len(components):
            return
        self._push_undo_state()
        components.pop(self.current_component_index)
        if components:
            self.current_component_index = min(self.current_component_index, len(components) - 1)
        else:
            self.current_component_index = None
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)

    def move_component(self, direction: int) -> None:
        record = self.current_record()
        if not record or self.current_component_index is None:
            return
        components = self.get_components(record)
        src = self.current_component_index
        dst = src + direction
        if src < 0 or src >= len(components) or dst < 0 or dst >= len(components):
            return
        self._move_component_to_index(src, dst, push_undo=True)

    def _move_component_to_index(self, source_index: int, target_index: int, push_undo: bool) -> bool:
        record = self.current_record()
        if not record:
            return False
        components = self.get_components(record)
        if (
            source_index < 0
            or source_index >= len(components)
            or target_index < 0
            or target_index >= len(components)
            or source_index == target_index
        ):
            return False
        if push_undo:
            self._push_undo_state()
        component = components.pop(source_index)
        components.insert(target_index, component)
        self.current_component_index = target_index
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)
        return True

    def copy_component(self) -> None:
        record = self.current_record()
        if not record or self.current_component_index is None:
            return
        components = self.get_components(record)
        if self.current_component_index >= len(components):
            return
        self.component_clipboard = copy.deepcopy(components[self.current_component_index])
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(json.dumps(self.component_clipboard, ensure_ascii=False))
        except Exception:
            pass
        self.component_info_var.set("Copied selected component")

    def paste_component_over_selection(self) -> None:
        record = self.current_record()
        if not record or self.current_component_index is None:
            return
        components = self.get_components(record)
        if self.current_component_index >= len(components):
            return
        component = None
        if self.component_clipboard is not None:
            component = copy.deepcopy(self.component_clipboard)
        else:
            try:
                clipboard_text = self.root.clipboard_get().strip()
                component = json.loads(clipboard_text)
            except Exception:
                component = None
        if not isinstance(component, dict):
            messagebox.showwarning(
                "Nothing to paste",
                "Copy a component first with Ctrl+C, then select another row and press Ctrl+V.",
            )
            return
        target_component = copy.deepcopy(components[self.current_component_index])
        if not self.vars["paste_include_state"].get():
            component = self._merge_component_identity(component, target_component)
        self._push_undo_state()
        components[self.current_component_index] = component
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)

    def _merge_component_identity(self, source: dict, target: dict) -> dict:
        if "keyboard" in source and "keyboard" in target:
            source_key = source["keyboard"]
            target_key = copy.deepcopy(target["keyboard"])
            target_key["hidUsage"] = source_key.get("hidUsage", target_key.get("hidUsage"))
            target_key["displayName"] = source_key.get(
                "displayName",
                KEYBOARD_USAGE_TO_NAME.get(target_key.get("hidUsage"), target_key.get("displayName", "")),
            )
            return {"keyboard": target_key}
        if "mouse" in source and "mouse" in target:
            source_button = source["mouse"].get("button", {})
            target_button = copy.deepcopy(target["mouse"].get("button", {}))
            target_button["hidUsage"] = source_button.get("hidUsage", target_button.get("hidUsage"))
            return {"mouse": {"button": target_button}}
        return source

    def start_keystroke_recording(self, mode: str) -> None:
        """Open the recorder window and capture live key presses into sequence components."""
        if not self.apply_current_edits():
            return
        record = self.current_record()
        if not record:
            return
        macro = record["node"].get("macro", {})
        if macro.get("type") != "SEQUENCE":
            messagebox.showinfo("Wrong macro type", "Recording is only available for SEQUENCE macros.")
            return
        if self.recording_window and self.recording_window.winfo_exists():
            self.recording_window.lift()
            return

        self.recording_mode = mode
        self.recorded_components = []
        self.record_last_event_time = None
        self.record_pressed_usages = set()

        win = tk.Toplevel(self.root)
        self.recording_window = win
        win.title("Record Keystrokes")
        win.geometry("560x180")
        win.transient(self.root)
        win.grab_set()
        win.columnconfigure(0, weight=1)

        ttk.Label(
            win,
            text="Type here to capture keystrokes. Escape finishes recording.",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        ttk.Label(
            win,
            text=f"Mode: {'replace sequence' if mode == 'replace' else 'append to sequence'}",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))
        info = tk.StringVar(value="Waiting for input...")
        ttk.Label(win, textvariable=info).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 6))
        capture = tk.Text(win, height=4, wrap="word")
        capture.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        capture.focus_set()
        capture.bind("<KeyPress>", lambda event: self._on_record_key_press(event, info))
        capture.bind("<KeyRelease>", lambda event: self._on_record_key_release(event, info))
        win.protocol("WM_DELETE_WINDOW", self.finish_keystroke_recording)

    def _record_delay_since_last_event(self) -> None:
        now = time.perf_counter()
        if self.record_last_event_time is None:
            self.record_last_event_time = now
            return
        if self.vars["sequence_use_default_delay"].get():
            elapsed_ms = self._current_sequence_default_delay()
        elif self.vars["record_use_actual_delay"].get():
            elapsed_ms = int(round((now - self.record_last_event_time) * 1000))
        else:
            elapsed_ms = self._current_sequence_default_delay()
        self.record_last_event_time = now
        if elapsed_ms > 0:
            self.recorded_components.append({"delay": {"durationMs": elapsed_ms}})

    def _current_sequence_default_delay(self) -> int:
        record = self.current_record()
        if not record:
            return 0
        sequence = record["node"].get("macro", {}).get("sequence", {})
        raw_value = self.vars["sequence_default_delay"].get().strip()
        if raw_value:
            try:
                return int(raw_value)
            except Exception:
                pass
        try:
            return int(sequence.get("defaultDelay", 0))
        except Exception:
            return 0

    def _keysym_to_usage(self, keysym: str) -> int | None:
        if not keysym:
            return None
        alias = {
            "control_l": "Ctrl",
            "control_r": "Right Ctrl",
            "shift_l": "Shift",
            "shift_r": "Right Shift",
            "alt_l": "Alt",
            "alt_r": "Right Alt",
            "win_l": "GUI",
            "win_r": "Right GUI",
            "super_l": "GUI",
            "super_r": "Right GUI",
            "return": "Enter",
            "escape": "Escape",
            "backspace": "Backspace",
            "space": "Space",
            "tab": "Tab",
            "prior": "Page Up",
            "next": "Page Down",
            "left": "Left",
            "right": "Right",
            "up": "Up",
            "down": "Down",
            "minus": "-",
            "equal": "=",
            "bracketleft": "[",
            "bracketright": "]",
            "backslash": "\\",
            "semicolon": ";",
            "apostrophe": "'",
            "grave": "`",
            "comma": ",",
            "period": ".",
            "slash": "/",
        }
        normalized = alias.get(keysym.lower(), keysym)
        return KEYBOARD_NAME_TO_USAGE.get(str(normalized).upper())

    def _on_record_key_press(self, event, info_var: tk.StringVar):
        if event.keysym == "Escape":
            self.finish_keystroke_recording()
            return "break"
        usage = self._keysym_to_usage(event.keysym)
        if usage is None or usage in self.record_pressed_usages:
            return None
        self._record_delay_since_last_event()
        self.record_pressed_usages.add(usage)
        self.recorded_components.append(
            {
                "keyboard": {
                    "displayName": KEYBOARD_USAGE_TO_NAME.get(usage, event.keysym),
                    "hidUsage": usage,
                    "isDown": True,
                }
            }
        )
        info_var.set(f"Recorded {len(self.recorded_components)} events")
        return "break"

    def _on_record_key_release(self, event, info_var: tk.StringVar):
        usage = self._keysym_to_usage(event.keysym)
        if usage is None or usage not in self.record_pressed_usages:
            return None
        self._record_delay_since_last_event()
        self.record_pressed_usages.discard(usage)
        self.recorded_components.append(
            {
                "keyboard": {
                    "displayName": KEYBOARD_USAGE_TO_NAME.get(usage, event.keysym),
                    "hidUsage": usage,
                }
            }
        )
        info_var.set(f"Recorded {len(self.recorded_components)} events")
        return "break"

    def finish_keystroke_recording(self) -> None:
        """Close the recorder window and insert the recorded components into the sequence."""
        win = self.recording_window
        self.recording_window = None
        if win and win.winfo_exists():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        if not self.recorded_components:
            return

        record = self.current_record()
        if not record:
            return
        components = self.get_components(record)
        self._push_undo_state()
        if self.recording_mode == "replace":
            components[:] = copy.deepcopy(self.recorded_components)
            self.current_component_index = 0 if components else None
        else:
            insert_at = len(components)
            if self.current_component_index is not None:
                insert_at = self.current_component_index + 1
            for offset, component in enumerate(self.recorded_components):
                components.insert(insert_at + offset, copy.deepcopy(component))
            self.current_component_index = insert_at if self.recorded_components else self.current_component_index
        self.mark_dirty()
        self.refresh_component_tree()
        self.populate_form(record)

    def update_keystroke_macro(self) -> None:
        """Apply the keystroke tab fields to the selected keystroke macro."""
        record = self.current_record()
        if not record:
            return
        macro = record["node"].get("macro", {})
        if macro.get("type") != "KEYSTROKE":
            messagebox.showinfo("Wrong macro type", "The selected macro is not a KEYSTROKE macro.")
            return
        self._push_undo_state()
        if not self._apply_keystroke_values(macro):
            return
        action_name = self.vars["keystroke_key_name"].get().strip()
        if action_name:
            macro["actionName"] = action_name
            self.vars["action_name"].set(action_name)
        self.mark_dirty()
        self.populate_form(record)

    def _apply_keystroke_values(self, macro: dict) -> bool:
        code = self._parse_int(self.vars["keystroke_code"].get(), "keystroke code")
        if code is None:
            return False
        keystroke = macro.setdefault("keystroke", {})
        keystroke["code"] = code
        modifiers = [usage for usage, var in self.keystroke_modifier_vars.items() if var.get()]
        if modifiers:
            keystroke["modifiers"] = sorted(modifiers)
        else:
            keystroke.pop("modifiers", None)
        return True

    def replace_key_in_scope(self, filtered_only: bool) -> None:
        """Replace one keyboard key name across the current macro or filtered macro set."""
        from_name = self.vars["replace_from"].get().strip()
        to_name = self.vars["replace_to"].get().strip()
        from_usage = KEYBOARD_NAME_TO_USAGE.get(from_name.upper())
        to_usage = KEYBOARD_NAME_TO_USAGE.get(to_name.upper())
        if from_usage is None or to_usage is None:
            messagebox.showwarning("Invalid key", "Choose valid From and To keys.")
            return

        targets = []
        if filtered_only:
            targets = [self.macro_records[index] for index in self.filtered_indices]
        else:
            record = self.current_record()
            if record:
                targets = [record]

        if not targets:
            return

        self._push_undo_state()
        replacements = 0
        target_display = KEYBOARD_USAGE_TO_NAME.get(to_usage, to_name)
        for record in targets:
            macro = record["node"].get("macro", {})
            if macro.get("type") != "SEQUENCE":
                continue
            for component in self.get_components(record):
                keyboard = component.get("keyboard")
                if not keyboard:
                    continue
                if keyboard.get("hidUsage") == from_usage:
                    keyboard["hidUsage"] = to_usage
                    keyboard["displayName"] = target_display
                    replacements += 1

        if replacements == 0:
            messagebox.showinfo("No matches", "No matching keyboard components were found in scope.")
            return

        self.mark_dirty()
        if self.current_record():
            self.populate_form(self.current_record())
        messagebox.showinfo(
            "Replacement complete",
            f"Updated {replacements} keyboard components from {from_name} to {to_name}.",
        )

    def set_all_delays_current(self) -> None:
        """Apply the entered delay value to every delay component in the current macro."""
        self.set_all_delays_in_scope(filtered_only=False)

    def set_sequence_default_delay(self) -> None:
        """Apply the entered delay value to the selected macro's sequence default delay."""
        self.set_sequence_default_delay_in_scope(filtered_only=False)

    def set_all_delays_in_scope(self, filtered_only: bool) -> None:
        """Apply one delay value to every delay component in the chosen macro scope."""
        duration = self._parse_int(self.vars["replace_delay"].get(), "delay duration")
        if duration is None:
            return
        if filtered_only:
            targets = [self.macro_records[index] for index in self.filtered_indices]
        else:
            record = self.current_record()
            targets = [record] if record else []
        if not targets:
            return

        self._push_undo_state()
        updated = 0
        affected_macros = 0
        for record in targets:
            macro = record["node"].get("macro", {})
            if macro.get("type") != "SEQUENCE":
                continue
            record_updates = 0
            for component in self.get_components(record):
                delay = component.get("delay")
                if delay is not None:
                    delay["durationMs"] = duration
                    updated += 1
                    record_updates += 1
            if record_updates:
                affected_macros += 1

        if not updated:
            messagebox.showinfo("No delays", "No delay components were found in scope.")
            return

        self.mark_dirty()
        current = self.current_record()
        if current:
            self.populate_form(current)
        scope_label = "filtered macros" if filtered_only else "current macro"
        messagebox.showinfo(
            "Delays updated",
            f"Updated {updated} delay components across {affected_macros} {scope_label}.",
        )

    def set_sequence_default_delay_in_scope(self, filtered_only: bool) -> None:
        """Apply one default delay value to the chosen macro scope."""
        record = self.current_record()
        duration = self._parse_int(self.vars["replace_delay"].get(), "default delay")
        if duration is None:
            return
        if filtered_only:
            targets = [self.macro_records[index] for index in self.filtered_indices]
        else:
            targets = [record] if record else []
        if not targets:
            return

        self._push_undo_state()
        updated = 0
        for target in targets:
            macro = target["node"].get("macro", {})
            if macro.get("type") != "SEQUENCE":
                continue
            macro.setdefault("sequence", {})["defaultDelay"] = duration
            updated += 1

        if not updated:
            messagebox.showinfo("Wrong macro type", "No SEQUENCE macros were found in scope.")
            return

        if record and record["node"].get("macro", {}).get("type") == "SEQUENCE":
            self.vars["sequence_default_delay"].set(str(duration))
        self.mark_dirty()
        if record:
            self.populate_form(record)
        scope_label = "filtered macros" if filtered_only else "current macro"
        messagebox.showinfo(
            "Default delay updated",
            f"Updated default delay for {updated} {scope_label}.",
        )

    def save_file(self) -> None:
        """Save back to the currently loaded source type."""
        if not self.apply_current_edits():
            return
        if self.source_kind == "settings_db":
            self.save_settings_db()
            return
        if not self.file_path:
            self.save_file_as()
            return
        self._save_json_to_path(self.file_path, update_status=True)

    def _save_json_to_path(self, path: Path, update_status: bool) -> bool:
        """Write the in-memory JSON data to disk and optionally refresh status text."""
        try:
            path.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not save file:\n{exc}")
            return False
        self.is_dirty = False
        if update_status:
            self.assignment_status_var.set(f"Saved {path}")
            self._update_status()
        return True

    def save_settings_db(self) -> None:
        """Write the in-memory data payload back into the loaded settings.db DATA row."""
        if not self.settings_db_path or self.settings_db_row_id is None:
            messagebox.showerror("Save failed", "No settings.db source is loaded.")
            return
        if not self._confirm_settings_db_write():
            return

        payload_text = json.dumps(self.data, indent=2, ensure_ascii=False)
        payload_bytes = payload_text.encode("utf-8")
        snapshot_label = f"GHub Macro Browser {time.strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            with sqlite3.connect(self.settings_db_path) as conn:
                conn.execute(
                    "INSERT INTO SNAPSHOTS (UUID, LABEL, FILE) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), snapshot_label, payload_bytes),
                )
                conn.execute(
                    "UPDATE DATA SET FILE = ?, _date_created = CURRENT_TIMESTAMP WHERE _id = ?",
                    (payload_bytes, self.settings_db_row_id),
                )
                conn.commit()
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not write settings.db:\n{exc}")
            return

        self.is_dirty = False
        self.assignment_status_var.set(f"Saved {self.settings_db_path}")
        self._update_status()

    def save_file_as(self) -> None:
        """Prompt for a new JSON file path and write the current data there."""
        path = filedialog.asksaveasfilename(
            title="Save G Hub JSON As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path(__file__).resolve().parent),
            initialfile=self.file_path.name if self.file_path else "ghub_edited.json",
        )
        if not path:
            return
        path_obj = Path(path)
        if self.source_kind == "json":
            self.file_path = path_obj
            self._save_json_to_path(path_obj, update_status=True)
            return
        if self._save_json_to_path(path_obj, update_status=False):
            self.assignment_status_var.set(f"Exported JSON to {path_obj}")
            self._update_status()

    def on_close(self) -> None:
        """Ask about unsaved changes before closing the application window."""
        if self.is_dirty:
            if not messagebox.askyesno("Unsaved changes", "Close without saving?"):
                return
        self.root.destroy()

    def _parse_int(self, value: str, label: str) -> int | None:
        try:
            return int(str(value).strip())
        except Exception:
            messagebox.showwarning("Invalid number", f"Enter a valid integer for {label}.")
            return None


def main() -> None:
    root = tk.Tk()
    app = GHubMacroBrowserApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
