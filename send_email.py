import io
import email
import smtplib
import logging
import pandas as pd
from email.mime.text import MIMEText
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


# def send_email(subject, body, to_email, from_email, password, attachment=None):
#     msg = MIMEMultipart()
#     msg['From'] = from_email
#     msg['To'] = to_email
#     msg['Subject'] = subject
    
#     msg.attach(MIMEText(body, 'html'))
    
#     if attachment is not None:
#         part = MIMEApplication(attachment.getvalue(), Name='search_result.xlsx')
#         part['Content-Disposition'] = f'attachment; filename="search_result.xlsx"'
#         msg.attach(part)
        
#     server = smtplib.SMTP('smtp.gmail.com', 587)
#     server.starttls()
#     server.login(from_email, password)
#     text = msg.as_string()
#     server.sendmail(from_email, to_email, text)
#     server.quit()
    
def send_email(subject, body, to_email, from_email, password, attachment=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        if attachment is not None:
            part = MIMEApplication(attachment.getvalue(), Name='search_result.xlsx')
            part['Content-Disposition'] = f'attachment; filename="search_result.xlsx"'
            msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        logging.info("Email sent successfully.")
    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP Authentication Error. Please check your email and password.")
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending email: {str(e)}", exc_info=True)
    
def format_results_as_html(results):
    html = "<html><body>"
    for result in results:
        html += f"<h2>{result['Title']}</h2>"
        html += f"<p>{result['Summary']}</p>"
        html += f"<a href='{result['Source']}'>Read More</a>"
        html += "<hr>"
    html += "</body></html>"
    return html

# def manage_and_send_results(results, to_email, from_email, password, subject):
#     body = format_results_as_html(results)
#     # Create Excel file in memory (as before)
#     output = io.BytesIO()
#     df = pd.DataFrame(results)
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, index=False, sheet_name='Sheet1')
#         workbook = writer.book
#         worksheet = writer.sheets['Sheet1']
#         worksheet.set_column('A:A', 50)
#         worksheet.set_column('B:B', 100)
#         worksheet.set_column('C:C', 50)
#     output.seek(0)
#     send_email(subject, body, to_email, from_email, password, output)
#     print(f"Email sent to {to_email}")
 
    
def manage_and_send_results(results, to_email, from_email, password, subject):
    logging.info(f"Managing and sending results to {to_email}")
    if not results:
        logging.warning("No results to send.")
        return
    
    try:
        body = format_results_as_html(results)
        logging.info("HTML body formatted successfully.")
        
        # Create Excel file in memory
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
        logging.info("Excel file created in memory successfully.")
        
        send_email(subject, body, to_email, from_email, password, output)
        logging.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logging.error(f"Error in manage_and_send_results: {str(e)}", exc_info=True)
    
def send_confirmation_email(to_email, new_query, new_subject, from_email, email_password):
    subject = "News Preferences Updated"
    body = f"Your news preferences have been updated.\n\nNew Query: {new_query}\n"
    if new_subject:
        body += f"New Subject: {new_subject}\n"
    body += "\nYou will start receiving news based on these new preferences in the next update."
    
    send_email(subject, body, to_email, from_email, email_password)