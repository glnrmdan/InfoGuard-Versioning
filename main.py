import time
import schedule
import requests
import logging
from user import User
from urllib3.exceptions import InsecureRequestWarning
from search_article import perform_search, process_and_replace_results
from email_parser import check_for_updates
from send_email import manage_and_send_results, send_confirmation_email, send_email

# Disable SSL verification warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global list to store all users
users = [
    User("glnrmdan@gmail.com", "Technology trends", "Daily Tech Update"),
    User("sakatareharya@gmail.com", "Financial news", "Daily Finance Roundup")
]

def update_search_job(imap_server, imap_user, imap_pass, folder='INBOX'):
    logging.info("Running update_search_job")
    try:
        new_query, new_subject, user_email = check_for_updates(imap_server, imap_user, imap_pass, folder, users)
        logging.info(f"Received new_query: {new_query}, new_subject: {new_subject}, user_email: {user_email}")
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
            
            send_confirmation_email(user.email, new_query, new_subject, from_email, email_password)
            
            # Trigger an immediate search for the updated user
            search_job(user)
        else:
            logging.info("No updates found")
    except Exception as e:
        logging.error(f"Error in update_search_job: {str(e)}", exc_info=True)


def search_job(user=None):
    if user:
        perform_search_for_user(user)
    else:
        for user in users:
            perform_search_for_user(user)

def perform_search_for_user(user):
    logging.info(f"Performing search for user {user.email} with query '{user.search_query}' at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        results = perform_search(user.search_query, total_result, use_serpapi)
        logging.info(f"Search completed for {user.email}. Found {len(results)} results.")
        if results:
            processed_results = process_and_replace_results(results, user.search_query, total_result, use_serpapi)
            logging.info(f"Processed results for {user.email}. {len(processed_results)} valid results after processing.")
            if processed_results:
                logging.info(f"Attempting to send email to {user.email} with {len(processed_results)} processed results")
                manage_and_send_results(processed_results, user, from_email, email_password, user.email_subject)
            else:
                logging.warning(f"No valid results to send after processing for {user.email}.")
        else:
            logging.warning(f"No results found in initial search for {user.email}.")
    except Exception as e:
        logging.error(f"Error in search_job for {user.email}: {str(e)}", exc_info=True)


if __name__ == "__main__":
    # API configuration
    API_KEY = "AIzaSyCwWlf7Ka_BHc9fNElQtFoKRJUlDaV7O_o"
    SEARCH_ENGINE_ID = "70ff0242dca66436a"
    SERPAPI_KEY = "b397516f95f8e092c677d0b9e12d11a714a2849911a81d1197056366c1ead3cb"
    
    # search_query = 'How to growth the selling'  # Initial search query
    email_subject = "Search Results Update"  # Initial email subject
    total_result = 8
    search_interval = 2  # Check every 1 minute
    use_serpapi = True

    from_email = "testmail1122222@gmail.com"
    email_password = "xuouvmsncyasmxqa" 

    # IMAP configuration for checking updates
    imap_server = "imap.gmail.com"
    imap_user = from_email
    imap_pass = email_password
    imap_folder = 'INBOX'
    
    print("To update your news preferences, send an email to", from_email)
    print("Subject: Update News Preferences")
    print("Body:")
    print("New Query: Your desired search query")
    print("New Subject: Your desired email subject (optional)")

    logging.info(f"Initial search query: '{search_query}'")
    logging.info(f"Initial email subject: '{email_subject}'")
    logging.info(f"Scheduled search every {search_interval} minutes")

    # Schedule the search job for all users
    schedule.every(search_interval).minutes.do(search_job).tag('search_job')
    
    # Schedule the update check job (check every 15 minutes)
    schedule.every(1).minutes.do(update_search_job, imap_server, imap_user, imap_pass, imap_folder)

    logging.info("Starting the news update service")
    logging.info(f"Performing searches every {search_interval} minutes")
    logging.info("Checking for preference updates every 15 minutes")
    
    # Perform initial search for all users
    search_job()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
    
    # test email send
    # try:
    #     send_email("Test Email", "<p>This is a test email.</p>", to_email, from_email, email_password)
    #     logging.info("Test email sent successfully.")
    # except Exception as e:
    #     logging.error(f"Failed to send test email: {str(e)}", exc_info=True)