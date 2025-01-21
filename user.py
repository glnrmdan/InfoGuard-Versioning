from datetime import datetime

class User:
    def __init__(self, email, search_query, email_subject):
        self.email = email
        self.search_query = search_query
        self.email_subject = email_subject
        self.last_news_sent = datetime.min  # Initialize with the earliest possible date

    def update_last_news_sent(self):
        self.last_news_sent = datetime.now()