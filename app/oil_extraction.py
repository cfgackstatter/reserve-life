"""
Oil Data Extraction Module

Extracts crude oil reserves and production data from SEC filings using LLM technology.
"""

from typing import Optional, Dict, Any, Tuple
import io
import sys
import math
import re
import requests
from contextlib import redirect_stdout, redirect_stderr
from bs4 import BeautifulSoup, Tag

from app.llm_client import query_llm, extract_json_from_response, is_llm_available

SEC_USER_AGENT = "your_email@example.com"


def has_reserves_keywords(text: str) -> bool:
    """Check if text contains crude oil reserves keywords."""
    if not text or len(text) < 20:
        return False
    text_lower = text.lower()
    if 'reserve' not in text_lower:
        return False
    oil_indicators = ['oil', 'crude', 'barrel', 'bbl', 'mmbbl', 'petroleum']
    if not any(ind in text_lower for ind in oil_indicators):
        return False
    return 'proved' in text_lower or 'proven' in text_lower or 'total' in text_lower


def has_production_keywords(text: str) -> bool:
    """Check if text contains crude oil production keywords."""
    if not text or len(text) < 20:
        return False
    text_lower = text.lower()
    if 'production' not in text_lower and 'produced' not in text_lower:
        return False
    oil_indicators = ['oil', 'crude', 'barrel', 'bbl', 'bpd', 'mbpd', 'petroleum']
    if not any(ind in text_lower for ind in oil_indicators):
        return False
    return any(ind in text_lower for ind in ['day', 'daily', 'annual', 'year', 'mbpd', 'bpd'])


def has_numbers(text: str) -> bool:
    """Check if text contains numbers."""
    return bool(re.search(r'\d', text))


def download_filing_html(filing_url: str) -> Optional[str]:
    """Download complete HTML content from SEC filing URL."""
    try:
        print(f"Downloading: {filing_url}")
        headers = {"User-Agent": SEC_USER_AGENT}
        response = requests.get(filing_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            html_content = response.text
            print(f"✅ Downloaded {len(html_content):,} characters ({len(html_content)/1024:.1f} KB)")
            return html_content
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None


def extract_oil_content(html_content: str) -> Tuple[str, str]:
    """Extract reserves and production content from HTML filing."""
    print("Parsing HTML and extracting content...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for element in soup(["script", "style", "nav", "footer", "header", "meta", "link", "noscript"]):
        element.decompose()
    
    print("✅ Cleaned HTML (removed script/style/meta tags)")
    
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} total tables")
    
    reserves_tables = []
    production_tables = []
    
    for i, table in enumerate(tables):
        if not isinstance(table, Tag):
            continue
        
        table_text = table.get_text(separator=' ', strip=True)
        
        if has_reserves_keywords(table_text) and has_numbers(table_text):
            reserves_tables.append((i, table))
        
        if has_production_keywords(table_text) and has_numbers(table_text):
            production_tables.append((i, table))
    
    print(f"✅ Found {len(reserves_tables)} reserves tables")
    print(f"✅ Found {len(production_tables)} production tables")
    
    reserves_content = []
    for i, table in reserves_tables:
        clean_table = table.get_text(separator=' | ', strip=True)
        reserves_content.append(f"[TABLE {i+1}]\n{clean_table}\n\n")
    
    production_content = []
    for i, table in production_tables:
        clean_table = table.get_text(separator=' | ', strip=True)
        production_content.append(f"[TABLE {i+1}]\n{clean_table}\n\n")
    
    all_text_elements = soup.find_all(['p', 'div', 'span', 'td', 'li', 'th'])
    print(f"📝 Searching {len(all_text_elements)} text elements")
    
    reserves_paragraphs = []
    production_paragraphs = []
    
    for elem in all_text_elements:
        if not isinstance(elem, Tag):
            continue
        
        text = elem.get_text(strip=True)
        
        if len(text) > 30:
            if has_reserves_keywords(text) and has_numbers(text):
                reserves_paragraphs.append(text)
            
            if has_production_keywords(text) and has_numbers(text):
                production_paragraphs.append(text)
    
    print(f"✅ Found {len(reserves_paragraphs)} reserves paragraphs")
    print(f"✅ Found {len(production_paragraphs)} production paragraphs")
    
    reserves_text = '\n'.join(reserves_content) + "\n\n" + "\n".join(reserves_paragraphs[:20])
    production_text = '\n'.join(production_content) + "\n\n" + "\n".join(production_paragraphs[:20])
    
    print(f"📦 Reserves content: {len(reserves_text):,} characters")
    print(f"📦 Production content: {len(production_text):,} characters")
    
    return reserves_text, production_text


def create_llm_prompt(reserves_content: str, production_content: str) -> str:
    """Create specialized LLM prompt with extracted content."""
    combined_content = f"""=== CRUDE OIL RESERVES DATA ===
{reserves_content}

=== CRUDE OIL PRODUCTION DATA ===
{production_content}
"""
    
    prompt = f"""Extract oil data from this SEC filing content. Return JSON with exact format:
{{"proved_reserves": <number>, "annual_production": <number>}}

SEARCH FOR:
1. CRUDE OIL PROVED RESERVES (barrels) - total proved reserves
2. ANNUAL CRUDE OIL PRODUCTION (barrels/year) - convert daily to annual if needed

CONVERSION RULES:
- Million barrels (MM, MMBbl) = ×1,000,000
- Billion barrels (B, BBbl) = ×1,000,000,000
- Thousand barrels/day (MBD, MBPD) = ×1,000×365 for annual
- Barrels/day (BPD, bbl/d) = ×365 for annual

Return null if not found.

SEC FILING CONTENT:
{combined_content}"""
    
    return prompt


def extract_oil_data_with_llm(filing_url: str) -> Optional[Dict[str, float]]:
    """Extract oil reserves and production data using LLM."""
    if not is_llm_available():
        print("❌ LLM not available")
        return None
    
    html_content = download_filing_html(filing_url)
    if not html_content:
        return None
    
    reserves_content, production_content = extract_oil_content(html_content)
    
    if not reserves_content.strip() and not production_content.strip():
        print("❌ Both reserves and production content are empty")
        return None
    elif not reserves_content.strip():
        print("⚠️ Reserves content is empty")
    elif not production_content.strip():
        print("⚠️ Production content is empty")
    else:
        print("✅ Both reserves and production content found")
    
    prompt = create_llm_prompt(reserves_content, production_content)
    print(f"📝 Prompt created: {len(prompt):,} characters")
    
    print("🤖 Querying LLM...")
    response = query_llm(prompt, max_tokens=500, temperature=0.0)
    
    if not response:
        print("❌ LLM query failed")
        return None
    
    print(f"✅ LLM responded with {len(response)} characters")
    print(f"LLM Response: {response}")
    
    json_data = extract_json_from_response(response, required_keys=['proved_reserves', 'annual_production'])
    
    if not json_data:
        print("❌ Failed to parse JSON from LLM response")
        return None
    
    print(f"✅ Successfully parsed JSON: {json_data}")
    
    reserves_raw = json_data.get('proved_reserves')
    production_raw = json_data.get('annual_production')
    
    try:
        reserves_val = math.nan if reserves_raw is None else float(reserves_raw)
    except (ValueError, TypeError) as e:
        print(f"❌ Error converting reserves: {e}")
        reserves_val = math.nan
    
    try:
        production_val = math.nan if production_raw is None else float(production_raw)
    except (ValueError, TypeError) as e:
        print(f"❌ Error converting production: {e}")
        production_val = math.nan
    
    result = {
        'proved_reserves': reserves_val,
        'annual_production': production_val
    }
    
    if not math.isnan(reserves_val) and not math.isnan(production_val):
        print(f"✅ SUCCESS: Reserves={reserves_val:,.0f}, Production={production_val:,.0f}")
    elif not math.isnan(reserves_val):
        print(f"⚠️ PARTIAL: Reserves={reserves_val:,.0f}, Production=N/A")
    elif not math.isnan(production_val):
        print(f"⚠️ PARTIAL: Reserves=N/A, Production={production_val:,.0f}")
    else:
        print("❌ No valid data extracted")
    
    return result


def extract_oil_data_from_filing(filing_url: str) -> Dict[str, Any]:
    """Main entry point for oil data extraction with logging."""
    log_capture = io.StringIO()
    try:
        # Capture all print output to log_capture
        with redirect_stdout(log_capture), redirect_stderr(log_capture):
            result = extract_oil_data_with_llm(filing_url)
        
        extraction_log = log_capture.getvalue()
        
        if result:
            return {
                'success': True,
                'data': result,
                'log': extraction_log
            }
        else:
            return {
                'success': False,
                'data': {'proved_reserves': math.nan, 'annual_production': math.nan},
                'log': extraction_log
            }
    except Exception as e:
        extraction_log = log_capture.getvalue()
        return {
            'success': False,
            'data': {'proved_reserves': math.nan, 'annual_production': math.nan},
            'log': extraction_log + f"\n❌ Exception: {str(e)}"
        }
