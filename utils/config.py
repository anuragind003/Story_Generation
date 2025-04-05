# utils/config.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Models - All these models support JSON response format
DEFAULT_MODEL = "gpt-3.5-turbo-0125"
PLANNER_MODEL = "gpt-4-turbo-preview"
GENERATOR_MODEL = "gpt-4-turbo-preview"
REFINER_MODEL = "gpt-4-turbo-preview"
UPDATER_MODEL = "gpt-3.5-turbo-0125"

def load_api_key():
    """Get API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY not found in environment variables")
        # List the environment variables for debugging
        logging.debug("Available environment variables: " + ", ".join(os.environ.keys()))
    else:
        # Log that we found the key (without showing the full key)
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        logging.info(f"Found API key: {masked_key}")
    return api_key