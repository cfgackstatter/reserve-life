"""
General Utilities Module
Contains company info fetching and data persistence functions.
"""

from typing import Dict, Any, Optional
import yfinance as yf
import json
import os


def get_yahoo_info(ticker: str) -> Optional[Dict[str, str]]:
    """
    Fetch basic company info from Yahoo Finance.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dict with company info or None if not found
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        if info and 'longName' in info:
            return {
                'ticker': ticker.upper(),
                'name': info.get('longName', ''),
                'country': info.get('country', '')
            }
    except Exception as e:
        print(f"Error fetching Yahoo info for {ticker}: {e}")
    return None


def load_company_data(data_file: str) -> Dict[str, Any]:
    """
    Load company data from JSON file.
    
    Args:
        data_file: Path to JSON data file
        
    Returns:
        Dict containing company data
    """
    if os.path.exists(data_file):
        try:
            with open(data_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data file {data_file}: {e}")
    return {}


def save_company_data(data: Dict[str, Any], data_file: str) -> None:
    """
    Save company data to JSON file.
    
    Args:
        data: Company data dictionary
        data_file: Path to JSON data file
    """
    try:
        with open(data_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data file {data_file}: {e}")
