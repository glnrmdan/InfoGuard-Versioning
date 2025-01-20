import socket
import requests
import tiktoken
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning 
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Just for developing only the API is here
client = OpenAI(api_key="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")

def get_full_title(url):
    try:
        session = requests_retry_session()
        response = session.get(url, timeout=10, verify=False)  # Disable SSL verification
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title')
        if title:
            return title.string.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching full title from {url}: {str(e)}")
    except socket.gaierror as e:
        print(f"DNS resolution error for {url}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error fetching title from {url}: {str(e)}")
    return None

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
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

def extract_article_content(url):
    try:
        session = requests_retry_session()
        response = session.get(url, timeout=10, verify=False)  # Disable SSL verification
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
        
        return text
    except requests.exceptions.RequestException as e:
        print(f"Error extracting content from {url}: {str(e)}")
    except socket.gaierror as e:
        print(f"DNS resolution error for {url}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error extracting content from {url}: {str(e)}")
    return ""

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
                            {"role": "system", "content": "Summarize the following text in a few sentences:"},
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
                    {"role": "system", "content": "Summarize the following text in a few sentences:"},
                    {"role": "user", "content": text}
                ],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in summarization: {str(e)}")
        return text[:200] + "..."  # Fallback to first 200 characters of the original text