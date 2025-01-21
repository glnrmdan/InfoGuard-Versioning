from imap_tools import MailBox

MAIL_PASSWORD = 'xuouvmsncyasmxqa'
MAIL_USERNAME = 'testmail1122222@gmail.com'

with MailBox("imap.gmail.com").login(MAIL_USERNAME, MAIL_PASSWORD, "Inbox") as mailbox:
    # print(mailbox.folder.list())
    # print(mailbox.folder.get())
    for msg in mailbox.fetch(limit=1, reverse=True, mark_seen=True):
        print(f"Email from: {msg.from_} -- {msg.date}\nSubject: {msg.subject}\nText: {msg.text}")
