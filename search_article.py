import re
import time
import logging
import requests
import pandas as pd
from serpapi import GoogleSearch
from article_extraction import extract_article_content, summarize_text, get_full_title

# Just for developing only the API key is here
API_KEY = "AIzaSyCwWlf7Ka_BHc9fNElQtFoKRJUlDaV7O_o"
SEARCH_ENGINE_ID = "70ff0242dca66436a"
SERPAPI_KEY = "b397516f95f8e092c677d0b9e12d11a714a2849911a81d1197056366c1ead3cb"

def clean_filename(filename):
    """
    Function to clean up string to be used as a filename.
    
    :param filename: The original string to be cleaned up
    
    :return: Cleaned up string safe to use as a filename
    """
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    return filename

# date_restrict as time configuration
def build_google_payload(query, start=1, num=10, date_restrict='w1', **params):
    """
    Function to build the payload for the Google Search API request.
    
    :param query: The search term (query)
    :param start: The index of the first result to return
    :param link_site: Specifies that all search results should contain a link to a particular URL
    :param search_type: Type of search (default is undefined, 'IMAGE' for image search)
    :param date_restrict: Restricts results based on recency (on 1 week)
    :param params: Additional parameters to be included in the request
    
    :return: Dictionary containing the API request parameters
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
    Function to send a GET request to the Google Search API and handle potential errors.
    
    :param payload: Dictionary containing the API request parameters
    :return: JSON response from the API
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
    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "q": query,
        "num": num_results,
        "tbm": "nws" # This parameters sets the search to the news
    }
    search = GoogleSearch(params)
    return search.get_dict()

# In the process_search_results function:
# def process_search_results(items):
    processed_results = []
    for item in items:
        api_title = item.get('title', '').strip()
        link = item.get('link', '')
        
        # Try to get the full title from the webpage
        full_title = get_full_title(link)
        
        # Use the full title if available, otherwise use the API-provided title
        title = full_title if full_title else api_title
        
        content = extract_article_content(link)
        if not content:
            content = "Unable to extract content from this page."
        
        summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
        processed_results.append({
            'Title': title,
            'Summary': summary if summary else "Unable to summarize content.",
            'Source': link
        })
        time.sleep(1)  # Add a 1-second delay between requests
    return processed_results

def process_search_results(items):
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

# def process_and_replace_results(items, query, result_total, use_serpapi):
    processed_results = []
    error_count = 0
    extra_items_index = result_total
    
    for item in items[:result_total]:
        try:
            api_title = item.get('title', '').strip()
            link = item.get('link', '')
            
            full_title = get_full_title(link)
            title = full_title if full_title else api_title
            
            content = extract_article_content(link)
            if content.startswith("Error:") or content.startswith("Access to this page has been denied"):
                raise Exception(content)
            
            summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
            if not summary:
                raise Exception("Unable to summarize content")
            
            processed_results.append({
                'Title': title,
                'Summary': summary,
                'Source': link
            })
        except Exception as e:
            print(f"Error processing {link}: {str(e)}")
            error_count += 1
            
            # Try to replace with an extra result
            if extra_items_index < len(items):
                print(f"Replacing with next available result")
                replacement_item = items[extra_items_index]
                extra_items_index += 1
                try:
                    api_title = replacement_item.get('title', '').strip()
                    link = replacement_item.get('link', '')
                    
                    full_title = get_full_title(link)
                    title = full_title if full_title else api_title
                    
                    content = extract_article_content(link)
                    if content.startswith("Error:") or content.startswith("Access to this page has been denied"):
                        raise Exception(content)
                    
                    summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
                    if not summary:
                        raise Exception("Unable to summarize content")
                    
                    processed_results.append({
                        'Title': title,
                        'Summary': summary,
                        'Source': link
                    })
                except Exception as e:
                    print(f"Error processing replacement {link}: {str(e)}")
                    error_count += 1
            else:
                print("No more replacement results available")
        
        time.sleep(1) # 1 second delay between requests
        
    # In case still don't have enough results, perform another search
    while len(processed_results) < result_total:
        print(f"Not enough results, performing additional search")
        additional_items = perform_search(query, result_total - len(processed_results), use_serpapi)
        for item in additional_items:
            try:
                api_title = item.get('title', '').strip()
                link = item.get('link', '')
                
                full_title = get_full_title(link)
                title = full_title if full_title else api_title
                
                content = extract_article_content(link)
                if not content:
                    raise Exception("Unable to extract content")
                
                summary = summarize_text(content, max_tokens=150, max_chunk_tokens=3000)
                if not summary:
                    raise Exception("Unable to summarize content")
                
                processed_results.append({
                    'Title': title,
                    'Summary': summary,
                    'Source': link
                })
                
                if len(processed_results) == result_total:
                    break
            except Exception as e:
                print(f"Error processing additional result {link}: {str(e)}")
                
            time.sleep(1)
            
    return processed_results