import io
import email
import smtplib
import logging
import pandas as pd
from email.mime.text import MIMEText # Handle non-ASCII characters
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_email(subject, body, to_email, from_email, password, attachment=None):
    """
    Sends an email with optional Excel attachment using Gmail SMTP.
    
    Args:
        subject (str): Email subject line
        body (str): Email body content (HTML format)
        to_email (str): Recipient email address
        from_email (str): Sender email address
        password (str): Sender email password or app-specific password
        attachment (BytesIO, optional): Excel file as bytes stream
    
    Raises:
        smtplib.SMTPAuthenticationError: If email/password authentication fails
        smtplib.SMTPException: For other SMTP-related errors
        Exception: For unexpected errors
    
    Note:
        - Uses Gmail SMTP server on port 587
        - Supports HTML content
        - Can attach Excel files
    """
    try:
        msg = MIMEMultipart()
        # Email structure that will be sent
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach the email body as HTML content (templating reason)
        msg.attach(MIMEText(body, 'html'))
        
        if attachment is not None: # Check if there's an attachment
            part = MIMEApplication(attachment.getvalue(), Name='search_result.xlsx')
            part['Content-Disposition'] = f'attachment; filename="search_result.xlsx"' # Set the attachment name
            msg.attach(part)
        
        # SMTP gmail server connection
        server = smtplib.SMTP('smtp.gmail.com', 587) # SMTP Port 587
        server.starttls()
        server.login(from_email, password)
        
        # Send the email
        text = msg.as_string() # Convert the message to a string
        server.sendmail(from_email, to_email, text) # Send the email
        server.quit() # Close the connection
        logging.info("Email sent successfully.")
        
    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP Authentication Error. Please check your email and password.")
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending email: {str(e)}", exc_info=True)
    
# HTML format 
def format_results_as_html(results):
    """
    Formats search results into HTML format for email body.
    
    Args:
        results (list): List of dictionaries containing search results
            Each dictionary should have:
                - Title: Article title
                - Summary: Article summary
                - Source: Article URL
    
    Returns:
        str: HTML formatted string containing all results
    
    Example:
        results = [
            {
                'Title': 'Example Article',
                'Summary': 'Article summary...',
                'Source': 'https://example.com'
            }
        ]
    """

    html = "<html><body>"
    for result in results:
        html += f"<h2>{result['Title']}</h2>"
        html += f"<p>{result['Summary']}</p>"
        html += f"<a href='{result['Source']}'>Read More</a>"
        html += "<hr>"
    html += "</body></html>"
    return html
    
def manage_and_send_results(results, user, from_email, password, subject):
    """
    Manages the process of formatting results and sending them via email.
    
    This function:
        1. Formats results as HTML
        2. Creates Excel attachment
        3. Sends email with both HTML content and Excel attachment
        4. Updates user's last news sent timestamp
    
    Args:
        results (list): List of search results
        user (User): User object containing email and preferences
        from_email (str): Sender email address
        password (str): Sender email password
        subject (str): Email subject line
    
    Raises:
        Exception: If there's an error in sending email or creating attachment
    
    Note:
        - Excel file includes all columns from results
        - Columns are auto-sized for better readability
        - Don't inclue the excel file later. Only send the email.
    """
    logging.info(f"Managing and sending results to {user.email}")
    if not results:
        logging.warning(f"No results to send to {user.email}.")
        return
    
    body = format_results_as_html(results)
    output = io.BytesIO()
    df = pd.DataFrame(results)
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        worksheet.set_column('A:A', 50)
        worksheet.set_column('B:B', 100)
        worksheet.set_column('C:C', 50)
    output.seek(0)
    try:
        send_email(subject, body, user.email, from_email, password, output)
        user.update_last_news_sent()
        logging.info(f"Email sent successfully to {user.email}")
    except Exception as e:
        logging.error(f"Error sending email to {user.email}: {str(e)}", exc_info=True)
    
# Confirmation email that user already changed their preferences
def send_confirmation_email(to_email, new_query, new_subject, from_email, email_password):
    """
    Sends a confirmation email when user preferences are updated.
    
    Args:
        to_email (str): User's email address
        new_query (str): Updated search query
        new_subject (str): Updated email subject
        from_email (str): Sender email address
        email_password (str): Sender email password
    
    Note:
        - Confirms both query and subject changes
        - Informs user about when changes will take effect
    """
    subject = "News Preferences Updated"
    body = f"Your news preferences have been updated.\n\nNew Query: {new_query}\n"
    if new_subject:
        body += f"New Subject: {new_subject}\n"
    body += "\nYou will start receiving news based on these new preferences in the next update."
    
    send_email(subject, body, to_email, from_email, email_password)