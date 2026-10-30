"""Open a tab in the regular Firefox session, without creating a dedicated window."""
import subprocess
import sys
import webbrowser


def open_tab(url: str) -> None:
    if sys.platform == "darwin":
        result = subprocess.run(["/usr/bin/open", "-a", "Firefox", url], capture_output=True)
        if result.returncode == 0:
            return
    webbrowser.open_new_tab(url)
