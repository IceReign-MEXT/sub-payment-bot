import os
import shutil
from datetime import datetime

# Current working directory
cwd = os.getcwd()

# Backup folder name with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_folder = os.path.join(cwd, f"backup_{timestamp}")

# Create backup folder
os.makedirs(backup_folder, exist_ok=True)

# List of files/folders to exclude from backup
exclude = [backup_folder, "__pycache__"]

# Move files/folders to backup folder
for item in os.listdir(cwd):
    if item in exclude:
        continue
    src = os.path.join(cwd, item)
    dst = os.path.join(backup_folder, item)
    shutil.move(src, dst)

print(f"✅ Backup completed! All files moved to: {backup_folder}")
