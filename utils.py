import yfinance as yf
import pandas as pd
import requests
import json
import os
import re
import random
import time
from datetime import datetime

def get_yahoo_info(ticker):
    """Fetch basic company info from Yahoo Finance."""
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info
    if info and 'longName' in info:
        return {
            'ticker': ticker.upper(),
            'name': info.get('longName', ''),
            'country': info.get('country', '')
        }
    return None

def get_cik_from_ticker(ticker):
    """Lookup CIK for a given ticker from SEC's ticker.txt (tab-separated)."""
    url_txt = "https://www.sec.gov/include/ticker.txt"
    try:
        headers = {"User-Agent": "your_email@example.com"}
        resp = requests.get(url_txt, headers=headers, timeout=10)
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            ticker_lower = ticker.lower()
            for line in lines:
                try:
                    tkr, cik = line.strip().split('\t')
                    if tkr == ticker_lower:
                        return str(cik).zfill(10)
                except ValueError:
                    continue
    except Exception as e:
        print(f"SEC request error: {e}")
    return None

def get_filings_in_date_range(cik, start_date, end_date, filing_types, user_agent="your_email@example.com"):
    """
    Generic function to fetch filings of specified types between start_date and end_date from SEC EDGAR.
    
    Args:
        cik (str): Company CIK (zero-padded 10 digits)
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format  
        filing_types (list): List of filing types like ['10-K', '10-Q', '8-K']
        user_agent (str): User agent for requests
    
    Returns:
        list: List of filing dicts sorted by date (descending)
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": user_agent}
    result = []
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        
        for form, acc_no, fdate, primary_doc in zip(
            filings.get("form", []),
            filings.get("accessionNumber", []),
            filings.get("filingDate", []),
            filings.get("primaryDocument", [])
        ):
            # Check if filing type matches and date is in range
            if (form.upper() in [ft.upper() for ft in filing_types] and 
                start_date <= fdate <= end_date):
                
                acc_no_nodash = acc_no.replace("-", "")
                html_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_nodash}/{primary_doc}"
                
                result.append({
                    "type": form,
                    "date": fdate,
                    "accession": acc_no,
                    "html_url": html_url,
                    "primary_document": primary_doc
                })
        
        # Sort by date descending
        result.sort(key=lambda x: x["date"], reverse=True)
        
    except Exception as e:
        print(f"Error fetching filings for CIK {cik}: {e}")
    
    return result

def extract_oil_data_from_10k(filing_url):
    """
    Dummy function that returns random oil data for testing.
    TODO: Replace with actual extraction logic later.
    """
    # Simulate processing time
    time.sleep(1)
    
    # Generate random but realistic values
    proved_reserves = random.uniform(5e9, 50e9)  # 5B to 50B barrels
    annual_production = random.uniform(50e6, 500e6)  # 50M to 500M barrels/year
    
    print(f"Extracted dummy data: Reserves: {proved_reserves:,.0f} barrels, Production: {annual_production:,.0f} barrels/year")
    
    return {
        'proved_reserves': proved_reserves,
        'annual_production': annual_production
    }