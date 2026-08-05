from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


profile_dir_value = os.getenv("X_CHROME_PROFILE_DIR")
options = Options()
options.add_argument(f"--user-data-dir={PROFILE_DIR}")
options.add_argument("--profile-directory=Default")
options.add_argument("--start-maximized")
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")

driver = webdriver.Chrome(options=options)

try:
    print("Opening X...")
    driver.get("https://x.com/home")

    print("Current URL:", driver.current_url)
    input("Check that X is signed in, then press Enter to close...")
finally:
    driver.quit()
