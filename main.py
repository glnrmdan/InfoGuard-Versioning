import time
import schedule
import requests
import logging
from urllib3.exceptions import InsecureRequestWarning
from search_article import perform_search, process_and_replace_results
from email_parser import check_for_updates
from send_email import manage_and_send_results, send_confirmation_email, send_email

# Disable SSL verification warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_search_job(imap_server, imap_user, imap_pass, folder='INBOX'):
    global search_query, email_subject
    logging.info("Running update_search_job")
    try:
        new_query, new_subject = check_for_updates(imap_server, imap_user, imap_pass, folder)
        logging.info(f"Received new_query: {new_query}, new_subject: {new_subject}")
        if new_query is not None or new_subject is not None:
            if new_query is not None:
                search_query = new_query
                logging.info(f"Search query updated to: {search_query}")
            if new_subject is not None:
                email_subject = new_subject
                logging.info(f"Email subject updated to: {email_subject}")
            
            send_confirmation_email(to_email, new_query, new_subject, from_email, email_password)
            
            # Reschedule the search job with the new query
            schedule.clear('search_job')
            schedule.every(search_interval).minutes.do(search_job).tag('search_job')
            logging.info("Search job rescheduled with new parameters")
            
            # Trigger an immediate search with the new query
            search_job()
        else:
            logging.info("No updates found")
    except Exception as e:
        logging.error(f"Error in update_search_job: {str(e)}", exc_info=True)

def search_job():
    logging.info(f"Performing search for '{search_query}' at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        results = perform_search(search_query, total_result, use_serpapi)
        logging.info(f"Search completed. Found {len(results)} results.")
        if results:
            processed_results = process_and_replace_results(results, search_query, total_result, use_serpapi)
            logging.info(f"Processed results. {len(processed_results)} valid results after processing.")
            if processed_results:
                logging.info(f"Attempting to send email with {len(processed_results)} processed results")
                manage_and_send_results(processed_results, to_email, from_email, email_password, email_subject)
            else:
                logging.warning("No valid results to send after processing.")
        else:
            logging.warning("No results found in initial search.")
    except Exception as e:
        logging.error(f"Error in search_job: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # API configuration
    API_KEY = "AIzaSyCwWlf7Ka_BHc9fNElQtFoKRJUlDaV7O_o"
    SEARCH_ENGINE_ID = "70ff0242dca66436a"
    SERPAPI_KEY = "b397516f95f8e092c677d0b9e12d11a714a2849911a81d1197056366c1ead3cb"
    
    search_query = 'How to growth the selling'  # Initial search query
    email_subject = "Search Results Update"  # Initial email subject
    total_result = 5
    search_interval = 1  # Check every 1 minute
    use_serpapi = True

    to_email = "sakatareharya@gmail.com"
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

    # Schedule the search job
    schedule.every(search_interval).minutes.do(search_job).tag('search_job')
    
    # Schedule the update check job (check every 1 minute)
    schedule.every(1).minutes.do(update_search_job, imap_server, imap_user, imap_pass, imap_folder)

    logging.info("Checking for updates every 1 minute")
    
        # Test email send
    try:
        send_email("Test Email", "<p>This is a test email.</p>", to_email, from_email, email_password)
        logging.info("Test email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send test email: {str(e)}", exc_info=True)

    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

# def job(query, result_total, use_serpapi, to_email, from_email, password):
#     print(f"Performing search for '{query}' at {time.strftime('%Y-%m-%d %H:%M:%S')}")
#     items = perform_search(query, result_total, use_serpapi, extra_results=5)
#     if items:
#         results = process_and_replace_results(items, query, result_total, use_serpapi)
#         if results:
#             manage_and_send_results(results, to_email, from_email, password)
#         else:
#             print("No valid results to send.")
#     else:
#         print("No results found in initial search.")

# def setup_schedule(interval, query, result_total, use_serpapi, to_email, from_email, password):
#     if isinstance(interval, int):  # Minutes
#         schedule.every(interval).minutes.do(job, query, result_total, use_serpapi, to_email, from_email, password)
#     elif interval == 'hourly':
#         schedule.every().hour.do(job, query, result_total, use_serpapi, to_email, from_email, password)
#     elif interval == 'daily':
#         schedule.every().day.at("00:00").do(job, query, result_total, use_serpapi, to_email, from_email, password)
#     elif interval == 'weekly':
#         schedule.every().monday.at("00:00").do(job, query, result_total, use_serpapi, to_email, from_email, password)
#     else:
#         raise ValueError("Invalid interval. Use 'hourly', 'daily', 'weekly', or an integer for minutes.")

        
# if __name__ == "__main__":
#     # Just for developing only the API key is here
#     API_KEY = "AIzaSyCwWlf7Ka_BHc9fNElQtFoKRJUlDaV7O_o"
#     SEARCH_ENGINE_ID = "70ff0242dca66436a"
#     SERPAPI_KEY = "b397516f95f8e092c677d0b9e12d11a714a2849911a81d1197056366c1ead3cb"
    
#     search_query = 'Military Document'
#     total_result = 5
#     search_interval = 1  # 1 minute
#     use_serpapi = True
    
#     # Email configuration
    
#     to_email = "sakatareharya@gmail.com"
#     from_email = "glnrmdan@gmail.com"
#     password = "zuetpvehyfnlxfbh" 
    
#     setup_schedule(search_interval, search_query, total_result, use_serpapi, to_email, from_email, password)
    
#     print(f"Scheduled search for '{search_query}' every {search_interval} minute(s)")
#     try:
#         while True:
#             try:
#                 schedule.run_pending()
#                 time.sleep(1)
#             except Exception as e:
#                 print(f"An error occurred during scheduled run: {str(e)}")
#                 # Optionally, you could add a longer sleep here to avoid rapid retries in case of persistent errors
#                 time.sleep(60)
#     except KeyboardInterrupt:
#         print("Script interrupted by user. Exiting...")
    