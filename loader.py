import os
import logging
from openai import OpenAI

# Define base directory (current directory where the script is running)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_config_path(filename):
    """
    Constructs the full path to a configuration file.
    
    Args:
        filename (str): Name of the configuration file
    
    Returns:
        str: Full path to the configuration file
    """
    return os.path.join(BASE_DIR, filename)

def load_openai_key(filename='openai_api_key.txt'):
    """
    Loads OpenAI API key from the configuration file.
    
    Args:
        filename (str): Name of the OpenAI API key file
    
    Returns:
        str: OpenAI API key
        
    Raises:
        FileNotFoundError: If the API key file is not found
        IOError: If there's an error reading the file
    """
    file_path = get_config_path(filename)
    logging.debug(f"Loading OpenAI API key from: {file_path}")
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"OpenAI API key file not found at {file_path}")
    except IOError as e:
        raise IOError(f"Error reading OpenAI API key file: {str(e)}")


def load_search_api_keys(filename='search_api_keys.txt'):
    """
    Loads search API keys from the configuration file.
    
    Args:
        filename (str): Name of the search API keys file
    
    Returns:
        dict: Dictionary containing Google and SerpAPI configurations
        
    Raises:
        FileNotFoundError: If the config file is not found
        ValueError: If the config file is missing required values
    """
    file_path = get_config_path(filename)
    logging.debug(f"Loading search API keys from: {file_path}")
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            logging.debug(f"Read {len(lines)} lines from config file")
            config = {}
            for line in lines:
                logging.debug(f"Processing line: {line.strip()}")
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip()
            
            logging.debug(f"Parsed configuration: {config}")
            
            # Extract required values
            google_api_key = config.get('google_api_key')
            search_engine_id = config.get('search_engine_id')
            serpapi_key = config.get('serpapi_key')
            
            logging.debug(f"Extracted values:")
            logging.debug(f"google_api_key: {'present' if google_api_key else 'missing'}")
            logging.debug(f"search_engine_id: {'present' if search_engine_id else 'missing'}")
            logging.debug(f"serpapi_key: {'present' if serpapi_key else 'missing'}")
            
            if not all([google_api_key, search_engine_id, serpapi_key]):
                missing_keys = [key for key, value in {
                    'google_api_key': google_api_key,
                    'search_engine_id': search_engine_id,
                    'serpapi_key': serpapi_key
                }.items() if not value]
                raise ValueError(f"Missing required search API configuration values: {', '.join(missing_keys)}")
                
            return {
                'google_api_key': google_api_key,
                'search_engine_id': search_engine_id,
                'serpapi_key': serpapi_key
            }
    except FileNotFoundError:
        raise FileNotFoundError(f"Search API keys file not found at {file_path}")
    except Exception as e:
        logging.error(f"Error while processing search API keys: {str(e)}")
        logging.error(f"File content:")
        try:
            with open(file_path, 'r') as file:
                logging.error(file.read())
        except Exception as read_error:
            logging.error(f"Could not read file content: {str(read_error)}")
        raise IOError(f"Error reading search API keys: {str(e)}")

def load_all_configs():
    """
    Loads all API keys and configurations.
    
    Returns:
        dict: Dictionary containing all API keys and configurations
        
    Raises:
        Exception: If any configuration loading fails
    """
    try:
        # Load OpenAI API key
        openai_key = load_openai_key()
        
        # Load search API keys
        search_configs = load_search_api_keys()
        
        # Combine all configurations
        configs = {
            'openai_api_key': openai_key,
            **search_configs
        }
        
        return configs
    except Exception as e:
        logging.error(f"Error loading configurations: {str(e)}")
        raise

def validate_configs(configs):
    """
    Validates loaded configurations.
    
    Args:
        configs (dict): Dictionary of loaded configurations
        
    Returns:
        bool: True if all configurations are valid
        
    Raises:
        ValueError: If any configuration is invalid
    """
    validation_rules = {
        'openai_api_key': (lambda x: x.startswith('sk-'), "Invalid OpenAI API key format"),
        'google_api_key': (lambda x: x.startswith('AIza'), "Invalid Google API key format"),
        'search_engine_id': (lambda x: bool(x), "Missing Google Search Engine ID"),
        'serpapi_key': (lambda x: len(x) >= 64, "Invalid SerpAPI key format")
    }
    
    for key, (validator, error_msg) in validation_rules.items():
        if key not in configs or not validator(configs[key]):
            raise ValueError(f"{error_msg} for {key}")
    
    return True