import asyncio
import sys
import os
from src.scrapers.aggregator import JobAggregator

# Sources to test
SOURCES = [
    "simplify", 
    "cvrve", 
    "linkedin", 
    "jobright", 
    "dice", 
    "builtin"
]

async def test_scraper(source):
    print(f"\nTesting {source.upper()}...")
    agg = JobAggregator(validate_links=True) # Turn on validation to be realistic
    
    try:
        # High limit to ensure we fetch enough to find new ones
        limit = 20 
        print(f"  Scraping up to {limit} jobs...")
        
        # Get specific scraper to test raw output
        scraper_map = {
            "simplify": agg.scrapers[0], # Assuming order based on aggregator init, risky but let's try mapping manually if needed
            "cvrve": agg.scrapers[1],
            "linkedin": agg.scrapers[2],
            "jobright": agg.scrapers[3],
            "dice": agg.scrapers[4],
            "builtin": agg.scrapers[5] if len(agg.scrapers) > 5 else None
        }
        
        # Better approach: find scraper by source name
        target_scraper = next((s for s in agg.scrapers if s.SOURCE_NAME.lower() == source), None)
        
        if target_scraper:
            print(f"  🔍 Direct scrape from {target_scraper.SOURCE_NAME}...")
            raw = await target_scraper.scrape(limit=limit)
            print(f"  📊 Raw yielded: {len(raw)}")
        
        jobs = await agg.scrape_source(source, limit=limit)
        
        print(f"  ✅ Finished {source}")
        print(f"  Found: {len(jobs)} (after validation & deduplication)")
        
        if len(jobs) > 0:
            print(f"  Sample: {jobs[0].title} @ {jobs[0].company}")
            print(f"  URL: {jobs[0].url}")
        else:
            print("  ⚠️ No new jobs found (might contain only existing or failed to parse)")

    except Exception as e:
        print(f"  ❌ Failed: {e}")

async def main():
    print("🚀 Starting individual scraper tests...")
    
    for source in SOURCES:
        await test_scraper(source)
    
    print("\n🏁 All tests complete.")

if __name__ == "__main__":
    # Ensure we can import src
    sys.path.append(os.getcwd())
    asyncio.run(main())
