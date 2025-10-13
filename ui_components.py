"""
UI Components Module - Modern, consistent styling
Contains all Dash UI rendering functions with improved design.
"""

from typing import Dict, Any, List, Union
import math
from dash import html, dcc

# Consistent button styling
BUTTON_BASE = {
    'height': '32px',
    'padding': '6px 12px',
    'fontSize': '12px',
    'fontWeight': '500',
    'border': 'none',
    'borderRadius': '4px',
    'cursor': 'pointer',
    'display': 'inline-flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'minWidth': '70px',
    'textAlign': 'center'
}

BUTTON_STYLES = {
    'extract': {
        **BUTTON_BASE,
        'backgroundColor': '#28a745',
        'color': 'white',
        'marginRight': '4px'
    },
    'extract_done': {
        **BUTTON_BASE,
        'backgroundColor': '#6c757d',
        'color': 'white',
        'marginRight': '4px'
    },
    'log': {
        **BUTTON_BASE,
        'backgroundColor': '#17a2b8',
        'color': 'white',
        'padding': '6px 8px',
        'minWidth': '60px'
    }
}

def is_nan_or_none(value) -> bool:
    """Check if value is NaN or None."""
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (ValueError, TypeError):
        return True

def render_company_table(companies: Dict[str, Any]) -> Union[html.Div, html.Table]:
    """Render company management table with modern styling."""
    if not companies:
        return html.Div(
            "No companies added yet. Add a company above to get started.",
            style={'color': '#6c757d', 'fontStyle': 'italic', 'textAlign': 'center', 'padding': '20px'}
        )

    header = html.Thead([
        html.Tr([
            html.Th("", style={'width': '40px', 'textAlign': 'center'}),
            html.Th("Ticker", style={'width': '80px', 'textAlign': 'center', 'fontWeight': '600'}),
            html.Th("Company Name", style={'textAlign': 'left', 'fontWeight': '600'})
        ], style={'backgroundColor': '#f8f9fa'})
    ])

    rows = []
    for ticker, entry in companies.items():
        rows.append(
            html.Tr([
                html.Td(
                    dcc.Checklist(
                        id={'type': 'company-checkbox', 'index': ticker},
                        options=[{'label': '', 'value': ticker}],
                        value=[],
                        style={'margin': '0'}
                    ),
                    style={'textAlign': 'center', 'padding': '8px'}
                ),
                html.Td(
                    html.Code(entry["info"]["ticker"], 
                             style={'backgroundColor': '#e9ecef', 'padding': '2px 6px', 'borderRadius': '3px'}),
                    style={'textAlign': 'center', 'padding': '8px'}
                ),
                html.Td(entry["info"]["name"], style={'textAlign': 'left', 'padding': '8px'})
            ], style={'borderBottom': '1px solid #dee2e6'})
        )

    return html.Table(
        [header, html.Tbody(rows)],
        style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'backgroundColor': 'white',
            'borderRadius': '6px',
            'overflow': 'hidden',
            'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'
        }
    )

def render_filing_tab_content(ticker: str, filings: Dict[str, Any]) -> html.Div:
    """Render filings table with consistent button styling."""
    if not filings:
        return html.Div(
            f"No filings found for {ticker}. Use 'Update Filings' to fetch data.",
            style={'color': '#6c757d', 'fontStyle': 'italic', 'padding': '20px', 'textAlign': 'center'}
        )

    # Sort filings by filing date (newest first)  
    sorted_filings = sorted(filings.items(), key=lambda x: x[1].get('filing_date', ''), reverse=True)
    rows = []

    for accession, filing in sorted_filings:  # Changed from date to accession
        filing_type = filing.get('type', 'Unknown')
        url = filing.get('url', '')
        period_end = filing.get('period_end', '')
        filing_date = filing.get('filing_date', '')  # Get actual filing date
        extracted_data = filing.get('extracted_data', {})
        extraction_log = filing.get('extraction_log', '')

        # Check if we have valid oil data (not NaN/None/0)
        reserves = extracted_data.get('proved_reserves', 0)
        production = extracted_data.get('annual_production', 0)
        has_reserves = not is_nan_or_none(reserves) and reserves > 0
        has_production = not is_nan_or_none(production) and production > 0
        has_oil_data = has_reserves or has_production

        # Extract button
        extract_btn = html.Button(
            "Extract" if not has_oil_data else "Re-extract",
            id={'type': 'extract-single-btn', 'ticker': ticker, 'date': accession},  # Use accession for id
            n_clicks=0,
            style=BUTTON_STYLES['extract'] if not has_oil_data else BUTTON_STYLES['extract_done']
        )

        # Log button (only show if there's a log)
        buttons = [extract_btn]
        if extraction_log or 'extracted_data' in filing:
            log_btn = html.Button(
                "📋 Log",
                id={'type': 'log-btn', 'ticker': ticker, 'date': accession},  # Use accession for id
                n_clicks=0,
                style=BUTTON_STYLES['log'],
                title="View extraction log"
            )
            buttons.append(log_btn)

        # Data status with better formatting
        if has_oil_data:
            status_parts = []
            if has_reserves:
                status_parts.append(f"R: {reserves:,.0f}")
            if has_production:
                status_parts.append(f"P: {production:,.0f}")
            data_status = html.Div([
                html.Span("✓", style={'color': '#28a745', 'fontSize': '16px', 'marginRight': '4px'}),
                html.Small(" | ".join(status_parts) if status_parts else "Partial data",
                          style={'color': '#6c757d'})
            ])
        else:
            data_status = html.Span("✗", style={'color': '#dc3545', 'fontSize': '16px'})

        rows.append(html.Tr([
            html.Td(filing_date, style={'fontSize': '12px', 'padding': '6px', 'fontFamily': 'monospace', 'textAlign': 'left'}),  # Show filing_date
            html.Td(period_end, style={'fontSize': '12px', 'padding': '6px', 'fontFamily': 'monospace', 'textAlign': 'left'}),
            html.Td(
                html.Span(filing_type,
                         style={'backgroundColor': '#007bff', 'color': 'white',
                               'padding': '2px 6px', 'borderRadius': '3px', 'fontSize': '11px'}),
                style={'padding': '6px', 'textAlign': 'left'}
            ),
            html.Td(
                html.A(f"View {filing_type}", href=url, target="_blank",
                      style={'color': '#007bff', 'textDecoration': 'none'}) if url else f"{filing_type} Filing",
                style={'fontSize': '12px', 'padding': '6px', 'textAlign': 'left'}
            ),
            html.Td(data_status, style={'padding': '6px', 'textAlign': 'left'}),
            html.Td(html.Div(buttons, style={'display': 'flex', 'gap': '4px'}),
                   style={'padding': '6px', 'textAlign': 'left'})
        ], style={'borderBottom': '1px solid #dee2e6'}))

    header = html.Thead([
        html.Tr([
            html.Th("Filing Date", style={'padding': '6px', 'fontWeight': '600', 'fontSize': '12px', 'textAlign': 'left'}),
            html.Th("Period End", style={'padding': '6px', 'fontWeight': '600', 'fontSize': '12px', 'textAlign': 'left'}),
            html.Th("Type", style={'padding': '6px', 'fontWeight': '600', 'fontSize': '12px', 'textAlign': 'left'}),
            html.Th("Document", style={'padding': '6px', 'fontWeight': '600', 'fontSize': '12px', 'textAlign': 'left'}),
            html.Th("Data", style={'padding': '6px', 'fontWeight': '600', 'fontSize': '12px', 'textAlign': 'left'}),
            html.Th("Actions", style={'padding': '6px', 'fontWeight': '600', 'fontSize': '12px', 'textAlign': 'left'})
        ], style={'backgroundColor': '#f8f9fa'})
    ])

    table = html.Table(
        [header, html.Tbody(rows)],
        style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'backgroundColor': 'white',
            'fontSize': '12px'
        }
    )

    return html.Div(
        table,
        style={
            'maxHeight': '400px',
            'overflowY': 'auto',
            'border': '1px solid #dee2e6',
            'borderRadius': '6px',
            'backgroundColor': 'white'
        }
    )

def render_filings_tabs(companies: Dict[str, Any]) -> Union[html.Div, dcc.Tabs]:
    """Create tabs with fixed width and modern styling."""
    if not companies:
        return html.Div(
            "No companies to show filings for.",
            style={'color': '#6c757d', 'fontStyle': 'italic', 'textAlign': 'center', 'padding': '20px'}
        )

    # Filter companies that have filings
    companies_with_filings = {k: v for k, v in companies.items() if v.get('filings')}
    
    if not companies_with_filings:
        return html.Div(
            "No filings found. Use 'Update Filings' button to fetch filings.",
            style={'color': '#6c757d', 'fontStyle': 'italic', 'textAlign': 'center', 'padding': '20px'}
        )

    tabs = []
    for ticker, entry in companies_with_filings.items():
        filing_count = len(entry.get('filings', {}))
        tabs.append(dcc.Tab(
            label=f"{ticker} ({filing_count})",
            value=ticker,
            children=[render_filing_tab_content(ticker, entry.get('filings', {}))],
            style={
                'padding': '8px 16px',
                'fontSize': '13px',
                'fontWeight': '500',
                'border': '1px solid #dee2e6',
                'borderBottom': 'none',
                'backgroundColor': 'white',
                'minWidth': '120px',  # Fixed minimum width
                'maxWidth': '200px',  # Fixed maximum width
                'textAlign': 'center'
            },
            selected_style={
                'backgroundColor': '#007bff',
                'color': 'white',
                'padding': '8px 16px',
                'fontSize': '13px',
                'fontWeight': '600',
                'border': '1px solid #007bff',
                'borderBottom': 'none',
                'minWidth': '120px',  # Same fixed width
                'maxWidth': '200px',
                'textAlign': 'center'
            }
        ))

    return dcc.Tabs(
        id="filings-tabs",
        value=list(companies_with_filings.keys())[0],
        children=tabs,
        style={'marginTop': '16px'},
        colors={
            "border": "#dee2e6",
            "primary": "#007bff",
            "background": "#f8f9fa"
        }
    )

def get_dropdown_options(companies: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate dropdown options for companies with oil data."""
    options = []
    for ticker, entry in companies.items():
        if 'filings' in entry:
            # Check if any filing has oil data (handling NaN values)
            has_oil_data = False
            for filing in entry['filings'].values():
                extracted_data = filing.get('extracted_data', {})
                reserves = extracted_data.get('proved_reserves', 0)
                production = extracted_data.get('annual_production', 0)
                
                # Check if we have valid data (not NaN/None/0)
                if not is_nan_or_none(reserves) and reserves > 0:
                    has_oil_data = True
                    break
                if not is_nan_or_none(production) and production > 0:
                    has_oil_data = True
                    break
            
            if has_oil_data:
                company_name = entry['info']['name']
                # Truncate long company names for dropdown
                if len(company_name) > 40:
                    company_name = company_name[:37] + "..."
                    
                options.append({
                    "label": f"{ticker} - {company_name}",
                    "value": ticker
                })
    
    return options
