import asyncio
import sys
from pathlib import Path

# Ensure backend directory is in python path
# Go up 3 levels from this script: src/scripts/solve_captcha.py -> backend/
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.browser import BrowserManager  # noqa: E402
from src.utils.config import get_settings  # noqa: E402

async def main():
    print("🚀 Starting Manual CAPTCHA Solver...")
    print("   This will open a browser window for you to solve CAPTCHAs.")
    print("   Cookies will be saved automatically for future scraper runs.\n")
    
    # Force headless=False for this session
    settings = get_settings()
    settings.browser.headless = False
    
    manager = BrowserManager()
    await manager.start()
    
    print("✅ Browser started!")
    
    # Open Google Jobs
    print("   Opening Google Jobs...")
    page1 = await manager.new_page()
    await page1.goto("https://www.google.com/search?q=software+engineer+jobs&ibp=htl;jobs", timeout=60000)
    
    # Open Glassdoor
    print("   Opening Glassdoor...")
    page2 = await manager.new_page()
    await page2.goto("https://www.glassdoor.com/Job/jobs.htm?sc.keyword=Software%20Engineer", timeout=60000)
    
    print("\n👉 ACTION REQUIRED:")
    print("1. Interact with the browser windows.")
    print("2. Solve any CAPTCHAs / Cloudflare challenges you see.")
    print("3. Log in if necessary.")
    print("4. Verify pages are loading job listings correctly.")
    print("\nWhen you are done, press ENTER in this terminal to save and exit.")
    
    input()
    
    print("\n💾 Saving session and closing...")
    await manager.stop()
    print("✅ Session saved! You can now run the scrapers.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
