import imaplib
import email
from email.header import decode_header
import re
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def decode_subject(subject):
    decoded_subject, encoding = decode_header(subject)[0]
    if isinstance(decoded_subject, bytes):
        return decoded_subject.decode(encoding or 'utf-8')
    return decoded_subject

def check_for_updates(imap_server, imap_user, imap_pass, folder='INBOX'):
    logging.debug("Checking for update emails...")
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(imap_user, imap_pass)
        mail.select('folder')

        logging.debug("Searching for emails with subject 'Update News Preferences'")
        _, message_numbers = mail.search(None, '(UNSEEN SUBJECT "Update News Preferences")')
        
        if not message_numbers[0]:
            logging.debug("No new update emails found.")
            mail.close()
            mail.logout()
            return None, None

        for num in message_numbers[0].split():
            logging.debug(f"Processing email number: {num}")
            _, msg_data = mail.fetch(num, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    email_body = response_part[1]
                    email_message = email.message_from_bytes(email_body)
                    
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                    else:
                        body = email_message.get_payload(decode=True).decode()
                    
                    logging.debug(f"Email body: {body}")
                    
                    lines = body.strip().split('\n')
                    new_query = None
                    new_subject = None
                    for line in lines:
                        if line.startswith("New Query:"):
                            new_query = line.replace("New Query:", "").strip()
                            logging.debug(f"New query found: {new_query}")
                        elif line.startswith("New Subject:"):
                            new_subject = line.replace("New Subject:", "").strip()
                            logging.debug(f"New subject found: {new_subject}")
                    
                    mail.store(num, '+FLAGS', '\\Seen')
                    logging.debug("Email marked as read")
                    
                    mail.close()
                    mail.logout()
                    return new_query, new_subject

    except Exception as e:
        logging.error(f"Error in check_for_updates: {str(e)}")
    
    logging.debug("No valid update email found")
    return None, None

