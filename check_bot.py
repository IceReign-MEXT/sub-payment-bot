import os

print("🔍 Checking required files...")

# Required files for deployment
required_files = [
    "main.py",
    "requirements.txt",
    "Procfile",
    ".gitignore",
]

# Optional files
optional_files = [
    ".env.example",
    "README.md",
    "License",
    "subscriptions.db",
]

# Check required files
all_good = True
for file in required_files:
    if os.path.isfile(file):
        print(f"✅ Found: {file}")
    else:
        print(f"❌ Missing: {file}")
        all_good = False

# Check .env locally
if os.path.isfile(".env"):
    print("✅ .env exists locally (good, do NOT push)")
else:
    print("⚠️ .env missing locally!")

# Check if .env is ignored
with open(".gitignore", "r") as f:
    gitignore = f.read()
if ".env" in gitignore:
    print("✅ .env is in .gitignore (safe to push)")
else:
    print("⚠️ .env is NOT in .gitignore! Add it to keep secrets safe.")

# Optional review
detected_files = [f for f in optional_files if os.path.isfile(f)]
if detected_files:
    print(f"⚠️ Other files detected (optional review): {detected_files}")

if all_good:
    print("\n🎯 All required files are present. Ready to push!")
else:
    print("\n❌ Missing required files. Fix before pushing!")
