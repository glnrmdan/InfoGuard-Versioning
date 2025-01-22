import re
import time
import logging
import requests
import pandas as pd
from serpapi import GoogleSearch
from article_extraction import extract_article_content, summarize_text, get_full_title
from loader import load_all_configs, validate_configs

# Set up logging
logging.basicConfig(level=logging.DEBUG)

try:
    configs = load_all_configs()
    validate_configs(configs)
    
    # Use the configurations
    API_KEY = configs['google_api_key']
    SEARCH_ENGINE_ID = configs['search_engine_id']
    SERPAPI_KEY = configs['serpapi_key']

except Exception as e:
    logging.error(f"Failed to load configurations: {str(e)}")
    raise
def clean_filename(filename):
    """
    Sanitizes a string to be used as a safe filename.
    
    Args:
        filename (str): Original filename string
    
    Returns:
        str: Sanitized filename with special characters removed
    """
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    return filename

# date_restrict as time configuration
def build_google_payload(query, start=1, num=10, date_restrict='w1', **params):
    """
    Constructs the payload for Google Custom Search API requests.
    
    Args:
        query (str): Search query string
        start (int): Starting index for search results (1-based)
        num (int): Number of results to return (max 10)
        date_restrict (str): Time restriction for results (e.g., 'w1' for past week)
        **params: Additional API parameters
    
    Returns:
        dict: Complete API request parameters
    """
    payload = {
        'key': API_KEY,
        'q': query,
        'cx': SEARCH_ENGINE_ID,
        'start': start,
        'num': num,
        'dateRestrict': date_restrict
    }
    
    payload.update(params)
    return payload

def make_google_request(payload):
    """
    Executes a Google Custom Search API request.
    
    Args:
        payload (dict): API request parameters
    
    Returns:
        dict: JSON response from API or None if error occurs
    
    Raises:
        requests.exceptions.HTTPError: For HTTP errors
        Exception: For other errors
    """
    try:
        response = requests.get('https://www.googleapis.com/customsearch/v1', params=payload)
        response.raise_for_status()  # This will raise an HTTPError for bad responses
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        print(f"Response content: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def make_serpapi_request(query, num_results=10):
    """
    Executes a SerpAPI search request.
    
    Args:
        query (str): Search query string
        num_results (int): Number of results to return
    
    Returns:
        dict: Search results from SerpAPI
    
    Note:
        Uses global SERPAPI_KEY constant
        Specifically searches news results
    """
    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "q": query,
        "num": num_results,
        "tbm": "nws" # This parameters sets the search to the news
    }
    search = GoogleSearch(params)
    return search.get_dict()

def process_search_results(items):
    """
    Processes raw search results into structured format with summaries.
    
    Args:
        items (list): List of raw search result items
    
    Returns:
        list: Processed results with titles, summaries, and sources
    
    Note:
        - Includes error handling for inaccessible articles
        - Adds 1-second delay between requests
        - Attempts to get full article content and summarize it
    """
    processed_results = []
    for item in items:
        api_title = item.get('title', '').strip()
        link = item.get('link', '')
        
        full_title = get_full_title(link)
        title = full_title if full_title else api_title
        
        content = extract_article_content(link)
        if content.startswith("Error:") or content.startswith("Access to this page has been denied"):
            summary = f"We couldn't access the full content of this article due to the following issue:\n{content}\n\nHowever, here's what we know about it:\n\nTitle: {title}\n\nYou can try accessing the article directly at: {link}"
        else:
            try:
                summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
                if not summary:
                    summary = f"We couldn't summarize this article, but here's a brief excerpt:\n\n{content[:200]}...\n\nYou can read the full article at: {link}"
            except Exception as e:
                summary = f"An error occurred while summarizing this article: {str(e)}\n\nHowever, here's what we know about it:\n\nTitle: {title}\n\nYou can try reading the full article at: {link}"
        
        processed_results.append({
            'Title': title,
            'Summary': summary,
            'Source': link
        })
        time.sleep(1)  # Add a 1-second delay between requests
    return processed_results

def perform_search(query, result_total=10, use_serpapi=False, extra_results=5):
    """
    Performs search operation using either Google API or SerpAPI.
    
    Args:
        query (str): Search query string
        result_total (int): Number of results desired
        use_serpapi (bool): Whether to use SerpAPI instead of Google API
        extra_results (int): Additional results to fetch for backup
    
    Returns:
        list: Raw search results
    
    Note:
        - Handles pagination for Google API
        - Includes error handling and logging
    """
    total_to_fetch = result_total + extra_results
    try:
        if use_serpapi:
            response = make_serpapi_request(query, result_total)
            items = response.get('news_results', [])
        else:
            items = []
            reminder = result_total % 10
            pages = (result_total // 10) + 1 if reminder > 0 else result_total // 10
            
            for i in range(pages):
                if pages == i + 1 and reminder > 0:
                    payload = build_google_payload(query, start=i*10 + 1, num=reminder)
                else:
                    payload = build_google_payload(query, start=i*10 + 1)
                response = make_google_request(payload)
                if response is None:
                    logging.error("Failed to get response from Google Search API")
                    continue
                items.extend(response.get('items', []))
        
        logging.info(f"Raw search results: {items}")  # Log raw results
        
        if not items:
            logging.warning("No search results found")
            return []

        return items  # Return raw items instead of processed results
    except Exception as e:
        logging.error(f"Error in perform_search: {str(e)}", exc_info=True)
        return []

def process_and_replace_results(items, query, result_total, use_serpapi):
    """
    Processes search results and handles failed items with replacements.
    
    Args:
        items (list): Raw search result items
        query (str): Original search query
        result_total (int): Desired number of results
        use_serpapi (bool): Whether SerpAPI was used
    
    Returns:
        list: Processed results with replacements for failed items
    
    Note:
        - Includes error handling for each processing step
        - Attempts to replace failed items with extra results
        - Adds 1-second delay between requests
        - Logs processing statistics
    """
    processed_results = []
    error_count = 0
    extra_items_index = result_total
    
    for item in items[:result_total]:
        try:
            api_title = item.get('title', '').strip()
            link = item.get('link', '')
            
            if not link:
                logging.warning(f"Empty URL found for item: {item}")
                raise ValueError("Empty URL")
            
            full_title = get_full_title(link) or api_title
            
            content = extract_article_content(link)
            if not content or content.startswith("Error:"):
                if "Access blocked by Indonesian ISP" in content:
                    logging.warning(f"Access blocked by Indonesian ISP for {link}")
                    raise ValueError("Access blocked by Indonesian ISP")
                else:
                    raise ValueError(f"Unable to extract content: {content}")
            
            summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
            if not summary:
                raise ValueError("Unable to summarize content")
            
            processed_results.append({
                'Title': full_title,
                'Summary': summary,
                'Source': link
            })
        except Exception as e:
            logging.error(f"Error processing {link}: {str(e)}")
            error_count += 1
            
            # Try to replace with an extra result
            while extra_items_index < len(items):
                replacement_item = items[extra_items_index]
                extra_items_index += 1
                try:
                    api_title = replacement_item.get('title', '').strip()
                    link = replacement_item.get('link', '')
                    
                    if not link:
                        logging.warning(f"Empty URL found for replacement item: {replacement_item}")
                        continue
                    
                    full_title = get_full_title(link) or api_title
                    
                    content = extract_article_content(link)
                    if not content or content.startswith("Error:"):
                        continue
                    
                    summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
                    if not summary:
                        continue
                    
                    processed_results.append({
                        'Title': full_title,
                        'Summary': summary,
                        'Source': link
                    })
                    break
                except Exception as e:
                    logging.error(f"Error processing replacement {link}: {str(e)}")
            else:
                logging.warning("No more replacement results available")
        
        if len(processed_results) == result_total:
            break
        
        time.sleep(1) # 1 second delay between requests
    
    logging.info(f"Processed {len(processed_results)} results with {error_count} errors")
    return processed_results