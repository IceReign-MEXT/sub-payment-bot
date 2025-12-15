import os

required_files = [
    "main.py",
    "requirements.txt",
    "Procfile",
    ".gitignore",
]

optional_files = [
    ".env.example",
    "README.md",
    "License",
    "subscriptions.db",
    "check_bot.py",
    "get_group_id.py",
]

print("🔍 Checking required files...")
all_found = True

for f in required_files:
    try:
        with open(f):
            print(f"✅ Found: {f}")
    except FileNotFoundError:
        print(f"❌ Missing: {f}")
        all_found = False

# Check .env presence
if os.path.exists(".env"):
    print("✅ .env exists locally (good, do NOT push)")
else:
    print("❌ .env not found. You need to create it from .env.example")
    all_found = False

# Check .env is in .gitignore
with open(".gitignore") as gi:
    gitignore_content = gi.read()
    if ".env" in gitignore_content:
        print("✅ .env is in .gitignore (safe to push)")
    else:
        print("⚠️ .env not in .gitignore (add it before pushing)")

# Optional files review
present_optional = [f for f in optional_files if os.path.exists(f)]
if present_optional:
    print(f"⚠️ Other files detected (optional review): {present_optional}")

if all_found:
    print("\n🎯 All required files are present. Ready to push!")
else:
    print("\n❌ Some required files are missing. Fix before pushing!")
