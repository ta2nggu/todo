"""
Cross-Platform Minimalist Keyboard-Driven Todo App
Supported on Windows & macOS.
Default: Light Theme.
"""

import os
import sys
import json
import platform
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

# Determine OS
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

# Data & Config Locations
DATA_DIR = Path.home() / ".flow_todo"
DATA_FILE = DATA_DIR / "tasks.json"
CONFIG_FILE = DATA_DIR / "config.json"

STARTUP_FOLDER_WIN = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
VBS_STARTUP_PATH = STARTUP_FOLDER_WIN / "TaskFlow.vbs"

# Theme Palettes (Default: Light)
THEMES = {
    "light": {
        "bg_main": "#F8FAFC",          # Soft clean modern canvas
        "bg_card": "#FFFFFF",          # Pure white container/cards
        "bg_hover": "#F0F7FF",         # Selected item soft sky-blue tint
        "bg_input": "#FFFFFF",         # Input box
        "border_color": "#E2E8F0",     # Very soft subtle border
        "border_selected": "#93C5FD",  # Soft blue selection outline
        "accent_blue": "#3B82F6",      # Vibrant indicator bar
        "text_primary": "#0F172A",     # Deep dark slate (crisp)
        "text_secondary": "#475569",   # Medium slate
        "text_muted": "#94A3B8",       # Placeholder & subtle helper text
        # Gradient endpoints for Urgency Fade-out
        "fg_active": (15, 23, 42),     # Dark slate for top urgent task
        "fg_faded": (148, 163, 184),   # Fades towards soft gray for lower tasks
        "fg_completed": (160, 174, 192),
        # D-Day Badges (Pastel pill style)
        "badge_overdue": {"bg": "#FEE2E2", "fg": "#DC2626"},  # Soft Red
        "badge_today": {"bg": "#FFEDD5", "fg": "#C2410C"},    # Soft Orange
        "badge_urgent": {"bg": "#FEF3C7", "fg": "#B45309"},   # Soft Amber (D-1 ~ D-3)
        "badge_normal": {"bg": "#E0F2FE", "fg": "#0284C7"},   # Soft Blue
        "badge_far": {"bg": "#F1F5F9", "fg": "#475569"},      # Soft Slate
        "badge_done": {"bg": "#F1F5F9", "fg": "#94A3B8"},     # Muted Completed
        # Buttons & Icons
        "btn_primary_bg": "#2563EB",
        "btn_primary_fg": "#FFFFFF",
        "btn_header_bg": "#FFFFFF",
        "btn_header_border": "#E2E8F0",
        "check_done": "#10B981",       # Emerald check
        "check_undone": "#CBD5E1",     # Soft circle
    },
    "dark": {
        "bg_main": "#181825",
        "bg_card": "#1E1E2E",
        "bg_hover": "#313244",
        "bg_input": "#252538",
        "border_color": "#45475A",
        "border_selected": "#89B4FA",
        "accent_blue": "#89B4FA",
        "text_primary": "#CDD6F4",
        "text_secondary": "#A6ADC8",
        "text_muted": "#6C7086",
        "fg_active": (245, 245, 250),
        "fg_faded": (88, 91, 112),
        "fg_completed": (70, 72, 88),
        "badge_overdue": {"bg": "#E78284", "fg": "#11111B"},
        "badge_today": {"bg": "#EF9F76", "fg": "#11111B"},
        "badge_urgent": {"bg": "#E5C890", "fg": "#11111B"},
        "badge_normal": {"bg": "#85C1DC", "fg": "#11111B"},
        "badge_far": {"bg": "#626880", "fg": "#C6D0F5"},
        "badge_done": {"bg": "#3B3D4F", "fg": "#737994"},
        "btn_primary_bg": "#89B4FA",
        "btn_primary_fg": "#11111B",
        "btn_header_bg": "#1E1E2E",
        "btn_header_border": "#45475A",
        "check_done": "#A6E3A1",
        "check_undone": "#6C7086",
    }
}


def interpolate_color(rgb1, rgb2, factor):
    """Linearly interpolates between two RGB tuples. factor: 0.0 -> rgb1, 1.0 -> rgb2."""
    r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * factor)
    g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * factor)
    b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hex_str):
    """Converts '#RRGGBB' to (R, G, B) integer tuple."""
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def parse_date_input(text):
    """
    Parses natural/shorthand date inputs:
    - 'today', '오늘', '0' -> today's date
    - 'tomorrow', '내일', '+1' -> tomorrow
    - '+N' (e.g. '+3', '+7') -> N days from today
    - 'MM-DD', 'MM/DD', 'M.D' -> current year-MM-DD
    - 'YYYY-MM-DD', 'YYYYMMDD' -> specific date
    Returns datetime.date or None.
    """
    if not text:
        return None
    s = text.strip().lower()
    today = datetime.date.today()

    if s in ("today", "오늘", "0", "0일", "당일"):
        return today
    if s in ("tomorrow", "내일", "1일", "+1"):
        return today + datetime.timedelta(days=1)
    if s.startswith("+") and s[1:].isdigit():
        return today + datetime.timedelta(days=int(s[1:]))
    if s.endswith("일") and s[:-1].isdigit():
        return today + datetime.timedelta(days=int(s[:-1]))

    # Try numeric YYYYMMDD
    if len(s) == 8 and s.isdigit():
        try:
            return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:]))
        except ValueError:
            pass

    # Try standard formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m-%d", "%m/%d", "%m.%d"):
        try:
            dt = datetime.datetime.strptime(s, fmt).date()
            if "%Y" not in fmt:
                dt = dt.replace(year=today.year)
                if (today - dt).days > 180:
                    dt = dt.replace(year=today.year + 1)
            return dt
        except ValueError:
            continue

    return None


def calculate_dday(target_date, is_dark=False):
    """
    Returns (diff_days, dday_label, badge_style_dict)
    Calculates dynamic pastel colors proportional to remaining days.
    """
    if target_date is None:
        bg = "#1E293B" if is_dark else "#F1F5F9"
        fg = "#94A3B8" if is_dark else "#64748B"
        return (9999, "기한없음", {"bg": bg, "fg": fg})

    today = datetime.date.today()
    diff = (target_date - today).days

    if not is_dark:
        # High-contrast, clean pastel badges for Light Theme
        if diff < 0:
            # Overdue (지남): Pastel Soft Red
            return (diff, f"D+{abs(diff)} (지남)", {"bg": "#FEE2E2", "fg": "#DC2626"})
        elif diff == 0:
            # D-Day (오늘): Pastel Warm Coral/Orange
            return (0, "D-Day", {"bg": "#FFEDD5", "fg": "#C2410C"})
        elif diff == 1:
            # D-1 (내일): Pastel Peach/Amber
            return (1, "D-1", {"bg": "#FEF3C7", "fg": "#D97706"})
        elif diff <= 3:
            # D-2 ~ D-3: Pastel Soft Warm Yellow
            return (diff, f"D-{diff}", {"bg": "#FEF9C3", "fg": "#A16207"})
        elif diff <= 7:
            # D-4 ~ D-7 (이번 주): Pastel Mint Green
            return (diff, f"D-{diff}", {"bg": "#DCFCE7", "fg": "#15803D"})
        elif diff <= 14:
            # D-8 ~ D-14 (다음 주): Pastel Sky Blue
            return (diff, f"D-{diff}", {"bg": "#E0F2FE", "fg": "#0369A1"})
        elif diff <= 30:
            # D-15 ~ D-30 (이번 달): Pastel Lavender
            return (diff, f"D-{diff}", {"bg": "#EDE9FE", "fg": "#6D28D9"})
        else:
            # D-31+: Pastel Slate Gray
            return (diff, f"D-{diff}", {"bg": "#F1F5F9", "fg": "#475569"})
    else:
        # Readable badges for Dark Theme
        if diff < 0:
            return (diff, f"D+{abs(diff)} (지남)", {"bg": "#450A0A", "fg": "#FCA5A5"})
        elif diff == 0:
            return (0, "D-Day", {"bg": "#431407", "fg": "#FDBA74"})
        elif diff == 1:
            return (1, "D-1", {"bg": "#451A03", "fg": "#FCD34D"})
        elif diff <= 3:
            return (diff, f"D-{diff}", {"bg": "#422006", "fg": "#FEF08A"})
        elif diff <= 7:
            return (diff, f"D-{diff}", {"bg": "#052E16", "fg": "#86EFAC"})
        elif diff <= 14:
            return (diff, f"D-{diff}", {"bg": "#082F49", "fg": "#7DD3FC"})
        elif diff <= 30:
            return (diff, f"D-{diff}", {"bg": "#2E1065", "fg": "#C4B5FD"})
        else:
            return (diff, f"D-{diff}", {"bg": "#1E293B", "fg": "#94A3B8"})


class TaskManager:
    """Handles task storage and sorting logic."""
    def __init__(self, filepath=DATA_FILE):
        self.filepath = filepath
        self.tasks = []
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    self.tasks = raw_data.get("tasks", [])
            except Exception as e:
                print(f"Error loading tasks: {e}")
                self.tasks = []
        else:
            # Starter sample tasks
            today = datetime.date.today()
            self.tasks = [
                {
                    "id": 1,
                    "title": "주간 업무 보고서 작성",
                    "due_date": today.strftime("%Y-%m-%d"),
                    "completed": False,
                    "created_at": datetime.datetime.now().isoformat(),
                },
                {
                    "id": 2,
                    "title": "클라이언트 피드백 검토 및 회의 준비",
                    "due_date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                    "completed": False,
                    "created_at": datetime.datetime.now().isoformat(),
                },
                {
                    "id": 3,
                    "title": "신규 프로젝트 기획안 초안 공유",
                    "due_date": (today + datetime.timedelta(days=4)).strftime("%Y-%m-%d"),
                    "completed": False,
                    "created_at": datetime.datetime.now().isoformat(),
                },
                {
                    "id": 4,
                    "title": "팀 개발 환경 라이브러리 업데이트",
                    "due_date": (today + datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
                    "completed": False,
                    "created_at": datetime.datetime.now().isoformat(),
                },
                {
                    "id": 5,
                    "title": "사내 보안 교육 이수하기",
                    "due_date": (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                    "completed": True,
                    "created_at": datetime.datetime.now().isoformat(),
                },
            ]
            self.save()

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump({"tasks": self.tasks}, f, ensure_ascii=False, indent=2)

    def add_task(self, title, due_date_str):
        new_id = max([t["id"] for t in self.tasks], default=0) + 1
        self.tasks.append({
            "id": new_id,
            "title": title.strip(),
            "due_date": due_date_str,
            "completed": False,
            "created_at": datetime.datetime.now().isoformat()
        })
        self.save()

    def toggle_completed(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                t["completed"] = not t["completed"]
                break
        self.save()

    def update_task(self, task_id, new_title, new_due_date):
        for t in self.tasks:
            if t["id"] == task_id:
                t["title"] = new_title.strip()
                t["due_date"] = new_due_date
                break
        self.save()

    def delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self.save()

    def get_sorted_tasks(self):
        """
        Sort order:
        1. Incomplete tasks first:
           - Nearest remaining days at the top (Overdue first, then D-Day, D-1, D-2...)
           - Tasks without date at the end of incomplete list
        2. Completed tasks at bottom
        """
        def sort_key(task):
            is_done = 1 if task["completed"] else 0
            d_str = task.get("due_date")
            if d_str:
                try:
                    dt = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                    diff = (dt - datetime.date.today()).days
                    has_date = 0
                except ValueError:
                    diff = 9999
                    has_date = 1
            else:
                diff = 9999
                has_date = 1
            return (is_done, has_date, diff)

        return sorted(self.tasks, key=sort_key)


class TodoApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("TaskFlow • 업무 Todo")
        self.minsize(420, 500)

        # Load Config (Default theme: light)
        self.config = self._load_config()
        self.theme_name = self.config.get("theme", "light")
        if self.theme_name not in THEMES:
            self.theme_name = "light"
        self.theme = THEMES[self.theme_name]

        self.always_on_top = self.config.get("always_on_top", True)
        saved_geometry = self.config.get("geometry", "520x680")
        try:
            self.geometry(saved_geometry)
        except Exception:
            self.geometry("520x680")

        self.configure(bg=self.theme["bg_main"])

        # OS Specific Modifiers
        self.mod_key = "⌘" if IS_MAC else "Ctrl"

        # Fonts
        family = "SF Pro Text" if IS_MAC else "Segoe UI"
        self.font_title = tkfont.Font(family=family, size=13, weight="bold")
        self.font_regular = tkfont.Font(family=family, size=10)
        self.font_btn = tkfont.Font(family=family, size=10, weight="bold")
        self.font_strike = tkfont.Font(family=family, size=10, overstrike=True)
        self.font_badge = tkfont.Font(family=family, size=8, weight="bold")
        self.font_check = tkfont.Font(family=family, size=12)
        self.font_sub = tkfont.Font(family=family, size=9)
        self.font_shortcut = tkfont.Font(family=family, size=8)

        # State
        self.manager = TaskManager()
        self.selected_index = 0
        self.display_items = []
        self.current_date = datetime.date.today()

        # Window attributes
        self.attributes("-topmost", self.always_on_top)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Build UI
        self._build_header()
        self._build_input_bar()
        self._build_list_view()
        self._build_footer()

        # Keyboard Bindings
        self._bind_shortcuts()

        # Initial Render
        self.refresh_list()

        # Periodic Date & D-Day check (for continuous running & auto midnight rollover)
        self._schedule_date_check()

    def _load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"always_on_top": True, "geometry": "520x680", "theme": "light"}

    def _save_config(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.config["geometry"] = self.winfo_geometry()
            self.config["always_on_top"] = self.always_on_top
            self.config["theme"] = self.theme_name
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _on_close(self):
        self._save_config()
        self.destroy()

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.theme = THEMES[self.theme_name]
        self._save_config()
        self._apply_theme()

    def _apply_theme(self):
        t = self.theme
        self.configure(bg=t["bg_main"])
        self.header_frame.configure(bg=t["bg_main"])
        self.left_frame.configure(bg=t["bg_main"])
        self.right_frame.configure(bg=t["bg_main"])
        self.title_lbl.configure(fg=t["text_primary"], bg=t["bg_main"])
        self.subtitle_lbl.configure(fg=t["text_secondary"], bg=t["bg_main"])

        # Header buttons
        theme_icon = "☀️ 라이트" if self.theme_name == "light" else "🌙 다크"
        self.theme_btn.configure(
            text=theme_icon,
            bg=t["btn_header_bg"],
            fg=t["text_primary"],
            activebackground=t["bg_hover"],
            highlightbackground=t["btn_header_border"]
        )
        self.pin_btn.configure(
            bg=t["btn_header_bg"],
            activebackground=t["bg_hover"],
            highlightbackground=t["btn_header_border"]
        )
        self._update_pin_btn()

        self.startup_btn.configure(
            bg=t["btn_header_bg"],
            activebackground=t["bg_hover"],
            highlightbackground=t["btn_header_border"]
        )
        self._update_startup_btn()

        # Input Bar
        self.input_container.configure(bg=t["bg_card"], highlightbackground=t["border_color"])
        self.entry_row.configure(bg=t["bg_card"])
        task_fg = t["text_muted"] if self.task_entry.get() == "새 할 일을 입력하세요..." else t["text_primary"]
        date_fg = t["text_muted"] if self.date_entry.get() == "마감일 (+3/오늘)" else t["text_primary"]
        self.task_entry.configure(
            bg=t["bg_input"],
            fg=task_fg,
            insertbackground=t["text_primary"],
            highlightbackground=t["border_color"],
            highlightcolor=t["border_selected"]
        )
        self.date_entry.configure(
            bg=t["bg_input"],
            fg=date_fg,
            insertbackground=t["text_primary"],
            highlightbackground=t["border_color"],
            highlightcolor=t["border_selected"]
        )
        self.add_btn.configure(bg=t["btn_primary_bg"], fg=t["btn_primary_fg"])

        # List & Canvas
        self.list_container.configure(bg=t["bg_main"])
        self.canvas.configure(bg=t["bg_main"])
        self.scrollable_frame.configure(bg=t["bg_main"])

        # Footer
        self.footer_frame.configure(bg=t["bg_main"])
        if hasattr(self, 'shortcut_lbl1'):
            self.shortcut_lbl1.configure(fg=t["text_secondary"], bg=t["bg_main"])
            self.shortcut_lbl2.configure(fg=t["text_muted"], bg=t["bg_main"])

        self.refresh_list()

    def _is_startup_enabled(self):
        if IS_WIN:
            return VBS_STARTUP_PATH.exists()
        return False

    def toggle_startup(self):
        if not IS_WIN:
            messagebox.showinfo(
                "Mac 시작프로그램 설정",
                "Mac에서는 [시스템 설정 > 일반 > 로그인 항목]에 run_todo.sh 또는 실행 스크립트를 등록하시면 부팅 시 자동 실행됩니다."
            )
            return

        if self._is_startup_enabled():
            try:
                if VBS_STARTUP_PATH.exists():
                    VBS_STARTUP_PATH.unlink()
                self._update_startup_btn()
                messagebox.showinfo("시작프로그램", "윈도우 시작프로그램에서 해제되었습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"설정 실패: {e}")
        else:
            try:
                STARTUP_FOLDER_WIN.mkdir(parents=True, exist_ok=True)
                python_exe = sys.executable
                pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
                if not Path(pythonw_exe).exists():
                    pythonw_exe = python_exe
                script_path = str(Path(__file__).resolve())

                vbs_content = (
                    f'Set WshShell = CreateObject("WScript.Shell")\r\n'
                    f'WshShell.Run """{pythonw_exe}"" ""{script_path}""", 0, False\r\n'
                )
                with open(VBS_STARTUP_PATH, "w", encoding="utf-8") as f:
                    f.write(vbs_content)
                self._update_startup_btn()
                messagebox.showinfo(
                    "시작프로그램 등록 완료",
                    "PC 부팅 시 백그라운드 콘솔 창 없이 TaskFlow가 자동으로 실행되도록 등록되었습니다!"
                )
            except Exception as e:
                messagebox.showerror("오류", f"등록 실패: {e}")

    def _update_startup_btn(self):
        t = self.theme
        if IS_WIN:
            if self._is_startup_enabled():
                self.startup_btn.config(text="🚀 자동시작: ON", fg=t["check_done"])
            else:
                self.startup_btn.config(text="🚀 자동시작: OFF", fg=t["text_muted"])
        else:
            self.startup_btn.config(text="🚀 자동시작", fg=t["text_muted"])

    def _update_pin_btn(self):
        t = self.theme
        if self.always_on_top:
            self.pin_btn.config(text="📌 고정 ON", fg=t["check_done"])
        else:
            self.pin_btn.config(text="📌 고정 OFF", fg=t["text_muted"])

    def toggle_pin(self):
        self.always_on_top = not self.always_on_top
        self.attributes("-topmost", self.always_on_top)
        self._update_pin_btn()
        self._save_config()

    def _build_header(self):
        t = self.theme
        self.header_frame = tk.Frame(self, bg=t["bg_main"], padx=16, pady=12)
        self.header_frame.pack(fill="x")

        # Title & Date
        today_str = datetime.date.today().strftime("%Y.%m.%d (%a)")
        self.left_frame = tk.Frame(self.header_frame, bg=t["bg_main"])
        self.left_frame.pack(side="left")

        self.title_lbl = tk.Label(
            self.left_frame, text="⚡ TaskFlow",
            font=self.font_title, fg=t["text_primary"], bg=t["bg_main"]
        )
        self.title_lbl.pack(anchor="w")

        self.subtitle_lbl = tk.Label(
            self.left_frame, text=f"{today_str}",
            font=self.font_sub, fg=t["text_secondary"], bg=t["bg_main"],
            cursor="hand2"
        )
        self.subtitle_lbl.pack(anchor="w")
        self.subtitle_lbl.bind("<Button-1>", lambda e: self._manual_refresh_date())

        # Top-right Controls: Theme, Pin & Startup
        self.right_frame = tk.Frame(self.header_frame, bg=t["bg_main"])
        self.right_frame.pack(side="right")

        self.pin_btn = tk.Button(
            self.right_frame,
            text="📌 고정 ON" if self.always_on_top else "📌 고정 OFF",
            font=self.font_sub,
            bg=t["btn_header_bg"],
            fg=t["check_done"] if self.always_on_top else t["text_muted"],
            activebackground=t["bg_hover"],
            bd=0,
            highlightthickness=1,
            highlightbackground=t["btn_header_border"],
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.toggle_pin
        )
        self.pin_btn.pack(side="right", padx=(4, 0))

        self.startup_btn = tk.Button(
            self.right_frame,
            text="🚀 자동시작",
            font=self.font_sub,
            bg=t["btn_header_bg"],
            fg=t["text_muted"],
            activebackground=t["bg_hover"],
            bd=0,
            highlightthickness=1,
            highlightbackground=t["btn_header_border"],
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.toggle_startup
        )
        self.startup_btn.pack(side="right", padx=4)
        self._update_startup_btn()

        theme_icon = "☀️ 라이트" if self.theme_name == "light" else "🌙 다크"
        self.theme_btn = tk.Button(
            self.right_frame,
            text=theme_icon,
            font=self.font_sub,
            bg=t["btn_header_bg"],
            fg=t["text_primary"],
            activebackground=t["bg_hover"],
            bd=0,
            highlightthickness=1,
            highlightbackground=t["btn_header_border"],
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.toggle_theme
        )
        self.theme_btn.pack(side="right", padx=4)

    def _build_input_bar(self):
        t = self.theme
        self.input_container = tk.Frame(
            self, bg=t["bg_card"], padx=14, pady=12,
            highlightthickness=1, highlightbackground=t["border_color"]
        )
        self.input_container.pack(fill="x", padx=16, pady=(0, 10))

        # Grid row for 100% unified vertical height across inputs & button
        self.entry_row = tk.Frame(self.input_container, bg=t["bg_card"])
        self.entry_row.pack(fill="x")
        self.entry_row.grid_columnconfigure(0, weight=1)
        self.entry_row.grid_rowconfigure(0, weight=1)

        self.task_entry = tk.Entry(
            self.entry_row,
            font=self.font_regular,
            bg=t["bg_input"],
            fg=t["text_muted"],
            insertbackground=t["text_primary"],
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=t["border_color"],
            highlightcolor=t["border_selected"]
        )
        self.task_entry.grid(row=0, column=0, sticky="nsew", padx=(0, 8), ipady=6)
        self.task_entry.insert(0, "새 할 일을 입력하세요...")
        self.task_entry.bind("<FocusIn>", self._clear_placeholder)
        self.task_entry.bind("<FocusOut>", self._restore_placeholder)

        # Date entry with width 14 and comfortable placeholder
        self.date_entry = tk.Entry(
            self.entry_row,
            width=14,
            font=self.font_regular,
            bg=t["bg_input"],
            fg=t["text_muted"],
            insertbackground=t["text_primary"],
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=t["border_color"],
            highlightcolor=t["border_selected"]
        )
        self.date_entry.grid(row=0, column=1, sticky="nsew", padx=(0, 8), ipady=6)
        self.date_entry.insert(0, "마감일 (+3/오늘)")
        self.date_entry.bind("<FocusIn>", self._clear_date_placeholder)
        self.date_entry.bind("<FocusOut>", self._restore_date_placeholder)

        # Quick Add Button (Flush with inputs via sticky nsew)
        self.add_btn = tk.Button(
            self.entry_row,
            text="+ 등록",
            font=self.font_btn,
            bg=t["btn_primary_bg"],
            fg=t["btn_primary_fg"],
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            bd=0,
            padx=14,
            cursor="hand2",
            command=self.add_task
        )
        self.add_btn.grid(row=0, column=2, sticky="nsew")

    def _build_list_view(self):
        t = self.theme
        self.list_container = tk.Frame(self, bg=t["bg_main"])
        self.list_container.pack(fill="both", expand=True, padx=16)

        self.canvas = tk.Canvas(
            self.list_container,
            bg=t["bg_main"],
            highlightthickness=0,
            bd=0
        )
        self.scrollbar = ttk.Scrollbar(
            self.list_container, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas, bg=t["bg_main"])

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)

        # Dynamic scroll configuration
        self.scrollable_frame.bind("<Configure>", lambda e: self._update_scroll_region())
        self.canvas.bind("<Configure>", lambda e: self._update_scroll_region())

        # Mousewheel binding
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _update_scroll_region(self, event=None):
        self.canvas.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        content_h = self.scrollable_frame.winfo_reqheight()

        if canvas_w > 1:
            self.canvas.itemconfig(self.canvas_window, width=canvas_w)

        # Only activate scroll if content exceeds canvas height
        if content_h <= canvas_h or canvas_h <= 1:
            self.canvas.configure(scrollregion=(0, 0, max(canvas_w, 1), max(canvas_h, 1)))
            self.canvas.yview_moveto(0.0)
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()
        else:
            self.canvas.configure(scrollregion=(0, 0, max(canvas_w, 1), content_h))
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        canvas_h = self.canvas.winfo_height()
        content_h = self.scrollable_frame.winfo_reqheight()
        # Strictly ignore mousewheel if content fits in the view
        if content_h <= canvas_h:
            self.canvas.yview_moveto(0.0)
            return

        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def _build_footer(self):
        t = self.theme
        self.footer_frame = tk.Frame(self, bg=t["bg_main"], padx=16, pady=10)
        self.footer_frame.pack(fill="x")

        line1 = "[Enter] 등록/선택     [Space] 완료(취소선)     [Del] 삭제     [F2] 수정"
        line2 = f"[↑ / ↓] 목록 이동     [{self.mod_key}+N] 새 할 일"

        self.shortcut_lbl1 = tk.Label(
            self.footer_frame,
            text=line1,
            font=self.font_shortcut,
            fg=t["text_secondary"],
            bg=t["bg_main"]
        )
        self.shortcut_lbl1.pack(anchor="center", pady=(0, 2))

        self.shortcut_lbl2 = tk.Label(
            self.footer_frame,
            text=line2,
            font=self.font_shortcut,
            fg=t["text_muted"],
            bg=t["bg_main"]
        )
        self.shortcut_lbl2.pack(anchor="center")

    def _bind_shortcuts(self):
        # Global hotkeys in window
        self.bind("<Up>", self._on_key_up)
        self.bind("<Down>", self._on_key_down)
        self.bind("<space>", self._on_key_space)
        self.bind("<Delete>", self._on_key_delete)
        if IS_MAC:
            self.bind("<BackSpace>", self._on_key_delete)
        self.bind("<F2>", self._on_key_edit)
        self.bind("<Escape>", self._on_key_escape)

        # Global key hook for reliable shortcuts across all Korean/English IME states
        self.bind_all("<Key>", self._on_global_key, add="+")

        # Direct root bindings (lowercase & uppercase)
        self.bind("<Control-n>", lambda e: self.focus_new_task())
        self.bind("<Control-N>", lambda e: self.focus_new_task())
        self.bind("<Command-n>", lambda e: self.focus_new_task())
        self.bind("<Command-N>", lambda e: self.focus_new_task())

        # When already typing in entry fields, consume Ctrl+N so it doesn't re-trigger focus_new_task
        self.task_entry.bind("<Control-n>", lambda e: "break")
        self.task_entry.bind("<Control-N>", lambda e: "break")
        self.task_entry.bind("<Command-n>", lambda e: "break")
        self.task_entry.bind("<Command-N>", lambda e: "break")
        self.date_entry.bind("<Control-n>", lambda e: "break")
        self.date_entry.bind("<Control-N>", lambda e: "break")
        self.date_entry.bind("<Command-n>", lambda e: "break")
        self.date_entry.bind("<Command-N>", lambda e: "break")

        # Window Pin, Theme, and Auto-start shortcuts have been removed per user request
        # (Top controls are available via header buttons to avoid typing interference)

        # Only on macOS map Command-Q to quit (Standard macOS convention)
        if IS_MAC:
            self.bind("<Command-q>", lambda e: self._on_close())
            self.bind("<Command-Q>", lambda e: self._on_close())

        # Inputs specific keys: Down / Esc / Tab to jump to list
        self.task_entry.bind("<Return>", lambda e: self.add_task())
        self.date_entry.bind("<Return>", lambda e: self.add_task())
        self.task_entry.bind("<Tab>", lambda e: self._on_task_entry_tab())
        self.date_entry.bind("<Tab>", lambda e: self._focus_list_from_input())
        self.date_entry.bind("<Shift-Tab>", lambda e: self._focus_task_entry_back())
        
        self.task_entry.bind("<Down>", self._focus_list_from_input)
        self.date_entry.bind("<Down>", self._focus_list_from_input)
        self.task_entry.bind("<Escape>", self._focus_list_from_input)
        self.date_entry.bind("<Escape>", self._focus_list_from_input)

        # Auto refresh date & D-Days when window gains focus (e.g. waking from sleep)
        self.bind("<FocusIn>", self._on_window_focus, add="+")

    def _schedule_date_check(self):
        """Periodically checks if the date has changed (e.g. past midnight) while running."""
        today = datetime.date.today()
        if today != self.current_date:
            self.current_date = today
            self.refresh_list()
        # Check every 30 seconds
        self.after(30000, self._schedule_date_check)

    def _on_window_focus(self, event=None):
        """Instantly updates date and D-Days when window gains focus or wakes from sleep."""
        today = datetime.date.today()
        if today != self.current_date:
            self.current_date = today
            self.refresh_list()

    def _manual_refresh_date(self):
        """Manual click refresh for the header date and D-Days."""
        self.current_date = datetime.date.today()
        self.refresh_list()

    def _on_global_key(self, event):
        # If user is currently typing in an entry box, NEVER intercept any key!
        current_focus = self.focus_get()
        if current_focus in (self.task_entry, self.date_entry):
            return

        is_ctrl = (event.state & 4 != 0) or (IS_MAC and (event.state & 8 != 0))
        if not is_ctrl:
            return

        k_sym = event.keysym.lower() if event.keysym else ""
        k_code = event.keycode

        # Keycode 78 = 'N', keysym 'n' / 'ㅜ' (Korean IME) -> Focus Input
        if k_code == 78 or k_sym in ("n", "ㅜ"):
            self.focus_new_task()
            return "break"

    def _on_task_entry_tab(self):
        self.date_entry.focus_set()
        self.date_entry.select_range(0, tk.END)
        return "break"

    def _focus_task_entry_back(self):
        self.task_entry.focus_set()
        self.task_entry.select_range(0, tk.END)
        return "break"

    def _focus_list_from_input(self, event=None):
        self.focus_set()
        if not self.task_entry.get().strip():
            self.task_entry.delete(0, tk.END)
            self.task_entry.insert(0, "새 할 일을 입력하세요...")
            self.task_entry.config(fg=self.theme["text_muted"])
        if not self.date_entry.get().strip():
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, "마감일 (+3/오늘)")
            self.date_entry.config(fg=self.theme["text_muted"])
        if self.display_items:
            self.refresh_list()
            self._ensure_selected_visible()
        return "break"

    # --- Placeholder Handlers ---
    def _clear_placeholder(self, event=None):
        t = self.theme
        if self.task_entry.get() == "새 할 일을 입력하세요...":
            self.task_entry.delete(0, tk.END)
            self.task_entry.config(fg=t["text_primary"])

    def _restore_placeholder(self, event=None):
        t = self.theme
        # Never restore placeholder if task_entry currently has keyboard focus!
        if self.focus_get() == self.task_entry:
            return
        if not self.task_entry.get().strip():
            self.task_entry.delete(0, tk.END)
            self.task_entry.insert(0, "새 할 일을 입력하세요...")
            self.task_entry.config(fg=t["text_muted"])

    def _clear_date_placeholder(self, event=None):
        t = self.theme
        if self.date_entry.get() == "마감일 (+3/오늘)":
            self.date_entry.delete(0, tk.END)
            self.date_entry.config(fg=t["text_primary"])

    def _restore_date_placeholder(self, event=None):
        t = self.theme
        # Never restore placeholder if date_entry currently has keyboard focus!
        if self.focus_get() == self.date_entry:
            return
        if not self.date_entry.get().strip():
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, "마감일 (+3/오늘)")
            self.date_entry.config(fg=t["text_muted"])

    def focus_new_task(self):
        t = self.theme
        if self.task_entry.get() == "새 할 일을 입력하세요...":
            self.task_entry.delete(0, tk.END)
        self.task_entry.config(fg=t["text_primary"])
        self.task_entry.focus_force()
        self.task_entry.selection_clear()
        self.task_entry.icursor(tk.END)

    def add_task(self):
        title = self.task_entry.get().strip()
        if not title or title == "새 할 일을 입력하세요...":
            self._focus_list_from_input()
            return

        date_text = self.date_entry.get().strip()
        if date_text == "마감일 (+3/오늘)":
            date_text = ""

        parsed_date = parse_date_input(date_text)
        date_str = parsed_date.strftime("%Y-%m-%d") if parsed_date else None

        self.manager.add_task(title, date_str)

        # Reset entries: keep task_entry ready for next input without placeholder!
        self.task_entry.delete(0, tk.END)
        self.task_entry.config(fg=self.theme["text_primary"])
        self.date_entry.delete(0, tk.END)
        self._restore_date_placeholder(None)
        self.task_entry.focus_set()

        self.selected_index = 0
        self.refresh_list()

    def refresh_list(self):
        t = self.theme
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.display_items = self.manager.get_sorted_tasks()
        total = len(self.display_items)
        if total == 0:
            empty_lbl = tk.Label(
                self.scrollable_frame,
                text="등록된 할 일이 없습니다.\n위 입력창에 마감일과 함께 작성해 보세요!",
                font=self.font_regular,
                fg=t["text_muted"],
                bg=t["bg_main"],
                pady=40
            )
            empty_lbl.pack(anchor="center")
            self._update_scroll_region()
            return

        # Ensure selected_index is within bounds
        if self.selected_index >= total:
            self.selected_index = max(0, total - 1)

        today_str = datetime.date.today().strftime("%Y.%m.%d (%a)")
        active_items = [item for item in self.display_items if not item["completed"]]
        active_count = len(active_items)
        self.subtitle_lbl.config(text=f"{today_str}  •  {active_count}개 남음")

        self.row_frames = []

        bg_card_rgb = hex_to_rgb(t["bg_card"])
        bg_main_rgb = hex_to_rgb(t["bg_main"])
        border_rgb = hex_to_rgb(t["border_color"])

        for idx, task in enumerate(self.display_items):
            is_done = task["completed"]
            is_selected = (idx == self.selected_index)

            d_str = task.get("due_date")
            target_date = None
            if d_str:
                try:
                    target_date = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            diff_days, dday_label, pastel_badge = calculate_dday(
                target_date, is_dark=(self.theme_name == "dark")
            )

            if not is_done:
                # Active (uncompleted) task: full crisp visibility (no gradient fade down the list)
                card_bg = t["bg_hover"] if is_selected else t["bg_card"]
                border_color = t["border_selected"] if is_selected else t["border_color"]
                text_fg = t["text_primary"]
                title_font = self.font_regular
                check_char = "○"
                check_fg = t["accent_blue"] if is_selected else t["check_undone"]
                badge_bg = pastel_badge["bg"]
                badge_fg = pastel_badge["fg"]
                date_fg = t["text_secondary"]
            else:
                # Completed task: faded out (흐릿하게) with strikethrough
                card_unselected_bg = interpolate_color(bg_card_rgb, bg_main_rgb, 0.85)
                card_unselected_border = interpolate_color(border_rgb, bg_main_rgb, 0.85)
                card_bg = t["bg_hover"] if is_selected else card_unselected_bg
                border_color = t["border_selected"] if is_selected else card_unselected_border
                text_fg = t.get("text_muted", "#94A3B8")
                date_fg = t.get("text_muted", "#94A3B8")
                title_font = self.font_strike
                check_char = "✔"
                check_fg = t["check_done"]
                badge_bg = t["badge_done"]["bg"]
                badge_fg = t["badge_done"]["fg"]

            row = tk.Frame(
                self.scrollable_frame,
                bg=card_bg,
                padx=8,
                pady=7,
                bd=0,
                highlightthickness=1,
                highlightbackground=border_color
            )
            row.pack(fill="x", pady=2)
            self.row_frames.append(row)

            # Left accent indicator bar (shows modern blue accent when selected)
            accent_color = t.get("accent_blue", "#3B82F6") if is_selected else card_bg
            accent_bar = tk.Frame(row, width=3, bg=accent_color)
            accent_bar.pack(side="left", fill="y", padx=(0, 6))

            # Left: Soft Circle Checkbox (○ vs ✔)
            check_lbl = tk.Label(
                row,
                text=check_char,
                font=self.font_check,
                fg=check_fg,
                bg=card_bg,
                cursor="hand2"
            )
            check_lbl.pack(side="left", padx=(0, 8))
            check_lbl.bind("<Button-1>", lambda e, tid=task["id"]: self._toggle_task(tid))

            # D-Day Badge (Soft pastel pill style)
            badge_lbl = tk.Label(
                row,
                text=f" {dday_label} ",
                font=self.font_badge,
                bg=badge_bg,
                fg=badge_fg,
                padx=6,
                pady=1
            )
            badge_lbl.pack(side="left", padx=(0, 8))

            # Task Title (Strikethrough & muted if completed)
            title_lbl = tk.Label(
                row,
                text=task["title"],
                font=title_font,
                fg=text_fg,
                bg=card_bg,
                anchor="w"
            )
            title_lbl.pack(side="left", fill="x", expand=True)

            # Right: Due date display
            date_display = d_str if d_str else "상시"
            date_lbl = tk.Label(
                row,
                text=date_display,
                font=self.font_sub,
                fg=date_fg,
                bg=card_bg
            )
            date_lbl.pack(side="right", padx=(4, 0))

            # Click row to select
            row.bind("<Button-1>", lambda e, i=idx: self._select_index(i))
            accent_bar.bind("<Button-1>", lambda e, i=idx: self._select_index(i))
            title_lbl.bind("<Button-1>", lambda e, i=idx: self._select_index(i))
            badge_lbl.bind("<Button-1>", lambda e, i=idx: self._select_index(i))
            date_lbl.bind("<Button-1>", lambda e, i=idx: self._select_index(i))

            # Double-click to edit
            row.bind("<Double-Button-1>", lambda e, t_item=task: self._open_edit_dialog(t_item))
            title_lbl.bind("<Double-Button-1>", lambda e, t_item=task: self._open_edit_dialog(t_item))

        self._update_scroll_region()

    def _select_index(self, index):
        self.selected_index = index
        self.refresh_list()

    def _toggle_task(self, task_id):
        self.manager.toggle_completed(task_id)
        self.refresh_list()

    # --- Keyboard Navigation ---
    def _on_key_up(self, event):
        if self.display_items and self.selected_index > 0:
            self.selected_index -= 1
            self.refresh_list()
            self._ensure_selected_visible()

    def _on_key_down(self, event):
        if self.display_items and self.selected_index < len(self.display_items) - 1:
            self.selected_index += 1
            self.refresh_list()
            self._ensure_selected_visible()

    def _on_key_space(self, event):
        if self.focus_get() in (self.task_entry, self.date_entry):
            return
        if self.display_items and 0 <= self.selected_index < len(self.display_items):
            current_task = self.display_items[self.selected_index]
            self._toggle_task(current_task["id"])

    def _on_key_delete(self, event=None):
        if self.focus_get() in (self.task_entry, self.date_entry):
            return
        if self.display_items and 0 <= self.selected_index < len(self.display_items):
            current_task = self.display_items[self.selected_index]
            self._confirm_delete_dialog(current_task)

    def _confirm_delete_dialog(self, task):
        t = self.theme
        dialog = tk.Toplevel(self)
        dialog.title("삭제 확인")
        dialog.geometry("380x180")
        dialog.configure(bg=t["bg_card"])
        dialog.transient(self)
        dialog.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - 190
        y = self.winfo_y() + (self.winfo_height() // 2) - 90
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog,
            text="선택한 할 일을 삭제하시겠습니까?",
            font=self.font_title,
            fg=t["text_primary"],
            bg=t["bg_card"]
        ).pack(pady=(20, 6))

        title_preview = task["title"]
        if len(title_preview) > 30:
            title_preview = title_preview[:27] + "..."

        tk.Label(
            dialog,
            text=f"\"{title_preview}\"",
            font=self.font_regular,
            fg=t["text_secondary"],
            bg=t["bg_card"]
        ).pack(pady=(0, 16))

        btn_frame = tk.Frame(dialog, bg=t["bg_card"])
        btn_frame.pack(pady=(0, 10))

        active_btn = [0]  # 0 for Yes, 1 for No

        def do_delete():
            self.manager.delete_task(task["id"])
            if self.selected_index >= len(self.display_items) - 1:
                self.selected_index = max(0, len(self.display_items) - 2)
            self.refresh_list()
            dialog.destroy()
            self._focus_list_from_input()

        def do_cancel():
            dialog.destroy()
            self._focus_list_from_input()

        yes_btn = tk.Button(
            btn_frame,
            text="  예 (Y / Enter)  ",
            font=self.font_badge,
            bg="#DC2626",
            fg="#FFFFFF",
            activebackground="#B91C1C",
            activeforeground="#FFFFFF",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=do_delete
        )
        yes_btn.pack(side="left", padx=8)

        no_btn = tk.Button(
            btn_frame,
            text="  아니오 (N / Esc)  ",
            font=self.font_badge,
            bg=t["bg_main"],
            fg=t["text_secondary"],
            activebackground=t["bg_hover"],
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=do_cancel
        )
        no_btn.pack(side="left", padx=8)

        def update_focus():
            if active_btn[0] == 0:
                yes_btn.config(highlightthickness=2, highlightbackground="#B91C1C", highlightcolor="#B91C1C")
                no_btn.config(highlightthickness=1, highlightbackground=t["border_color"], highlightcolor=t["border_color"])
                yes_btn.focus_set()
            else:
                yes_btn.config(highlightthickness=0, highlightbackground=t["border_color"], highlightcolor=t["border_color"])
                no_btn.config(highlightthickness=2, highlightbackground="#3B82F6", highlightcolor="#3B82F6")
                no_btn.focus_set()

        def on_dialog_key(event):
            k_code = event.keycode
            k_sym = event.keysym.lower() if event.keysym else ""
            k_char = getattr(event, "char", "").lower()

            # Yes shortcut: Y / y / Korean ㅛ / keycode 89
            if k_code == 89 or k_sym in ("y", "ㅛ") or k_char in ("y", "ㅛ"):
                do_delete()
                return "break"
            # No shortcut: N / n / Korean ㅜ / keycode 78
            elif k_code == 78 or k_sym in ("n", "ㅜ") or k_char in ("n", "ㅜ"):
                do_cancel()
                return "break"
            elif event.keysym == "Escape":
                do_cancel()
                return "break"
            # Enter: trigger currently active choice
            elif event.keysym in ("Return", "KP_Enter"):
                if active_btn[0] == 0:
                    do_delete()
                else:
                    do_cancel()
                return "break"
            # Arrow Left / Right / Tab to toggle active button
            elif event.keysym in ("Left", "Right", "Tab", "Up", "Down"):
                active_btn[0] = 1 - active_btn[0]
                update_focus()
                return "break"
            elif event.keysym == "space":
                if active_btn[0] == 0:
                    do_delete()
                else:
                    do_cancel()
                return "break"

        dialog.bind("<Key>", on_dialog_key)
        update_focus()

    def _on_key_edit(self, event):
        if self.display_items and 0 <= self.selected_index < len(self.display_items):
            self._open_edit_dialog(self.display_items[self.selected_index])

    def _on_key_escape(self, event):
        self._focus_list_from_input()

    def _ensure_selected_visible(self):
        canvas_h = self.canvas.winfo_height()
        content_h = self.scrollable_frame.winfo_reqheight()
        if content_h <= canvas_h or canvas_h <= 1:
            self.canvas.yview_moveto(0.0)
            return

        if not self.row_frames or self.selected_index >= len(self.row_frames):
            return

        self.canvas.update_idletasks()
        row = self.row_frames[self.selected_index]
        row_y = row.winfo_y()
        row_h = row.winfo_height()

        y1, y2 = self.canvas.yview()
        vis_top = y1 * content_h
        vis_bottom = y2 * content_h

        if row_y < vis_top:
            self.canvas.yview_moveto(max(0.0, row_y / content_h))
        elif row_y + row_h > vis_bottom:
            target = (row_y + row_h - canvas_h) / content_h
            self.canvas.yview_moveto(min(1.0, max(0.0, target)))

    def _open_edit_dialog(self, task):
        t = self.theme
        dialog = tk.Toplevel(self)
        dialog.title("할 일 수정")
        dialog.geometry("380x210")
        dialog.configure(bg=t["bg_card"])
        dialog.transient(self)
        dialog.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - 190
        y = self.winfo_y() + (self.winfo_height() // 2) - 105
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text="내용 수정", font=self.font_badge, fg=t["text_primary"], bg=t["bg_card"]).pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        edit_title = tk.Entry(
            dialog,
            font=self.font_regular,
            bg=t["bg_input"],
            fg=t["text_primary"],
            insertbackground=t["text_primary"],
            bd=0,
            highlightthickness=1,
            highlightbackground=t["border_color"]
        )
        edit_title.pack(fill="x", padx=16, ipady=4)
        edit_title.insert(0, task["title"])

        tk.Label(dialog, text="마감일 (YYYY-MM-DD / 오늘 / +3)", font=self.font_badge, fg=t["text_primary"], bg=t["bg_card"]).pack(
            anchor="w", padx=16, pady=(10, 4)
        )
        edit_date = tk.Entry(
            dialog,
            font=self.font_regular,
            bg=t["bg_input"],
            fg=t["text_primary"],
            insertbackground=t["text_primary"],
            bd=0,
            highlightthickness=1,
            highlightbackground=t["border_color"]
        )
        edit_date.pack(fill="x", padx=16, ipady=4)
        edit_date.insert(0, task.get("due_date") or "")

        btn_row = tk.Frame(dialog, bg=t["bg_card"])
        btn_row.pack(fill="x", padx=16, pady=16)

        def save_and_close():
            new_title = edit_title.get().strip()
            if new_title:
                d_val = edit_date.get().strip()
                p_date = parse_date_input(d_val)
                new_due = p_date.strftime("%Y-%m-%d") if p_date else (d_val if d_val else None)
                self.manager.update_task(task["id"], new_title, new_due)
                self.refresh_list()
            dialog.destroy()

        save_btn = tk.Button(
            btn_row,
            text="저장 (Enter)",
            font=self.font_badge,
            bg=t["btn_primary_bg"],
            fg=t["btn_primary_fg"],
            bd=0,
            padx=12,
            pady=4,
            command=save_and_close
        )
        save_btn.pack(side="right", padx=(8, 0))

        cancel_btn = tk.Button(
            btn_row,
            text="취소 (Esc)",
            font=self.font_badge,
            bg=t["bg_main"],
            fg=t["text_secondary"],
            bd=0,
            padx=12,
            pady=4,
            command=dialog.destroy
        )
        cancel_btn.pack(side="right")

        dialog.bind("<Return>", lambda e: save_and_close())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        edit_title.focus_set()


if __name__ == "__main__":
    app = TodoApp()
    app.mainloop()
