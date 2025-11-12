from __future__ import annotations

import importlib
import pkgutil
import sys

print("Python:", sys.version)
print("sys.path[0]:", sys.path[0])
has_pkg = any(m.name == "sublease_matcher" for m in pkgutil.iter_modules())
print("has sublease_matcher on path:", has_pkg)
try:
    module = importlib.import_module("sublease_matcher.api.main")
    print("main module file:", getattr(module, "__file__", "<unknown>"))
    print("OK")
except Exception as exc:
    print("IMPORT ERROR:", repr(exc))
    sys.exit(1)
