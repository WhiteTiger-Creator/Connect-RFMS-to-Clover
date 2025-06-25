import schedule
import time
from datetime import datetime
from app import main  # or from main import main

def run_main():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Running main() at {current_time}")
    main()

# Schedule it at 8:00 AM and 6:00 PM
schedule.every().day.at("03:00").do(run_main)
schedule.every().day.at("04:00").do(run_main)
schedule.every().day.at("05:00").do(run_main)
schedule.every().day.at("06:00").do(run_main)
schedule.every().day.at("07:00").do(run_main)
schedule.every().day.at("08:00").do(run_main)
schedule.every().day.at("09:00").do(run_main)
schedule.every().day.at("10:00").do(run_main)
schedule.every().day.at("11:00").do(run_main)
schedule.every().day.at("12:00").do(run_main)
schedule.every().day.at("13:00").do(run_main)
schedule.every().day.at("14:00").do(run_main)
schedule.every().day.at("15:38").do(run_main)
schedule.every().day.at("19:00").do(run_main)
schedule.every().day.at("20:00").do(run_main)

print("📅 Scheduler started. Waiting for scheduled tasks...")
while True:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Current time: {current_time}")
    schedule.run_pending()
    time.sleep(60)