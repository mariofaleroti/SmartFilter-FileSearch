from pathlib import Path
root = Path(__file__).resolve().parents[1]
helper = (root/'smart_filter'/'ui'/'window_icon.py').read_text(encoding='utf-8')
checks = {
    'icon file exists': (root/'assets'/'app_icon.ico').is_file(),
    'winfo_toplevel used': 'winfo_toplevel' in helper,
    'content frame scanned': 'content_frame' in helper,
    'children scanned': 'winfo_children' in helper,
    'direct iconbitmap used': 'iconbitmap(str(icon_path))' in helper,
    'delayed retry used': 'target.after(450' in helper,
}
for rel in [
    'smart_filter/ui/main_app.py',
    'smart_filter/ui/windows/about_window.py',
    'smart_filter/ui/windows/help_window.py',
    'smart_filter/ui/windows/category_window.py',
    'smart_filter/ui/windows/settings_window.py',
    'smart_filter/ui/windows/file_type_selection_window.py',
]:
    text = (root/rel).read_text(encoding='utf-8')
    checks[rel] = 'apply_window_icon_later(' in text
for rel in [
    'smart_filter/ui/windows/about_window.py',
    'smart_filter/ui/windows/help_window.py',
    'smart_filter/ui/windows/category_window.py',
    'smart_filter/ui/windows/settings_window.py',
    'smart_filter/ui/windows/file_type_selection_window.py',
]:
    text = (root/rel).read_text(encoding='utf-8')
    checks[rel + ' content_frame'] = 'apply_window_icon_later(' in text and 'content_frame' in text
missing = [name for name, ok in checks.items() if not ok]
if missing:
    raise SystemExit('Validation failed: ' + ', '.join(missing))
print('OK - secondary window icon fix reinforced')
