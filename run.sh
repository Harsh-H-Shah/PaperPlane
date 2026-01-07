#!/bin/bash
cd /home/harsh/Desktop/Projects/AutoApplier
source .venv/bin/activate

case "$1" in
    scrape)
        python main.py scrape --limit ${2:-50}
        ;;
    scheduler)
        python main.py scheduler start --interval ${2:-2}
        ;;
    dashboard)
        python main.py dashboard --port ${2:-8080}
        ;;
    stats)
        python main.py job-stats
        ;;
    jobs)
        python main.py jobs --limit ${2:-20}
        ;;
    all)
        # Run dashboard in background, then scheduler
        python main.py dashboard --port 8080 &
        sleep 2
        python main.py scheduler start --interval 2
        ;;
    *)
        echo "Usage: $0 {scrape|scheduler|dashboard|stats|jobs|all} [args]"
        echo ""
        echo "Commands:"
        echo "  scrape [limit]     - Scrape jobs once (default: 50)"
        echo "  scheduler [hours]  - Start scheduler (default: 2 hours)"
        echo "  dashboard [port]   - Start dashboard (default: 8080)"
        echo "  stats              - Show job statistics"
        echo "  jobs [limit]       - List jobs (default: 20)"
        echo "  all                - Start dashboard + scheduler"
        exit 1
        ;;
esac
