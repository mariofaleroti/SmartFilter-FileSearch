from pathlib import Path
root = Path(__file__).resolve().parents[1]
main_app = (root/'smart_filter'/'ui'/'main_app.py').read_text(encoding='utf-8')
helper = (root/'smart_filter'/'ui'/'window_icon.py').read_text(encoding='utf-8')
checks = {
    'main_app apply icon': 'apply_window_icon_later(self.app.root)' in main_app,
    'helper exists': 'def apply_window_icon_later' in helper,
    'icon file exists': (root/'assets'/'app_icon.ico').is_file(),
}
for rel in ['smart_filter/ui/windows/about_window.py','smart_filter/ui/windows/help_window.py','smart_filter/ui/windows/category_window.py','smart_filter/ui/windows/settings_window.py','smart_filter/ui/windows/file_type_selection_window.py']:
    text = (root/rel).read_text(encoding='utf-8')
    checks[rel] = 'apply_window_icon_later(' in text
missing = [name for name, ok in checks.items() if not ok]
if missing:
    raise SystemExit('Validation failed: ' + ', '.join(missing))
print('OK - icon applied across all product windows')
