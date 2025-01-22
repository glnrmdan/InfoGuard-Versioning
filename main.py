import time
import schedule
import requests
import logging
from datetime import datetime, timedelta, timezone
from urllib3.exceptions import InsecureRequestWarning
from search_article import perform_search, process_and_replace_results
from email_parser import check_for_updates
from send_email import manage_and_send_results, send_confirmation_email
from user import User

# Configuration
API_KEY = "AIzaSyCwWlf7Ka_BHc9fNElQtFoKRJUlDaV7O_o"
SEARCH_ENGINE_ID = "70ff0242dca66436a"
SERPAPI_KEY = "b397516f95f8e092c677d0b9e12d11a714a2849911a81d1197056366c1ead3cb"

TOTAL_RESULT = 4
USE_SERPAPI = True

FROM_EMAIL = "testmail1122222@gmail.com"
EMAIL_PASSWORD = "xuouvmsncyasmxqa" 

# IMAP configuration for checking updates
IMAP_SERVER = "imap.gmail.com"
IMAP_FOLDER = 'INBOX'
IMAP_USER = FROM_EMAIL
IMAP_PASS = EMAIL_PASSWORD

# Disable SSL verification warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global list to store all users
users = [
    User("glnrmdan@gmail.com", "Technology trends", "Daily Tech Update", 4), # 4 minutes interval
    User("sakatareharya@gmail.com", "Financial news", "Daily Finance Roundup", 6) # 6 minutes interval
]

def update_search_job(imap_server, imap_user, imap_pass, folder='INBOX'):
    logging.info("Running update_search_job")
    try:
        new_query, new_subject, user_email = check_for_updates(imap_server, imap_user, imap_pass, folder, users)
        if new_query is not None or new_subject is not None:
            user = next((u for u in users if u.email == user_email), None)
            if user is None:
                logging.warning(f"Received update for unknown user: {user_email}. Ignoring.")
                return
            
            if new_query is not None:
                user.search_query = new_query
                logging.info(f"Search query updated for {user_email}: {user.search_query}")
            if new_subject is not None:
                user.email_subject = new_subject
                logging.info(f"Email subject updated for {user_email}: {user.email_subject}")
            
            send_confirmation_email(user.email, new_query, new_subject, FROM_EMAIL, EMAIL_PASSWORD)
            
            # Reset the next search time to now, so the new query will be used in the next search
            user.set_next_search_time(datetime.now(timezone.utc))
        else:
            logging.info("No updates found")
    except Exception as e:
        logging.error(f"Error in update_search_job: {str(e)}", exc_info=True)

def search_job():
    current_time = datetime.now(timezone.utc)
    for user in users:
        try:
            if user.is_ready_for_search():
                perform_search_for_user(user)
                user.set_next_search_time(current_time + timedelta(minutes=user.search_interval))
        except Exception as e:
            logging.error(f"Error in search_job for user {user.email}: {str(e)}", exc_info=True)

def perform_search_for_user(user):
    logging.info(f"Performing search for user {user.email} with query '{user.search_query}' at {datetime.now(timezone.utc)}")
    try:
        results = perform_search(user.search_query, TOTAL_RESULT, USE_SERPAPI)
        logging.info(f"Search completed for {user.email}. Found {len(results)} results.")
        if results:
            processed_results = process_and_replace_results(results, user.search_query, TOTAL_RESULT, USE_SERPAPI)
            logging.info(f"Processed results for {user.email}. {len(processed_results)} valid results after processing.")
            if processed_results:
                logging.info(f"Attempting to send email to {user.email} with {len(processed_results)} processed results")
                manage_and_send_results(processed_results, user, FROM_EMAIL, EMAIL_PASSWORD, user.email_subject)
                user.update_last_news_sent()
            else:
                logging.warning(f"No valid results to send after processing for {user.email}.")
        else:
            logging.warning(f"No results found in initial search for {user.email}.")
    except Exception as e:
        logging.error(f"Error in perform_search_for_user for {user.email}: {str(e)}", exc_info=True)
        
def main():
    logging.info("Starting the news update service")
    logging.info("Checking for preference updates every 1 minutes")
    
    # Schedule jobs to run every minute
    schedule.every(1).minutes.do(search_job) # seach every minutes to looks any updates (This may need optimization later)
    schedule.every(1).minutes.do(update_search_job, IMAP_SERVER, IMAP_USER, IMAP_PASS, IMAP_FOLDER) # check for update of user preferences 
    
    # Perform initial search for all users
    search_job()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting .... ")
    except Exception as e:
        logging.error(f"Error in main: {str(e)}", exc_info=True)
        time.sleep(60) # Wait for 60 seconds before continuing
        
if __name__ == "__main__":
    main()