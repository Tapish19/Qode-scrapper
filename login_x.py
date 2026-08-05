import os
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

load_dotenv()

profile_dir_value = os.getenv("X_CHROME_PROFILE_DIR")
profile_name = os.getenv("X_CHROME_PROFILE_NAME", "Default")

if not profile_dir_value:
    raise RuntimeError(
        "X_CHROME_PROFILE_DIR is missing. Add it to your .env file."
    )

profile_dir = Path(profile_dir_value).expanduser().resolve()

options = Options()
options.add_argument(f"--user-data-dir={profile_dir}")
options.add_argument(f"--profile-directory={profile_name}")
options.add_argument("--start-maximized")
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")

driver = webdriver.Chrome(options=options)

try:
    print("Opening X...")
    driver.get("https://x.com/home")
    print("Current URL:", driver.current_url)
    input("Confirm that X is signed in, then press Enter to close...")
finally:
    driver.quit()
