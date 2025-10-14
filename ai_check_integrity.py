import os
import re
import importlib.util
from dotenv import load_dotenv

print("🤖 Running AI Integrity Scan...\n")

# Load environment variables
load_dotenv()

required_files = [
    "main.py",
    "deploy_bot.py",
    "requirements.txt",
    ".env"
]

missing_files = [f for f in required_files if not os.path.exists(f)]

if missing_files:
    print("❌ Missing files:")
    for f in missing_files:
        print(f"  - {f}")
else:
    print("✅ All required files found.\n")

# Check environment variables
required_envs = ["BOT_TOKEN", "SAFE_ETH_WALLET", "SAFE_SOL_WALLET"]
missing_envs = [e for e in required_envs if not os.getenv(e)]

if missing_envs:
    print("⚠️ Missing environment variables:")
    for e in missing_envs:
        print(f"  - {e}")
else:
    print("✅ All key environment variables present.\n")

# Check imports inside Python files
def check_imports(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    imports = re.findall(r"import (\S+)", content)
    for lib in imports:
        lib_name = lib.split('.')[0]
        if importlib.util.find_spec(lib_name) is None:
            print(f"⚠️ Missing library: {lib_name}")
    return True

print("🔍 Checking imports...\n")
for f in ["main.py", "deploy_bot.py"]:
    if os.path.exists(f):
        check_imports(f)

print("\n✅ Scan complete! If no ❌ errors above, you’re ready for deployment.")
