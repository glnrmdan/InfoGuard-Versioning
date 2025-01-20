import time
import schedule
import requests
import logging
import imaplib
from urllib3.exceptions import InsecureRequestWarning
from search_article import perform_search, process_and_replace_results
from email_parser import check_for_updates
from send_email import manage_and_send_results, send_confirmation_email

# Disable SSL verification warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def update_search_job(imap_server, imap_user, imap_pass):
    logging.debug("Running update_search_job")
    new_query, new_subject = check_for_updates(imap_server, imap_user, imap_pass)
    if new_query or new_subject:
        global search_query, email_subject
        send_confirmation_email(to_email, new_query, new_subject, from_email, email_password)
        if new_query:
            search_query = new_query
            logging.info(f"Search query updated to: {search_query}")
        if new_subject:
            email_subject = new_subject
            logging.info(f"Email subject updated to: {email_subject}")
        # Reschedule the search job with the new query
        schedule.clear('search_job')
        schedule.every(search_interval).minutes.do(search_job).tag('search_job')
        logging.info("Search job rescheduled with new parameters")
    else:
        logging.debug("No updates found")

def manual_imap_check(imap_server, imap_user, imap_pass, folder='INBOX'):
    logging.debug("Performing manual IMAP check")
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(imap_user, imap_pass)
    mail.select(folder)

    _, message_numbers = mail.search(None, 'ALL')
    logging.debug(f"All messages: {message_numbers}")

    _, recent_messages = mail.search(None, 'RECENT')
    logging.debug(f"Recent messages: {recent_messages}")

    _, unseen_messages = mail.search(None, 'UNSEEN')
    logging.debug(f"Unseen messages: {unseen_messages}")

    mail.close()
    mail.logout()

def search_job():
    print(f"Performing search for '{search_query}' at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    results = perform_search(search_query, total_result, use_serpapi)
    if results:
        manage_and_send_results(results, to_email, from_email, email_password, email_subject)
    else:
        print("No results to send.")

if __name__ == "__main__":
    # API configuration
    API_KEY = "YOUR_GOOGLE_API_KEY"
    SEARCH_ENGINE_ID = "YOUR_SEARCH_ENGINE_ID"
    SERPAPI_KEY = "YOUR_SERPAPI_KEY"
    
    search_query = 'Health Food'  # Initial search query
    email_subject = "Search Results Update"  # Initial email subject
    total_result = 5
    search_interval = 1  # Check every 60 minutes
    use_serpapi = True

    to_email = "sakatareharya@gmail.com"
    from_email = "glnrmdan@gmail.com"
    email_password = "zuetpvehyfnlxfbh" 

    # IMAP configuration for checking updates
    imap_server = "imap.gmail.com"
    imap_user = from_email
    imap_pass = email_password
    
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
    
    # Schedule the update check job (check every 15 minutes)
    imap_folder = 'INBOX'
    schedule.every(1).minutes.do(update_search_job, imap_server, imap_user, imap_pass,imap_folder)

    logging.info("Checking for updates every 1 minutes")
    
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
    