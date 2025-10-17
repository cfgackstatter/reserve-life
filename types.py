"""Type definitions for the application."""
from typing import TypedDict, Dict, Optional

class CompanyInfo(TypedDict):
    ticker: str
    name: str
    cik: str

class ExtractedData(TypedDict):
    proved_reserves: Optional[float]
    annual_production: Optional[float]

class FilingData(TypedDict):
    type: str
    filing_date: str
    url: str
    accession: str
    period_end: Optional[str]
    extracted_data: Optional[ExtractedData]
    extraction_log: str

class CompanyData(TypedDict):
    info: CompanyInfo
    filings: Dict[str, FilingData]
