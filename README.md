# Oil Companies Reserve Life Tracker

A Dash web application for tracking and analyzing oil company reserve life ratios using SEC EDGAR filings and AI-powered data extraction.

## Features

### 📊 Automated Data Collection
- **SEC EDGAR Integration**: Automatically fetches 10-K and 10-Q filings for oil companies
- **Yahoo Finance**: Retrieves current stock prices and company information
- **Date Range Selection**: Configurable historical data retrieval (default: 5 years)

### 🤖 AI-Powered Data Extraction
- **LLM-Based Extraction**: Uses Perplexity AI to automatically extract:
  - Proved crude oil reserves (barrels)
  - Annual crude oil production (barrels/year)
- **Intelligent Parsing**: Automatically identifies and extracts data from:
  - SEC filing tables
  - Text paragraphs containing oil data
  - Various data formats and units
- **Detailed Logging**: Full extraction logs for debugging and transparency

### 📈 Interactive Visualization
- **Time Series Charts**: Plot reserve life trends across multiple companies
- **Company Comparison**: Select and compare multiple oil companies
- **Reserve Life Calculation**: Automatically calculates years of reserves remaining

### 💾 Data Management
- **Persistent Storage**: Company data saved locally in JSON format
- **Add/Remove Companies**: Easy management of tracked companies
- **Bulk Extraction**: Extract data from multiple filings simultaneously
- **Single Filing Extraction**: Target specific filings for extraction

## Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup

1. **Clone the repository**
```console
git clone <your-repo-url>
cd oil-reserve-tracker
```

2. **Install dependencies**
```console
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file in the project root:
```console
PERPLEXITY_API_KEY=your_api_key_here
```

Get your API key from [Perplexity AI](https://www.perplexity.ai/)

4. **Run the application**
```console
python app.py
```

5. **Open in browser**
Navigate to `http://localhost:8050`

## Usage

### Adding a Company

1. Enter a stock ticker symbol (e.g., XOM, CVX, COP)
2. Click "Add Company"
3. Wait for SEC filings to be fetched
4. View filings in the "Filings" tab

### Extracting Oil Data

**Single Filing:**
1. Navigate to the "Filings" tab
2. Find the desired filing
3. Click "Extract" next to the filing
4. View extraction status and results

**Bulk Extraction:**
1. Click "Extract All" under a company's filings
2. Monitor progress messages
3. Review extraction logs for each filing

### Viewing Reserve Life Trends

1. Select one or more companies from the dropdown
2. Click "Plot Reserve Life"
3. Interactive chart displays reserve life over time
4. Hover over data points for detailed information

## Project Structure
```console
oil-reserve-tracker/
├── app.py # Main Dash application
├── sec_data.py # SEC EDGAR data fetching
├── oil_extraction.py # AI-powered data extraction
├── llm_client.py # Perplexity AI integration
├── ui_components.py # UI rendering components
├── utils.py # Utility functions
├── company_data.json # Persistent data storage
├── requirements.txt # Python dependencies
├── .env # Environment variables (create this)
└── README.md
```

## How It Works

### Data Extraction Process

1. **HTML Download**: Fetches complete SEC filing HTML
2. **Content Parsing**: Uses BeautifulSoup to clean and parse HTML
3. **Keyword Matching**: Identifies tables and text containing oil data
4. **LLM Processing**: Sends relevant content to Perplexity AI
5. **JSON Extraction**: Parses structured data from LLM response
6. **Unit Conversion**: Converts various units to standard barrels
7. **Storage**: Saves extracted data with detailed logs

### Reserve Life Calculation
```console
Reserve Life (years) = Proved Reserves (barrels) / Annual Production (barrels/year)
```

## Configuration

### Date Range
Modify `DEFAULT_YEARS_BACK` in `app.py`:

```console
DEFAULT_YEARS_BACK = 5 # Change to desired number of years
```

### SEC User Agent
Update `SEC_USER_AGENT` in `sec_data.py` and `oil_extraction.py`:

```console
SEC_USER_AGENT = "your_email@example.com"
```

### LLM Settings
Adjust in `oil_extraction.py`:

```console
response = query_llm(prompt, max_tokens=500, temperature=0.0)
```

## Limitations

- **LLM Dependency**: Requires active Perplexity AI API key
- **Data Accuracy**: Extraction accuracy depends on filing format consistency
- **Rate Limits**: SEC EDGAR has rate limiting (10 requests/second)
- **Manual Verification**: Always verify extracted data against original filings

## Troubleshooting

### "LLM not available"
- Check that `PERPLEXITY_API_KEY` is set in `.env`
- Verify API key is valid
- Ensure `perplexity-python` package is installed

### Empty extraction logs
- Check console output for errors
- Verify filing URL is accessible
- Review extraction log in filing details

### Chart not displaying
- Ensure at least one company has extracted data
- Check that both reserves and production are non-zero
- Verify `period_end` dates exist in filing data

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this project for any purpose.

## Acknowledgments

- **SEC EDGAR**: For providing free access to company filings
- **Perplexity AI**: For LLM-powered data extraction
- **Plotly Dash**: For the interactive web framework