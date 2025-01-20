import re
import time
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
def process_search_results(items):
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
                    print("Failed to get response from Google Search API")
                    continue
                items.extend(response.get('items', []))
        
        if not items:
            print("No search results found")
            return []

        processed_results = process_search_results(items)
        
        query_string_clean = clean_filename(query)
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        df = pd.DataFrame(processed_results)
        
        # Create a Pandas Excel writer using XlsxWriter as the engine
        with pd.ExcelWriter(f"Search_Result_{query_string_clean}_{timestamp}.xlsx", engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # Set the column width for the Title column (adjust the width as needed)
            worksheet.set_column('A:A', 50)  # Set width of column A (Title) to 50
            
            # Set the column width for the Summary column
            worksheet.set_column('B:B', 100)  # Set width of column B (Summary) to 100
            
            # Set the column width for the Source column
            worksheet.set_column('C:C', 50)  # Set width of column C (Source) to 50

        return processed_results
    except Exception as e:
        print(f"Error in perform_search: {str(e)}")
        return []

def process_and_replace_results(items, query, result_total, use_serpapi):
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
            if not content:
                raise Exception("Unable to extract content")
            
            summary = summarize_text(content, max_token=150, max_chunk_tokens=3000)
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
                except Exception as e:
                    print(f"Error processing replacement {link}: {str(e)}")
                    error_count += 1
            else:
                print("No more replacement results available")
        
        time.sleep(1) # 1 seconds delay between request
        
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