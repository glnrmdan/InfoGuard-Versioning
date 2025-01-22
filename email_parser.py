from imap_tools import MailBox, AND, A
import logging
import re
from datetime import datetime, timezone

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# def check_for_updates(imap_server, imap_user, imap_pass, folder='INBOX', users=None):
#     logging.debug(f"Checking for update emails in folder: {folder}")
#     try:
#         # Login into sender email and check if there are any updates of user preferences in inbox
#         with MailBox(imap_server).login(imap_user, imap_pass, folder) as mailbox:
#             logging.debug("Successfully logged into mailbox")
#             logging.debug("Searching for emails with subject 'Update News Preferences'")
#             # The subject must be 'Update News Preferences'
#             messages = mailbox.fetch(AND(subject='Update News Preferences'), reverse=True)
#             messages_list = list(messages)
#             logging.debug(f"Found {len(messages_list)} matching messages")

#             for msg in messages_list:
#                 user_email = msg.from_
#                 # Check email matching between inbox and user email list
#                 user = next((u for u in users if u.email == user_email), None)
                
#                 if user is None:
#                     logging.debug(f"Email from unknown user: {user_email}")
#                     continue
                
#                 # Parse email date
#                 msg_date = msg.date.replace(tzinfo=None)  # Remove timezone info for comparison
#                 if msg_date <= user.last_news_sent:
#                     logging.debug(f"Skipping old update email from {user_email}")
#                     continue

#                 logging.debug(f"Processing email: {msg.subject}")
#                 logging.debug(f"Email date: {msg.date}")
                
#                 # Parse email body
#                 body = msg.text or msg.html
#                 logging.debug(f"Email body: {body}")
                
#                 # New Query and Subject is parsed by message on email body with "New Query:" and "New Subject:"
#                 new_query, new_subject = parse_email_body(body)
                
#                 # Check if there is any new query of new subject from user (any users)
#                 if new_query or new_subject:
#                     # Mark the email as seen
#                     mailbox.flag(msg.uid, '\Seen', True)
#                     logging.debug("Email marked as read")
#                     return new_query, new_subject, user_email

#     except Exception as e:
#         logging.error(f"Error checking for updates: {str(e)}", exc_info=True)
    
#     logging.debug("No valid update email found")
#     return None, None, None

def check_for_updates(imap_server, imap_user, imap_pass, folder='INBOX', users=None):
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

# def parse_email_body(body):
#     # Initialize new_query and new_subject
#     new_query = None
#     new_subject = None
    
#     # Use regular expressions to find the new query and subject
#     # The new query and subject is parsed by message on email body with "New Query:" and "New Subject:"
#     query_match = re.search(r'New Query:\s*(.+)', body, re.IGNORECASE | re.MULTILINE)
#     subject_match = re.search(r'New Subject:\s*(.+)', body, re.IGNORECASE | re.MULTILINE)
    
#     # Check if there is any new query of new subject from user
#     if query_match:
#         new_query = query_match.group(1).strip()
#         logging.debug(f"New query found: {new_query}")
    
#     if subject_match:
#         new_subject = subject_match.group(1).strip()
#         logging.debug(f"New subject found: {new_subject}")
    
#     return new_query, new_subject

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
    
    return new_query, new_subject