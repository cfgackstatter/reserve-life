"""
SEC Data Operations Module

Handles SEC-related data fetching operations.
"""

from typing import List, Dict, Optional, Any
import requests
from bs4 import BeautifulSoup, Tag
from datetime import datetime
import re

from app.config import SEC_USER_AGENT, SEC_TIMEOUT

def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """Lookup CIK for a ticker symbol from SEC's ticker.txt file."""
    url_txt = "https://www.sec.gov/include/ticker.txt"
    try:
        headers = {"User-Agent": SEC_USER_AGENT}
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


def get_filings_from_search_page(cik: str, filing_type: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Scrape filings from SEC EDGAR search page."""
    search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type}&count=100"
    filings = []
    try:
        headers = {"User-Agent": SEC_USER_AGENT}
        resp = requests.get(search_url, headers=headers, timeout=SEC_TIMEOUT)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', class_='tableFile2')
        if not table or not isinstance(table, Tag):
            return []
        rows = table.find_all('tr')
        for row in rows[1:]:
            if not isinstance(row, Tag):
                continue
            cells = row.find_all('td')
            if len(cells) >= 4:
                filing_date_text = cells[3].get_text(strip=True)
                try:
                    filing_date = datetime.strptime(filing_date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                except Exception:
                    continue
                if start_date <= filing_date <= end_date:
                    desc_cell = cells[2]
                    acc_match = re.search(r'Acc-no:\s*([0-9-]+)', desc_cell.get_text())
                    if acc_match:
                        accession = acc_match.group(1)
                        filings.append({
                            'accession': accession,
                            'filing_date': filing_date,
                            'type': filing_type
                        })
        return filings
    except Exception as e:
        print(f"❌ Error fetching filings: {e}")
        return []


def get_filing_details_from_index(cik: str, accession: str, ticker: str) -> Optional[Dict[str, Any]]:
    """Extract filing details from SEC index page."""
    accession_no_dashes = accession.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{accession}-index.htm"
    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        resp = requests.get(index_url, headers=headers, timeout=SEC_TIMEOUT)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        period_end = None
        info_heads: list[Tag] = soup.find_all("div", class_="infoHead")
        for div in info_heads:
            if div.string and re.search(r"Period of Report", div.string, re.IGNORECASE):
                sib = div.find_next_sibling("div", class_="info")
                if sib:
                    period_end = sib.get_text(strip=True)
                break
        document_name = None
        document_url = None
        tables = soup.find_all('table')
        for table in tables:
            if not isinstance(table, Tag):
                continue
            rows = table.find_all('tr')
            header_idx_doc, header_idx_type = None, None
            for row in rows:
                if not isinstance(row, Tag):
                    continue
                header_cells = row.find_all('th')
                if header_cells:
                    for idx, th in enumerate(header_cells):
                        txt = th.get_text(strip=True).lower()
                        if txt == 'document':
                            header_idx_doc = idx
                        if txt == 'type':
                            header_idx_type = idx
                    continue
                data_cells = row.find_all('td')
                if (header_idx_doc is not None and header_idx_type is not None and len(data_cells) > max(header_idx_doc, header_idx_type)):
                    doc_cell = data_cells[header_idx_doc]
                    type_text = data_cells[header_idx_type].get_text(strip=True)
                    if type_text == '10-K':
                        if isinstance(doc_cell, Tag):
                            link = next((child for child in doc_cell.children if isinstance(child, Tag) and child.name == 'a'), None)
                        else:
                            link = None
                        if link and link.has_attr("href"):
                            document_name = link.get_text(strip=True)
                            href_url = str(link.get("href", ""))
                            if href_url.startswith('/ix?doc='):
                                href_url = href_url.replace('/ix?doc=', '', 1)
                            document_url = f"https://www.sec.gov{href_url}" if href_url.startswith('/') else href_url
                        else:
                            doc_text = doc_cell.get_text(strip=True) if isinstance(doc_cell, Tag) else str(doc_cell)
                            if '.htm' in doc_text:
                                document_name = doc_text.split('.htm')[0] + '.htm'
                            else:
                                document_name = doc_text.split()[0] if doc_text else None
                            document_url = None
                        break
            if document_name:
                break
        if period_end and document_name:
            if not document_url:
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{document_name}"
            else:
                filing_url = document_url
            return {
                'period_end': period_end,
                'url': filing_url,
                'document_name': document_name
            }
        return None
    except Exception as e:
        print(f"❌ Error fetching index: {e}")
        return None


def get_filings_in_date_range(cik: str, ticker: str, start_date: str, end_date: str, filing_types: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Retrieve all filings of given types in date range."""
    if filing_types is None:
        filing_types = ['10-K', '10-Q']
    filings_dict: Dict[str, Dict[str, Any]] = {}
    for filing_type in filing_types:
        filings = get_filings_from_search_page(cik, filing_type, start_date, end_date)
        for filing in filings:
            accession = filing['accession']
            if accession not in filings_dict:
                details = get_filing_details_from_index(cik, accession, ticker)
                if details:
                    filings_dict[accession] = {
                        'type': filing['type'],
                        'filing_date': filing['filing_date'],
                        'period_end': details['period_end'],
                        'url': details['url'],
                        'accession': accession
                    }
    return filings_dict
