import dash
from dash import html, dcc, Input, Output, State, callback_context
import plotly.graph_objs as go
import pandas as pd
import json
import os
from datetime import datetime, timedelta

from utils import (
    get_yahoo_info, get_cik_from_ticker, get_filings_in_date_range, extract_oil_data_from_10k
)

DATA_FILE = "company_data.json"

def load_json_file():
    """Load companies from the local JSON file."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_json_file(data):
    """Save companies and their data to the local JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def render_company_table(companies):
    """Render the company table with checkboxes for selection."""
    if not companies:
        return html.Div("No companies added yet.", style={'color': '#666'})
    
    header = html.Tr([
        html.Th("Select", style={'width': '80px'}), 
        html.Th("Ticker", style={'width': '80px'}), 
        html.Th("Name")
    ])
    rows = []
    for ticker, entry in companies.items():
        rows.append(
            html.Tr([
                html.Td(dcc.Checklist(
                    id={'type': 'company-checkbox', 'index': ticker},
                    options=[{'label': '', 'value': ticker}],
                    value=[],
                    style={'margin': '0'}
                )),
                html.Td(entry["info"]["ticker"]),
                html.Td(entry["info"]["name"]),
            ])
        )
    return html.Table([header] + rows, className="custom-table", 
                     style={'width': '100%', 'fontSize': '14px'})

def render_filing_tab_content(ticker, filings):
    """Render filings table for a single company in a tab."""
    if not filings:
        return html.Div("No filings for this company.", style={'color': '#666', 'padding': '10px'})
    
    rows = []
    for date, filing in sorted(filings.items(), reverse=True):
        year = date[:4]
        filing_type = filing.get('type', 'Unknown')
        url = filing.get('url', '')
        has_oil_data = bool(filing.get('extracted_data', {}).get('proved_reserves'))
        
        rows.append(html.Tr([
            html.Td(date, style={'fontSize': '12px'}),
            html.Td(filing_type, style={'fontSize': '12px'}),
            html.Td(html.A(f"{year} {filing_type}", href=url, target="_blank", 
                          style={'textDecoration': 'none', 'color': '#0066cc'}) if url else f"{year} {filing_type}",
                   style={'fontSize': '12px'}),
            html.Td("✓" if has_oil_data else "✗", 
                   style={'color': 'green' if has_oil_data else 'red', 'textAlign': 'center'})
        ]))
    
    header = html.Tr([
        html.Th("Date", style={'fontSize': '12px', 'padding': '5px'}),
        html.Th("Type", style={'fontSize': '12px', 'padding': '5px'}),
        html.Th("Link", style={'fontSize': '12px', 'padding': '5px'}),
        html.Th("Data", style={'fontSize': '12px', 'padding': '5px', 'textAlign': 'center'})
    ])
    
    table = html.Table([header] + rows, 
                      style={'width': '100%', 'fontSize': '12px'})
    
    return html.Div([
        table
    ], style={
        'height': '200px', 
        'overflowY': 'auto', 
        'border': '1px solid #ddd',
        'padding': '10px',
        'backgroundColor': 'white'
    })

def render_filings_tabs(companies):
    """Create tabs for each company showing their filings."""
    if not companies:
        return html.Div("No companies to show filings for.", style={'color': '#666'})
    
    # Filter companies that have filings
    companies_with_filings = {k: v for k, v in companies.items() if v.get('filings')}
    
    if not companies_with_filings:
        return html.Div("No filings found. Use 'Update Filings' button to fetch filings.", style={'color': '#666'})
    
    tabs = []
    for ticker, entry in companies_with_filings.items():
        tabs.append(dcc.Tab(
            label=f"{ticker} ({len(entry.get('filings', {}))})",
            value=ticker,
            children=[render_filing_tab_content(ticker, entry.get('filings', {}))],
            style={'padding': '6px 12px', 'fontSize': '13px'},
            selected_style={'backgroundColor': '#119DFF', 'color': 'white', 'padding': '6px 12px'}
        ))
    
    return dcc.Tabs(
        id="filings-tabs",
        value=list(companies_with_filings.keys())[0],
        children=tabs,
        style={'height': '35px'}
    )

def get_dropdown_options(companies):
    """Generate dropdown options for companies with oil data."""
    options = []
    for ticker, entry in companies.items():
        if 'filings' in entry:
            has_oil_data = any(
                filing.get('extracted_data', {}).get('proved_reserves', 0) > 0
                for filing in entry['filings'].values()
            )
            if has_oil_data:
                options.append({
                    "label": f"{entry['info']['ticker']} - {entry['info']['name']}", 
                    "value": ticker
                })
    return options

app = dash.Dash(__name__)
server = app.server

# Default date range (last 5 years)
default_start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
default_end_date = datetime.now().strftime('%Y-%m-%d')

app.layout = html.Div([
    html.H1("Oil Companies Reserve Life Tracker", style={'marginBottom': '20px'}),
    dcc.Store(id='company-store', data=load_json_file(), storage_type='local'),
    
    # Section 1: Manage Companies
    html.Div([
        html.H3("Manage Companies", style={'marginBottom': '10px'}),
        html.Div([
            dcc.Input(id='ticker-input', type='text', placeholder='Enter ticker (e.g. XOM)', 
                     debounce=True, style={'marginRight': '8px'}),
            html.Button('Add Company', id='add-btn', n_clicks=0, 
                       style={'marginRight': '8px'}),
            html.Button('Remove Selected', id='remove-btn', n_clicks=0, 
                       style={'backgroundColor': '#dc3545', 'color': 'white', 'border': 'none'}),
        ], style={'marginBottom': '10px'}),
        
        html.Div(id='company-table-div'),
        html.Div(id='company-message', style={'color': 'blue', 'fontSize': '13px', 'margin': '5px 0'}),
    ], style={'marginBottom': '20px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
    
    # Section 2: Update Filings
    html.Div([
        html.H3("Update Filings", style={'marginBottom': '10px'}),
        html.Div([
            html.Div([
                html.Label("Date Range:", style={'fontSize': '13px', 'marginRight': '10px'}),
                dcc.DatePickerRange(
                    id='filing-date-range',
                    start_date=default_start_date,
                    end_date=default_end_date,
                    display_format='YYYY-MM-DD',
                    style={'fontSize': '12px'}
                ),
            ], style={'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label("Types:", style={'fontSize': '13px', 'marginRight': '10px'}),
                dcc.Checklist(
                    id='filing-types-checklist',
                    options=[
                        {'label': '10-K', 'value': '10-K'},
                        {'label': '10-Q', 'value': '10-Q'}
                    ],
                    value=['10-K', '10-Q'],
                    inline=True,
                    style={'fontSize': '13px'}
                )
            ], style={'display': 'inline-block'}),
        ], style={'marginBottom': '10px'}),
        
        html.Button('Update Filings for All Companies', id='update-filings-btn', n_clicks=0,
                   style={'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 
                         'padding': '8px 16px', 'marginBottom': '10px'}),
        
        html.Div(id='filings-table-div'),
        html.Div(id='filing-message', style={'color': 'blue', 'fontSize': '13px', 'margin': '5px 0'}),
    ], style={'marginBottom': '20px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
    
    # Section 3: Extract Oil Data
    html.Div([
        html.H3("Extract Oil Data", style={'marginBottom': '10px'}),
        html.P("Extract oil reserves and production data from filings that don't have data yet.", 
               style={'fontSize': '13px', 'color': '#666', 'marginBottom': '10px'}),
        html.Button('Extract Oil Data for New Filings', id='extract-oil-btn', n_clicks=0,
                   style={'backgroundColor': '#ffc107', 'color': 'black', 'border': 'none', 'padding': '8px 16px'}),
        html.Div(id='extraction-message', style={'color': 'blue', 'fontSize': '13px', 'margin': '5px 0'}),
    ], style={'marginBottom': '20px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
    
    # Section 4: Reserve Life Chart
    html.Div([
        html.H3("Reserve Life Analysis", style={'marginBottom': '10px'}),
        dcc.Dropdown(id='select-companies', multi=True, placeholder="Select companies to visualize",
                    style={'marginBottom': '10px'}),
        dcc.Graph(id='edgar-chart'),
    ], style={'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
])

# Company table callback
@app.callback(
    Output('company-table-div', 'children'),
    Input('company-store', 'data'),
    prevent_initial_call=False
)
def update_company_table(store_data):
    """Update company table when store data changes."""
    companies = dict(store_data) if store_data else {}
    return render_company_table(companies)

# Filings tabs callback
@app.callback(
    Output('filings-table-div', 'children'),
    Input('company-store', 'data'),
    prevent_initial_call=False
)
def update_filings_tabs(store_data):
    """Update filings tabs when store data changes."""
    companies = dict(store_data) if store_data else {}
    return render_filings_tabs(companies)

# Main callback for company management
@app.callback(
    [Output('company-store', 'data'),
     Output('ticker-input', 'value'),
     Output('company-message', 'children')],
    [Input('add-btn', 'n_clicks'),
     Input('remove-btn', 'n_clicks')],
    [State('ticker-input', 'value'),
     State('company-store', 'data'),
     State({'type': 'company-checkbox', 'index': dash.ALL}, 'value')],
    prevent_initial_call=True
)
def manage_companies(add_clicks, remove_clicks, ticker, store_data, checkbox_values):
    """Handle adding and removing companies."""
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
    
    triggered = ctx.triggered[0]['prop_id']
    companies = dict(store_data) if store_data else {}
    message = ""
    ticker_val = ticker if ticker else ""
    
    if "add-btn" in triggered and ticker:
        ticker = ticker.upper()
        if ticker not in companies:
            info = get_yahoo_info(ticker)
            cik = get_cik_from_ticker(ticker)
            if info and cik:
                info["cik"] = cik
                companies[ticker] = {"info": info, "filings": {}}
                save_json_file(companies)
                message = f"✓ Added {ticker}"
            else:
                message = f"✗ Could not find company info for {ticker}"
        else:
            message = f"⚠ {ticker} already exists"
        ticker_val = ""
    
    elif "remove-btn" in triggered:
        selected_tickers = []
        for i, values in enumerate(checkbox_values):
            if values:
                selected_tickers.extend(values)
        
        for ticker_to_remove in selected_tickers:
            if ticker_to_remove in companies:
                companies.pop(ticker_to_remove)
        
        if selected_tickers:
            save_json_file(companies)
            message = f"✓ Removed {len(selected_tickers)} companies"
        else:
            message = "⚠ No companies selected for removal"
    
    return companies, ticker_val, message

# Filings update callback
@app.callback(
    [Output('company-store', 'data', allow_duplicate=True),
     Output('filing-message', 'children')],
    [Input('update-filings-btn', 'n_clicks')],
    [State('company-store', 'data'),
     State('filing-date-range', 'start_date'),
     State('filing-date-range', 'end_date'),
     State('filing-types-checklist', 'value')],
    prevent_initial_call=True
)
def update_filings(clicks, store_data, start_date, end_date, filing_types):
    """Update filings for all companies."""
    if not clicks:
        return dash.no_update, dash.no_update
    
    companies = dict(store_data) if store_data else {}
    if not companies:
        return companies, "⚠ No companies to update filings for"
    
    total_filings = 0
    for ticker, entry in companies.items():
        if 'info' in entry and 'cik' in entry['info']:
            try:
                filings_list = get_filings_in_date_range(
                    entry['info']['cik'], start_date, end_date, filing_types or ['10-K']
                )
                for filing in filings_list:
                    companies[ticker]['filings'][filing['date']] = {
                        'type': filing['type'],
                        'url': filing['html_url'],
                        'accession': filing['accession'],
                        'primary_document': filing['primary_document'],
                        'extracted_data': companies[ticker]['filings'].get(filing['date'], {}).get('extracted_data', {})
                    }
                total_filings += len(filings_list)
            except Exception as e:
                print(f"Error fetching filings for {ticker}: {e}")
    
    save_json_file(companies)
    return companies, f"✓ Updated {total_filings} filings for {len(companies)} companies"

# Extract oil data callback
@app.callback(
    [Output('company-store', 'data', allow_duplicate=True),
     Output('extraction-message', 'children')],
    [Input('extract-oil-btn', 'n_clicks')],
    [State('company-store', 'data')],
    prevent_initial_call=True
)
def extract_oil_data(clicks, store_data):
    """Extract oil data for filings that don't have data yet."""
    if not clicks:
        return dash.no_update, dash.no_update
    
    companies = dict(store_data) if store_data else {}
    if not companies:
        return companies, "⚠ No companies to extract data for"
    
    extraction_count = 0
    for ticker, entry in companies.items():
        filings = entry.get('filings', {})
        for filing_date, filing in filings.items():
            if not filing.get('extracted_data') or not filing['extracted_data'].get('proved_reserves'):
                try:
                    oil_data = extract_oil_data_from_10k(filing.get('url', ''))
                    if oil_data:
                        companies[ticker]['filings'][filing_date]['extracted_data'] = oil_data
                        extraction_count += 1
                except Exception as e:
                    print(f"Error extracting oil data for {ticker} {filing_date}: {e}")
    
    save_json_file(companies)
    return companies, f"✓ Extracted oil data from {extraction_count} new filings"

# Chart callback
@app.callback(
    Output('select-companies', 'options'),
    Input('company-store', 'data'),
    prevent_initial_call=False
)
def update_dropdown_options(store_data):
    """Update dropdown options for companies with oil data."""
    companies = dict(store_data) if store_data else {}
    return get_dropdown_options(companies)

@app.callback(
    Output('edgar-chart', 'figure'),
    [Input('select-companies', 'value')],
    [State('company-store', 'data')],
    prevent_initial_call=True
)
def plot_reserve_life_chart(selected, all_companies):
    """Plot reserve life time series chart using new data structure."""
    if not selected:
        return go.Figure()
    
    fig = go.Figure()
    
    for ticker in selected:
        entry = all_companies.get(ticker, {})
        filings = entry.get("filings", {})
        
        if filings:
            data_rows = []
            for filing_date, filing in filings.items():
                extracted = filing.get('extracted_data', {})
                if extracted.get('proved_reserves') and extracted.get('annual_production'):
                    try:
                        date_obj = datetime.strptime(filing_date, '%Y-%m-%d')
                        proved = extracted['proved_reserves']
                        production = extracted['annual_production']
                        reserve_life = proved / production if production > 0 else 0
                        filing_type = filing.get('type', 'Unknown')
                        
                        data_rows.append({
                            'date': date_obj,
                            'proved_reserves': proved,
                            'annual_production': production,
                            'reserve_life': reserve_life,
                            'filing_type': filing_type
                        })
                    except Exception:
                        continue
            
            if data_rows:
                df = pd.DataFrame(data_rows).sort_values('date')
                
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['reserve_life'],
                    name=f"{ticker} Reserve Life",
                    mode='lines+markers',
                    hovertemplate=(
                        f'<b>{ticker}</b><br>'
                        'Date: %{x|%Y-%m-%d}<br>'
                        'Filing Type: %{customdata[2]}<br>'
                        'Reserve Life: %{y:.1f} years<br>'
                        'Proved Reserves: %{customdata[0]:,.0f} barrels<br>'
                        'Annual Production: %{customdata[1]:,.0f} barrels<br>'
                        '<extra></extra>'
                    ),
                    customdata=df[['proved_reserves', 'annual_production', 'filing_type']].values,
                ))
    
    fig.update_layout(
        title="Reserve Life Time Series (Proved Reserves ÷ Annual Production)",
        xaxis_title="Filing Date",
        yaxis_title="Reserve Life (Years)",
        hovermode='closest'
    )
    
    return fig

if __name__ == "__main__":
    app.run(debug=True)
