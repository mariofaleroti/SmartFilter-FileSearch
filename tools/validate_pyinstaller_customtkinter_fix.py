from pathlib import Path
root = Path(__file__).resolve().parents[1]
for spec_name in ["SmartFilter.spec", "SmartFilterCLI.spec"]:
    text = (root / spec_name).read_text(encoding="utf-8")
    assert "collect_all" in text, f"{spec_name}: missing collect_all"
    assert 'collect_all("customtkinter")' in text, f"{spec_name}: missing customtkinter collection"
    assert '"customtkinter"' in text, f"{spec_name}: missing customtkinter hidden import"
    assert "datas=ctk_datas" in text, f"{spec_name}: datas not wired"
    assert "binaries=ctk_binaries" in text, f"{spec_name}: binaries not wired"
print("OK - PyInstaller specs include CustomTkinter explicitly")
