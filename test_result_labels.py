"""Check result labels without importing Raspberry Pi or UI dependencies."""
import ast
from pathlib import Path
from types import SimpleNamespace

source = ast.parse(Path(__file__).with_name("ui.py").read_text(encoding="utf-8"))
app = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "App")
method = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == "_d_result")
assignment = next(node for node in ast.walk(method) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "clabel" for target in node.targets))
expression = compile(ast.Expression(assignment.value), "ui.py", "eval")
for mode, plant, expected in [
    ("hasil_panen", "padi", "malai terdeteksi"),
    ("hasil_panen", "edamame", "polong terdeteksi"),
    ("deteksi_hpt", "padi", "HPT terdeteksi"),
    ("deteksi_hpt", "edamame", "HPT terdeteksi"),
]:
    actual = eval(expression, {"self": SimpleNamespace(mode=mode, plant=plant)})
    assert actual == expected, (mode, plant, actual)
print("All four result labels passed.")
