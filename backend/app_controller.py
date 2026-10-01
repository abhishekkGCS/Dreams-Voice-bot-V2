# backend/app_controller.py
import subprocess
import pygetwindow as gw
import psutil
from typing import Optional, Dict

class AppController:
    """Unified controller for launching, focusing, and terminating desktop apps."""

    APP_REGISTRY: Dict[str, Dict[str, str]] = {
        "notepad": {"command": "notepad", "proc_name": "notepad.exe", "window_title": "Notepad"},
        "calculator": {"command": "calc", "proc_name": "CalculatorApp.exe", "window_title": "Calculator"},
        "spotify": {"command": "spotify", "proc_name": "Spotify.exe", "window_title": "Spotify"},
        "chrome": {"command": "chrome", "proc_name": "chrome.exe", "window_title": "Google Chrome"},
        "edge": {"command": "msedge", "proc_name": "msedge.exe", "window_title": "Edge"},
        "code": {"command": "code", "proc_name": "Code.exe", "window_title": "Visual Studio Code"},
        "terminal": {"command": "wt", "proc_name": "WindowsTerminal.exe", "window_title": "Terminal"},
        "cmd": {"command": "cmd", "proc_name": "cmd.exe", "window_title": "Command Prompt"},
    }

    ALIASES: Dict[str, str] = {
        "vs code": "code",
        "vscode": "code",
        "editor": "code",
        "browser": "chrome",
        "google": "chrome",
        "music": "spotify",
        "calc": "calculator",
        "notes": "notepad",
    }

    @classmethod
    def resolve_app(cls, name: str) -> Optional[Dict[str, str]]:
        clean = name.lower().strip()
        key = cls.ALIASES.get(clean, clean)
        return cls.APP_REGISTRY.get(key)

    @classmethod
    def find_open_window(cls, title_substring: str):
        for window in gw.getAllWindows():
            if window.title and title_substring.lower() in window.title.lower():
                return window
        return None

    @classmethod
    def launch_or_focus(cls, app_name: str) -> str:
        profile = cls.resolve_app(app_name)
        if not profile:
            try:
                subprocess.Popen(app_name, shell=True)
                return f"Launched {app_name}."
            except Exception as e:
                return f"Could not launch {app_name}: {e}"

        existing_window = cls.find_open_window(profile["window_title"])
        if existing_window:
            try:
                if existing_window.isMinimized:
                    existing_window.restore()
                existing_window.activate()
                return f"{app_name} is already open; brought to the foreground."
            except Exception:
                pass

        subprocess.Popen(profile["command"], shell=True)
        return f"Launched {app_name}."

    @classmethod
    def close_app(cls, app_name: str) -> str:
        profile = cls.resolve_app(app_name)
        target_name = profile["proc_name"].lower() if profile else f"{app_name.lower()}.exe"

        closed_any = False
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and target_name in proc.info["name"].lower():
                    proc.terminate()
                    closed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed_any:
            return f"Successfully closed {app_name}."
        return f"No running instance of {app_name} was found."