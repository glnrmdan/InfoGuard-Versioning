from imap_tools import MailBox, AND, A
import logging
import re
from datetime import datetime, timezone

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def check_for_updates(imap_server, imap_user, imap_pass, folder='INBOX', users=None):
    """
    Monitors email inbox for user preference update requests.
    
    Checks for emails with subject 'Update News Preferences' and processes them
    to update user search queries and email subjects if requested.
    
    Args:
        imap_server (str): IMAP server address
        imap_user (str): Email username/address
        imap_pass (str): Email password
        folder (str, optional): IMAP folder to check. Defaults to 'INBOX'
        users (list, optional): List of User objects to check against
    
    Returns:
        tuple: (new_query, new_subject, user_email)
            - new_query (str or None): Updated search query if found
            - new_subject (str or None): Updated email subject if found
            - user_email (str or None): Email address of the user requesting update
    
    Raises:
        Exception: If there's an error accessing the mailbox or processing emails
    
    Note:
        - Only processes emails newer than the user's last news delivery
        - Marks processed emails as read
        - Ignores emails from unknown users
    """
    logging.debug(f"Checking for update emails in folder: {folder}")
    try:
        with MailBox(imap_server).login(imap_user, imap_pass, folder) as mailbox:
            logging.debug("Successfully logged into mailbox")
            logging.debug("Searching for emails with subject 'Update News Preferences'")
            messages = mailbox.fetch(AND(subject='Update News Preferences'), reverse=True)
            messages_list = list(messages)
            logging.debug(f"Found {len(messages_list)} matching messages")

            for msg in messages_list:
                user_email = msg.from_
                user = next((u for u in users if u.email == user_email), None)
                
                if user is None:
                    logging.debug(f"Email from unknown user: {user_email}")
                    continue

                msg_date = msg.date.replace(tzinfo=timezone.utc)  # Ensure timezone-aware
                user_last_news = user.last_news_sent.replace(tzinfo=timezone.utc)  # Ensure timezone-aware

                logging.debug(f"Processing email: {msg.subject}")
                logging.debug(f"Email date: {msg_date}")
                logging.debug(f"User's last news sent: {user_last_news}")

                if msg_date > user_last_news:
                    logging.debug(f"New update email from {user_email}")
                    
                    body = msg.text or msg.html
                    logging.debug(f"Email body: {body}")
                    
                    new_query, new_subject = parse_email_body(body)
                    
                    if new_query or new_subject:
                        # Mark the email as seen
                        mailbox.flag(msg.uid, '\Seen', True)
                        logging.debug("Email marked as read")
                        return new_query, new_subject, user_email
                else:
                    logging.debug(f"Skipping old update email from {user_email}")

    except Exception as e:
        logging.error(f"Error checking for updates: {str(e)}", exc_info=True)
    
    logging.debug("No valid update email found")
    return None, None, None

# This is need revision. Wait for the detail explanation about how user can change their preferences.
def parse_email_body(body):
    """
    Parses email body text to extract new query and subject preferences.
    
    Looks for specific patterns in the email body:
        - "New Query: <query text>"
        - "New Subject: <subject text>"
    
    Args:
        body (str): Email body text to parse
    
    Returns:
        tuple: (new_query, new_subject)
            - new_query (str or None): Updated search query if found
            - new_subject (str or None): Updated email subject if found
    
    Example:
        Email body:
            New Query: artificial intelligence news
            New Subject: AI Daily Update
        
        Returns:
            ("artificial intelligence news", "AI Daily Update")
    """
    new_query = None
    new_subject = None
    
    # Use regular expressions to find the new query and subject
    query_match = re.search(r'New Query:\s*(.+)', body, re.IGNORECASE | re.MULTILINE)
    subject_match = re.search(r'New Subject:\s*(.+)', body, re.IGNORECASE | re.MULTILINE)
    
    if query_match:
        new_query = query_match.group(1).strip()
        logging.debug(f"New query found: {new_query}")
    
    if subject_match:
        new_subject = subject_match.group(1).strip()
        logging.debug(f"New subject found: {new_subject}")
    
    return new_query, new_subject