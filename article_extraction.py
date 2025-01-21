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

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Just for developing only the API is here
client = OpenAI(api_key="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")

# def get_full_title(url, max_retries=3, backoff_factor=0.3):
#     ssl_context = ssl.create_default_context()
#     ssl_context.check_hostname = False
#     ssl_context.verify_mode = ssl.CERT_NONE

#     scraper = cloudscraper.create_scraper(
#         browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False},
#         ssl_context=ssl_context
#     )
    
#     for attempt in range(max_retries):
#         try:
#             response = scraper.get(url, timeout=15)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.content, 'html.parser')
#             title = soup.find('title')
#             if title:
#                 return title.string.strip()
#         except RequestException as e:
#             print(f"Error fetching full title from {url}: {str(e)}")
#         except Exception as e:
#             print(f"Unexpected error fetching title from {url}: {str(e)}")
        
#         if attempt < max_retries - 1:
#             time.sleep(backoff_factor * (2 ** attempt))
    
#     return None

def get_full_title(url, max_retries=3, backoff_factor=0.3):
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
            response = scraper.get(url, timeout=15)
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
    # Create a custom SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Create a scraper with the custom SSL context
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False},
        ssl_context=ssl_context
    )
    
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=15)
            
            if response.status_code == 403:
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
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
    
    
def summarize_text(text, max_tokens=150, model="gpt-3.5-turbo", max_chunk_tokens=3000):
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




























# import socket
# import requests
# import tiktoken
# from openai import OpenAI
# from bs4 import BeautifulSoup
# from urllib3.util.retry import Retry
# from requests.adapters import HTTPAdapter
# from urllib3.exceptions import InsecureRequestWarning 
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# # Just for developing only the API is here
# client = OpenAI(api_key="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")

# def get_full_title(url):
#     try:
#         session = requests_retry_session()
#         response = session.get(url, timeout=10, verify=False)  # Disable SSL verification
#         soup = BeautifulSoup(response.content, 'html.parser')
#         title = soup.find('title')
#         if title:
#             return title.string.strip()
#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching full title from {url}: {str(e)}")
#     except socket.gaierror as e:
#         print(f"DNS resolution error for {url}: {str(e)}")
#     except Exception as e:
#         print(f"Unexpected error fetching title from {url}: {str(e)}")
#     return None

# def requests_retry_session(
#     retries=3,
#     backoff_factor=0.3,
#     status_forcelist=(500, 502, 504),
#     session=None):
    
#     session = session or requests.Session()
#     retry = Retry(
#         total=retries,
#         read=retries,
#         connect=retries,
#         backoff_factor=backoff_factor,
#         status_forcelist=status_forcelist,
#     )
#     adapter = HTTPAdapter(max_retries=retry)
#     session.mount('http://', adapter)
#     session.mount('https://', adapter)
#     return session

# def extract_article_content(url):
#     try:
#         session = requests_retry_session()
#         response = session.get(url, timeout=10, verify=False)  # Disable SSL verification
#         soup = BeautifulSoup(response.content, 'html.parser')
        
#         # Remove script and style elements
#         for script in soup(["script", "style"]):
#             script.decompose()
        
#         # Get text
#         text = soup.get_text()
        
#         # Break into lines and remove leading and trailing space on each
#         lines = (line.strip() for line in text.splitlines())
#         # Break multi-headlines into a line each
#         chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
#         # Drop blank lines
#         text = '\n'.join(chunk for chunk in chunks if chunk)
        
#         return text
#     except requests.exceptions.RequestException as e:
#         print(f"Error extracting content from {url}: {str(e)}")
#     except socket.gaierror as e:
#         print(f"DNS resolution error for {url}: {str(e)}")
#     except Exception as e:
#         print(f"Unexpected error extracting content from {url}: {str(e)}")
#     return ""

# def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
#     """Returns the number of tokens in a text string."""
#     encoding = tiktoken.get_encoding(encoding_name)
#     num_tokens = len(encoding.encode(string))
#     return num_tokens
    
    
# def summarize_text(text, max_tokens=150, model="gpt-3.5-turbo", max_chunk_tokens=3000):
#     try:
#         # Calculate the number of tokens in the input text
#         input_tokens = num_tokens_from_string(text)
        
#         # If the input is too long, split it into chunks
#         if input_tokens > max_chunk_tokens:
#             chunks = []
#             current_chunk = ""
#             current_tokens = 0
#             for sentence in text.split('.'):
#                 sentence_tokens = num_tokens_from_string(sentence)
#                 if current_tokens + sentence_tokens > max_chunk_tokens:
#                     if current_chunk:
#                         chunks.append(current_chunk)
#                     current_chunk = sentence
#                     current_tokens = sentence_tokens
#                 else:
#                     current_chunk += sentence + '.'
#                     current_tokens += sentence_tokens
#             if current_chunk:
#                 chunks.append(current_chunk)
            
#             # Summarize each chunk
#             summaries = []
#             for chunk in chunks:
#                 try:
#                     response = client.chat.completions.create(
#                         model=model,
#                         messages=[
#                             {"role": "system", "content": "Summarize the following text in a few sentences:"},
#                             {"role": "user", "content": chunk}
#                         ],
#                         max_tokens=max_tokens // len(chunks)  # Distribute tokens among chunks
#                     )
#                     summaries.append(response.choices[0].message.content.strip())
#                 except Exception as e:
#                     print(f"Error summarizing chunk: {str(e)}")
#                     summaries.append(chunk[:100] + "...")  # Fallback to first 100 characters of the chunk
            
#             # Combine summaries
#             combined_summary = " ".join(summaries)
            
#             # If the combined summary is still too long, summarize it again
#             if num_tokens_from_string(combined_summary) > max_tokens:
#                 return summarize_text(combined_summary, max_tokens, model, max_chunk_tokens)
#             else:
#                 return combined_summary
#         else:
#             # If the input is not too long, process it as before
#             response = client.chat.completions.create(
#                 model=model,
#                 messages=[
#                     {"role": "system", "content": "Summarize the following text in a few sentences:"},
#                     {"role": "user", "content": text}
#                 ],
#                 max_tokens=max_tokens
#             )
#             return response.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"Error in summarization: {str(e)}")
#         return text[:200] + "..."  # Fallback to first 200 characters of the original text