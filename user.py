from datetime import datetime, timedelta, timezone

class User:
    def __init__(self, email, search_query, email_subject, search_interval):
        self.email = email # WHO to send results to (particular user email address)
        self.search_query = search_query # WHAT to search for
        self.email_subject = email_subject # How to label the results
        self.last_news_sent = datetime.now(timezone.utc)  # When was the last email sent to this user
        self.search_interval = search_interval # WHEN to search/ scrape of online article for particular user
        self.next_search_time = datetime.now(timezone.utc) # When should the next search be performed

    def update_last_news_sent(self):
        self.last_news_sent = datetime.now() # Update the last_news_sent timestamp
        self.next_search_time = self.last_news_sent + timedelta(minutes=self.search_interval) # Calculate the next search time
        
    def is_ready_for_search(self):
        return datetime.now(timezone.utc) >= self.next_search_time # Check if it's time to perform a search
    
    def set_next_search_time(self, next_time):
        if next_time.tzinfo is None:
            next_time = next_time.replace(tzinfo=timezone.utc)
        self.next_search_time = next_time