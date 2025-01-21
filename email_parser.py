from imap_tools import MailBox, AND
import logging
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def check_for_updates(imap_server, imap_user, imap_pass, folder='INBOX'):
    logging.debug(f"Checking for update emails in folder: {folder}")
    try:
        with MailBox(imap_server).login(imap_user, imap_pass, folder) as mailbox:
            logging.debug("Successfully logged into mailbox")
            logging.debug("Searching for emails with subject 'Update News Preferences'")
            messages = mailbox.fetch(AND(subject='Update News Preferences', seen=False), limit=1)
            messages_list = list(messages)
            logging.debug(f"Found {len(messages_list)} matching messages")

            for msg in messages_list:
                logging.debug(f"Processing email: {msg.subject}")
                
                body = msg.text or msg.html
                logging.debug(f"Email body: {body}")
                
                new_query, new_subject = parse_email_body(body)
                
                if new_query or new_subject:
                    # Mark the email as seen
                    mailbox.flag(msg.uid, '\Seen', True)
                    logging.debug("Email marked as read")
                    return new_query, new_subject

    except Exception as e:
        logging.error(f"Error checking for updates: {str(e)}")
    
    logging.debug("No valid update email found")
    return None, None

def parse_email_body(body):
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
    