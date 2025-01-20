import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pandas as pd
import io


def send_email(subject, body, to_email, from_email, password, attachment=None):
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
    
def format_results_as_html(results):
    html = "<html><body>"
    for result in results:
        html += f"<h2>{result['Title']}</h2>"
        html += f"<p>{result['Summary']}</p>"
        html += f"<a href='{result['Source']}'>Read More</a>"
        html += "<hr>"
    html += "</body></html>"
    return html

def manage_and_send_results(results, to_email, from_email, password, subject):
    body = format_results_as_html(results)
    # Create Excel file in memory (as before)
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
    send_email(subject, body, to_email, from_email, password, output)
    print(f"Email sent to {to_email}")
    
def send_confirmation_email(to_email, new_query, new_subject, from_email, email_password):
    subject = "News Preferences Updated"
    body = f"Your news preferences have been updated.\n\nNew Query: {new_query}\n"
    if new_subject:
        body += f"New Subject: {new_subject}\n"
    body += "\nYou will start receiving news based on these new preferences in the next update."
    
    send_email(subject, body, to_email, from_email, email_password)