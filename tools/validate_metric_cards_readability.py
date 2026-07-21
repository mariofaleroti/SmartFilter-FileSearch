from smart_filter.app_info import APP_VERSION
from pathlib import Path
root = Path(__file__).resolve().parents[1]
main_app = (root / "smart_filter" / "ui" / "main_app.py").read_text(encoding="utf-8")
app_info = (root / "smart_filter" / "app_info.py").read_text(encoding="utf-8")

def require(fragment: str, source: str, name: str) -> None:
    if fragment not in source:
        raise SystemExit(f"Missing fragment in {name}: {fragment}")

require('"title_font": ("small", "bold")', main_app, 'main_app.py')
require('"value_font": ("body", "bold")', main_app, 'main_app.py')
require('"title": tokens["text"]', main_app, 'main_app.py')
require('chip = ctk.CTkFrame(self.metrics_frame, corner_radius=9, height=60)', main_app, 'main_app.py')
require('chip.grid_propagate(False)', main_app, 'main_app.py')
require('title.configure(text_color=colors["title"]', main_app, 'main_app.py')
require(f'APP_VERSION = "{APP_VERSION}"', app_info, 'app_info.py')
print('OK - metric cards readability validated')
