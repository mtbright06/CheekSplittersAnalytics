import importlib
import platform
import sys

REQUIRED = [
    "bs4",
    "dotenv",
    "numpy",
    "pandas",
    "pybaseball",
    "requests",
    "scipy",
    "streamlit",
]

print("=" * 60)
print("SharpStack Environment Verification")
print("=" * 60)
print()

print(f"Python      : {platform.python_version()}")
print(f"Architecture: {platform.machine()}")
print(f"Executable  : {sys.executable}")
print()

failed = False

for package in REQUIRED:
    try:
        importlib.import_module(package)
        print(f"✅ {package}")
    except Exception:
        failed = True
        print(f"❌ {package}")

print()

if failed:
    print("Environment verification FAILED")
    sys.exit(1)

print("Environment Ready")