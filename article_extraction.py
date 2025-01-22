import ssl
import time
import socket
import logging
import tiktoken
import requests
import cloudscraper
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.exceptions import InsecureRequestWarning
from loader import load_all_configs, validate_configs

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

try:
    configs = load_all_configs()
    validate_configs(configs)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=configs['openai_api_key'])
    
except Exception as e:
    logging.error(f"Failed to load configurations: {str(e)}")
    raise

def get_full_title(url, max_retries=3, backoff_factor=0.3):
    """
    Extracts the full title from a webpage with retry mechanism.
    
    Args:
        url (str): URL of the webpage
        max_retries (int): Maximum number of retry attempts
        backoff_factor (float): Factor for exponential backoff between retries
    
    Returns:
        str or None: Page title if found, None otherwise
    
    Note:
        Uses CloudScraper to bypass common anti-bot protections
        Implements exponential backoff for retries
    """
    if not url:
        logging.error("Empty URL provided to get_full_title")
        return None

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False},
        ssl_context=ssl_context
    )
    
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=15, verify=False)  # Disable SSL verification
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            if title:
                return title.string.strip()
        except RequestException as e:
            logging.error(f"Error fetching full title from {url}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error fetching title from {url}: {str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(backoff_factor * (2 ** attempt))
    
    return None

def request_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 504],
    session=None):
    """
    Creates a requests session with retry capabilities.
    
    Args:
        retries (int): Number of retries for failed requests
        backoff_factor (float): Backoff factor between retries
        status_forcelist (list): HTTP status codes to retry on
        session (requests.Session, optional): Existing session to modify
    
    Returns:
        requests.Session: Configured session with retry mechanism
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def extract_article_content(url, max_retries=3, backoff_factor=0.3):
    """
    Extracts main content from a webpage with robust error handling.
    
    Args:
        url (str): URL of the webpage
        max_retries (int): Maximum number of retry attempts
        backoff_factor (float): Factor for exponential backoff between retries
    
    Returns:
        str: Extracted content or error message
    
    Note:
        - Handles various protection mechanisms (CloudFlare, PerimeterX)
        - Implements exponential backoff
        - Removes script and style elements
        - Handles "Internet Baik" blocking
    """
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False},
        ssl_context=ssl_context
    )
    
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=15, verify=False)  # Disable SSL verification
            
            # Handle Internet Baik (Some websites may blocked by provider and resulting as Internet Baik)
            # May need to find a ways to bypass it later
            if "Internet Baik" in response.text or "Internet Provider block" in response.text:
                return f"Error: Access blocked by Internet Baik or Internet Provider block for {url}. The website might be blocking automated access."
            elif response.status_code == 403:
                return f"Error: Access forbidden (403) for {url}. The website may be blocking automated access."
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            if not text:
                return f"Error: No text could be extracted from {url}. The page might be empty or use a format we can't process."
            
            return text
        
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                return f"Error: Request timed out for {url}. The website might be slow or unresponsive."
        
        except RequestException as e:
            if "Cloudflare" in str(e):
                return f"Error: Cloudflare protection detected for {url}. We couldn't bypass their security measures."
            elif "PerimeterX" in str(e):
                return f"Error: PerimeterX protection detected for {url}. We couldn't bypass their security measures."
            else:
                return f"Error: Unable to fetch content from {url}. Reason: {str(e)}"
        
        except Exception as e:
            return f"Error: Unexpected issue processing {url}. Reason: {str(e)}"
        
        if attempt < max_retries - 1:
            time.sleep(backoff_factor * (2 ** attempt))
    
    return f"Error: Maximum retries reached for {url}. We couldn't access the content after several attempts."

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """
    Counts the number of tokens in a text string using tiktoken.
    
    Args:
        string (str): Input text
        encoding_name (str): Name of the tokenizer encoding
    
    Returns:
        int: Number of tokens in the text
    """
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
    
    
def summarize_text(text, max_tokens=150, model="gpt-3.5-turbo", max_chunk_tokens=3000):
    """
    Summarizes text using OpenAI's GPT model with chunk handling.
    
    Args:
        text (str): Text to summarize
        max_tokens (int): Maximum tokens in the summary
        model (str): GPT model to use
        max_chunk_tokens (int): Maximum tokens per chunk
    
    Returns:
        str: Summarized text
    
    Note:
        - Handles long texts by chunking
        - Implements recursive summarization for long outputs
        - Includes fallback mechanism for errors
        - Distributes tokens among chunks for balanced summaries
    """
    try:
        # Calculate the number of tokens in the input text
        input_tokens = num_tokens_from_string(text)
        
        # If the input is too long, split it into chunks
        if input_tokens > max_chunk_tokens:
            chunks = []
            current_chunk = ""
            current_tokens = 0
            for sentence in text.split('.'):
                sentence_tokens = num_tokens_from_string(sentence)
                if current_tokens + sentence_tokens > max_chunk_tokens:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                else:
                    current_chunk += sentence + '.'
                    current_tokens += sentence_tokens
            if current_chunk:
                chunks.append(current_chunk)
            
            # Summarize each chunk
            summaries = []
            for chunk in chunks:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Summarize the text into a new text that cover the whole context in a few sentences:"},
                            {"role": "user", "content": chunk}
                        ],
                        max_tokens=max_tokens // len(chunks)  # Distribute tokens among chunks
                    )
                    summaries.append(response.choices[0].message.content.strip())
                except Exception as e:
                    print(f"Error summarizing chunk: {str(e)}")
                    summaries.append(chunk[:100] + "...")  # Fallback to first 100 characters of the chunk
            
            # Combine summaries
            combined_summary = " ".join(summaries)
            
            # If the combined summary is still too long, summarize it again
            if num_tokens_from_string(combined_summary) > max_tokens:
                return summarize_text(combined_summary, max_tokens, model, max_chunk_tokens)
            else:
                return combined_summary
        else:
            # If the input is not too long, process it as before
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Summarize the text into a new text that cover the whole context in a few sentences:"},
                    {"role": "user", "content": text}
                ],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in summarization: {str(e)}")
        return text[:200] + "..."  # Fallback to first 200 characters of the original text