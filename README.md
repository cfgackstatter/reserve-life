# Oil Companies Reserve Life Tracker

A Dash web application for tracking oil company reserve life ratios by analyzing SEC filings.

## Features

- **Company Management**: Add/remove oil companies by ticker symbol
- **Filing Retrieval**: Fetch 10-K and 10-Q filings from SEC EDGAR database
- **Data Extraction**: Extract proved reserves and production data from filings
- **Reserve Life Analysis**: Calculate and visualize reserve life trends over time

## Quick Start

1. **Clone and install**
```console
git clone https://github.com/cfgackstatter/reserve-life.git
cd reserve-life
pip install -r requirements.txt
```

2. **Run the app**
```console
python app.py
```

3. **Open your browser** to `http://localhost:8050`

## Usage

1. **Add Companies**: Enter ticker symbols (e.g., XOM, CVX) to add oil companies
2. **Update Filings**: Select date range and filing types, then fetch filings for all companies
3. **Extract Data**: Run oil data extraction on new filings (currently uses dummy data)
4. **Analyze**: View reserve life trends in the interactive chart

## Project Structure
```console
reserve-life/
├── app.py # Main Dash application
├── utils.py # Utility functions for data fetching
├── assets/
│ └── style.css # Custom CSS styling
├── requirements.txt # Python dependencies
└── README.md # This file
```

## Data Sources

- **Company Info**: Yahoo Finance API via yfinance
- **SEC Filings**: SEC EDGAR database
- **Reserve Data**: Extracted from 10-K/10-Q filings (extraction logic TBD)

## Development Status

🚧 **Work in Progress** - Currently uses dummy data for oil reserves/production extraction. Real extraction logic will be implemented using regex/HTML parsing or LLM-based approaches.

## License

MIT License
