import schedule
import time
from datetime import datetime
from app import main  # or from main import main

def run_main():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Running main() at {current_time}")
    main()

# Schedule it at 8:00 AM and 6:00 PM
schedule.every().day.at("06:00").do(run_main)
schedule.every().day.at("18:00").do(run_main)

print("📅 Scheduler started. Waiting for scheduled tasks...")
while True:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Current time: {current_time}")
    schedule.run_pending()
    time.sleep(60)