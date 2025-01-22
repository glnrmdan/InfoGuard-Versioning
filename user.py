from datetime import datetime, timedelta, timezone

class User:
    """
    A class representing a user of the news update service.
    
    This class manages user preferences and timing for news searches and delivery.
    """
    def __init__(self, email, search_query, email_subject, search_interval):
        """
        Initialize a new User instance.
        
        Args:
            email (str): User's email address for receiving updates
            search_query (str): The search term or phrase for finding relevant news
            email_subject (str): Subject line for email updates
            last_news_sent (datetime): Timestamp of the last news delivery
            search_interval (int): Minutes between searches
            next_search_time (datetime): Scheduled time for the next search
        
        Note:
            All datetime attributes are initialized with UTC timezone
        """
        self.email = email # WHO to send results to (particular user email address)
        self.search_query = search_query # WHAT to search for
        self.email_subject = email_subject # How to label the results
        self.last_news_sent = datetime.now(timezone.utc)  # When was the last email sent to this user
        self.search_interval = search_interval # WHEN to search/ scrape of online article for particular user
        self.next_search_time = datetime.now(timezone.utc) # When should the next search be performed

    def update_last_news_sent(self):
        """
        Updates the timestamp of the last news delivery and calculates next search time.
        
        This method is called after successfully sending news to the user.
        Updates both last_news_sent and next_search_time based on the search_interval.
        
        Returns:
            None
        """
        self.last_news_sent = datetime.now() # Update the last_news_sent timestamp
        self.next_search_time = self.last_news_sent + timedelta(minutes=self.search_interval) # Calculate the next search time
        
    def is_ready_for_search(self):
        """
        Checks if it's time to perform a new search for this user.
        
        Compares current time against next scheduled search time.
        
        Returns:
            bool: True if current time is >= next_search_time, False otherwise
        """
        return datetime.now(timezone.utc) >= self.next_search_time # Check if it's time to perform a search
    
    def set_next_search_time(self, next_time):
        """
        Sets the next scheduled search time for this user.
        
        Args:
            next_time (datetime): The datetime for the next search
        
        Note:
            Automatically converts naive datetime to UTC if timezone is not specified
        
        Returns:
            None
        """
        if next_time.tzinfo is None:
            next_time = next_time.replace(tzinfo=timezone.utc)
        self.next_search_time = next_time