"""Dash callback handlers."""

import json
import math
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import plotly.graph_objs as go
from dash import ALL, Input, Output, State, callback_context, html, no_update

from app.config import DATA_FILE
from app.oil_extraction import extract_oil_data_from_filing
from app.sec_data import get_cik_from_ticker, get_filings_in_date_range
from app.ui_components import get_dropdown_options, render_company_table, render_filings_tabs
from app.utils import get_yahoo_info, save_company_data

@lru_cache(maxsize=128)
def get_cached_cik(ticker: str) -> Optional[str]:
    """Cache CIK lookups to avoid repeated API calls."""
    return get_cik_from_ticker(ticker)

def validate_date_range(start_date: str, end_date: str) -> bool:
    """Validate date range inputs."""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        return start <= end and (end - start).days <= 365 * 10  # Max 10 years
    except:
        return False
    
def register_callbacks(app):
    """Register all application callbacks."""

    @app.callback(
        Output('company-table-div', 'children'),
        Input('company-store', 'data'),
        prevent_initial_call=False
    )
    def update_company_table(store_data: Dict[str, Any]) -> Union[html.Div, html.Table]:
        """Update company table when store data changes."""
        try:
            companies = dict(store_data) if store_data else {}
            return render_company_table(companies)
        except Exception as e:
            print(f"Error updating company table: {e}")
            return html.Div(f"Error loading companies: {str(e)}")
        
    @app.callback(
        [Output('company-store', 'data'),
        Output('company-ticker-input', 'value'),
        Output('add-company-feedback', 'children')],
        [Input('add-company-btn', 'n_clicks'),
        Input('remove-company-btn', 'n_clicks')],
        [State('company-ticker-input', 'value'),
        State('company-store', 'data'),
        State({'type': 'company-checkbox', 'index': ALL}, 'value')],
        prevent_initial_call=True
    )
    def manage_companies(
        add_clicks: int,
        remove_clicks: int,
        ticker: str,
        store_data: Dict[str, Any],
        checkbox_values: List[List[str]]
    ) -> Tuple[Any, Any, Any]:
        """Handle adding and removing companies with enhanced error handling."""
        try:
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update, no_update
            
            triggered = ctx.triggered[0]['prop_id']
            companies = dict(store_data) if store_data else {}
            message = ""
            ticker_val = ticker if ticker else ""
            
            if "add-company-btn" in triggered and ticker:
                ticker = ticker.upper().strip()
                if ticker not in companies:
                    info = get_yahoo_info(ticker)
                    cik = get_cached_cik(ticker)
                    if info and cik:
                        info["cik"] = cik
                        companies[ticker] = {"info": info, "filings": {}}
                        save_company_data(companies, DATA_FILE)
                        message = f"✓ Added {ticker}"
                    else:
                        message = f"✗ Could not find company info for {ticker}"
                else:
                    message = f"⚠ {ticker} already exists"
                ticker_val = ""
            
            elif "remove-company-btn" in triggered:
                selected_tickers = []
                for values in checkbox_values:
                    if values:
                        selected_tickers.extend(values)
                
                for ticker_to_remove in selected_tickers:
                    if ticker_to_remove in companies:
                        companies.pop(ticker_to_remove)
                
                if selected_tickers:
                    save_company_data(companies, DATA_FILE)
                    message = f"✓ Removed {len(selected_tickers)} companies"
                else:
                    message = "⚠ No companies selected for removal"
            
            return companies, ticker_val, message
        
        except Exception as e:
            print(f"Error in manage_companies: {e}")
            return no_update, no_update, f"❌ Error: {str(e)}"
        
    @app.callback(
        [Output('company-store', 'data', allow_duplicate=True),
        Output('filings-table-div', 'children'),
        Output('filing-message', 'children')],
        [Input('company-store', 'data'),
        Input('update-filings-btn', 'n_clicks')],
        [State('filing-date-range', 'start_date'),
        State('filing-date-range', 'end_date'),
        State('filing-types-checklist', 'value')],
        prevent_initial_call=True  # CHANGED: Must be True when using allow_duplicate
    )
    def update_filings_display(store_data, n_clicks, start_date, end_date, filing_types):
        """Handle both data updates and filing button clicks."""
        try:
            ctx = callback_context
            companies = dict(store_data) if store_data else {}
            
            # Check what triggered this callback
            if not ctx.triggered:
                # This shouldn't happen with prevent_initial_call=True, but safe fallback
                return no_update, render_filings_tabs(companies), ""
            
            trigger_id = ctx.triggered[0]['prop_id']
            
            if 'company-store.data' in trigger_id:
                # Data changed - update display only
                return no_update, render_filings_tabs(companies), ""
            
            elif 'update-filings-btn.n_clicks' in trigger_id and n_clicks:
                # Button clicked - update filings data
                if not companies:
                    return no_update, render_filings_tabs(companies), "⚠️ No companies to update filings for"
                
                if not filing_types:
                    return no_update, render_filings_tabs(companies), "⚠️ Please select at least one filing type"
                
                # Validate date range
                if not validate_date_range(start_date, end_date):
                    return no_update, render_filings_tabs(companies), "⚠️ Invalid date range (max 10 years allowed)"
                
                total_new_filings = 0
                updated_companies = []
                
                print(f"🔄 Updating filings for {len(companies)} companies...")
                
                for ticker, entry in companies.items():
                    try:
                        # Use cached CIK lookup
                        cik = get_cached_cik(ticker)
                        if not cik:
                            print(f"❌ Could not find CIK for {ticker}")
                            continue
                        
                        print(f"📊 Fetching filings for {ticker} (CIK: {cik})")
                        filings_dict = get_filings_in_date_range(cik, ticker, start_date, end_date, filing_types)
                        
                        if not filings_dict:
                            print(f"⚠️ No filings found for {ticker}")
                            continue
                        
                        # Initialize filings dict if not exists
                        if 'filings' not in companies[ticker]:
                            companies[ticker]['filings'] = {}
                        
                        new_filings_count = 0
                        
                        for accession, filing_data in filings_dict.items():
                            if accession not in companies[ticker]['filings']:
                                new_filings_count += 1
                                # Preserve existing extracted data if any
                                existing_extracted_data = companies[ticker]['filings'].get(accession, {}).get('extracted_data', {})
                                
                                companies[ticker]['filings'][accession] = {
                                    'type': filing_data['type'],
                                    'filing_date': filing_data.get('filing_date', ''),
                                    'url': filing_data['url'],
                                    'accession': filing_data['accession'],
                                    'period_end': filing_data.get('period_end', ''),
                                    'extracted_data': existing_extracted_data
                                }
                        
                        if new_filings_count > 0:
                            total_new_filings += new_filings_count
                            updated_companies.append(f"{ticker} (+{new_filings_count})")
                            print(f"✅ Added {new_filings_count} new filings for {ticker}")
                            
                    except Exception as e:
                        print(f"❌ Error updating filings for {ticker}: {e}")
                        continue
                
                # Save and prepare response
                if total_new_filings > 0:
                    save_company_data(companies, DATA_FILE)
                    message = f"✅ Added {total_new_filings} new filings: {', '.join(updated_companies)}"
                else:
                    message = "ℹ️ No new filings found in the specified date range"
                
                return companies, render_filings_tabs(companies), message
            
            # Default case
            return no_update, render_filings_tabs(companies), ""
            
        except Exception as e:
            print(f"Error in update_filings_display: {e}")
            return no_update, html.Div(f"Error: {str(e)}"), f"❌ Error: {str(e)}"
        
    @app.callback(
        [Output('company-store', 'data', allow_duplicate=True),
        Output('extraction-message', 'children')],
        [Input('extract-oil-btn', 'n_clicks')],
        [State('company-store', 'data')],
        prevent_initial_call=True
    )
    def extract_oil_data_bulk(
        clicks: int,
        store_data: Dict[str, Any]
    ) -> Tuple[Any, Any]:
        """Extract oil data for all filings that don't have data yet."""
        try:
            if not clicks:
                return no_update, no_update
            
            companies = dict(store_data) if store_data else {}
            if not companies:
                return companies, "⚠ No companies to extract data for"
            
            extraction_count = 0
            failed_count = 0
            
            for ticker, entry in companies.items():
                filings = entry.get('filings', {})
                for filing_date, filing in filings.items():
                    extracted_data = filing.get('extracted_data', {})
                    
                    # Check if we already have valid data (not NaN)
                    import math
                    has_reserves = extracted_data.get('proved_reserves', 0)
                    has_production = extracted_data.get('annual_production', 0)
                    has_valid_data = (isinstance(has_reserves, (int, float)) and not math.isnan(has_reserves) and has_reserves > 0) or \
                                    (isinstance(has_production, (int, float)) and not math.isnan(has_production) and has_production > 0)
                    
                    if not has_valid_data:
                        try:
                            # extract_oil_data_from_filing returns: {'success': bool, 'data': {...}, 'log': str}
                            result = extract_oil_data_from_filing(filing.get('url', ''))
                            
                            if result and result.get('success'):
                                # Extract the actual data from the 'data' field
                                oil_data = result['data']
                                reserves = oil_data.get('proved_reserves', 0)
                                production = oil_data.get('annual_production', 0)
                                
                                companies[ticker]['filings'][filing_date]['extracted_data'] = {
                                    'proved_reserves': reserves,
                                    'annual_production': production
                                }
                                companies[ticker]['filings'][filing_date]['extraction_log'] = result.get('log', '')
                                
                                # Check if we got valid numbers (not NaN)
                                if not math.isnan(reserves) and not math.isnan(production):
                                    extraction_count += 1
                                else:
                                    failed_count += 1
                            else:
                                # Store empty data to mark as attempted
                                companies[ticker]['filings'][filing_date]['extracted_data'] = {
                                    'proved_reserves': 0,
                                    'annual_production': 0
                                }
                                companies[ticker]['filings'][filing_date]['extraction_log'] = result.get('log', '') if result else 'Extraction failed'
                                failed_count += 1
                        except Exception as e:
                            print(f"Error extracting oil data for {ticker} {filing_date}: {e}")
                            companies[ticker]['filings'][filing_date]['extraction_log'] = f"Error: {str(e)}"
                            failed_count += 1
            
            save_company_data(companies, DATA_FILE)
            
            if extraction_count > 0:
                message = f"✓ Extracted data from {extraction_count} filings"
                if failed_count > 0:
                    message += f" ({failed_count} failed)"
            else:
                message = f"⚠ No data extracted ({failed_count} filings processed)"
            
            return companies, message
            
        except Exception as e:
            print(f"Error in extract_oil_data_bulk: {e}")
            return no_update, f"❌ Error: {str(e)}"

    @app.callback(
        [Output('company-store', 'data', allow_duplicate=True),
        Output('extraction-message', 'children', allow_duplicate=True)],
        [Input({'type': 'extract-single-btn', 'ticker': ALL, 'date': ALL}, 'n_clicks')],
        [State('company-store', 'data')],
        prevent_initial_call=True
    )
    def extract_single_filing(
        clicks_list: List[int],
        store_data: Dict[str, Any]
    ) -> Tuple[Any, Any]:
        """Extract oil data from a single filing with enhanced error handling."""
        try:
            ctx = callback_context
            if not any(clicks_list) or not ctx.triggered:
                return no_update, no_update
            
            companies = dict(store_data) if store_data else {}
            
            # Parse the triggered button ID
            triggered_id = ctx.triggered[0]['prop_id']
            try:
                id_str = triggered_id.split('.')[0]
                button_id = json.loads(id_str)
                ticker = button_id['ticker']
                date = button_id['date']
            except:
                return no_update, "❌ Error parsing button ID"
            
            if ticker not in companies or date not in companies[ticker].get('filings', {}):
                return companies, f"❌ Filing not found for {ticker} on {date}"
            
            filing = companies[ticker]['filings'][date]
            filing_url = filing.get('url', '')
            
            if not filing_url:
                return companies, f"❌ No URL found for {ticker} filing on {date}"
            
            try:
                # extract_oil_data_from_filing returns: {'success': bool, 'data': {...}, 'log': str}
                result = extract_oil_data_from_filing(filing_url)
                
                if result and result.get('success'):
                    # Extract the actual data from the 'data' field
                    oil_data = result['data']
                    reserves = oil_data.get('proved_reserves', 0)
                    production = oil_data.get('annual_production', 0)
                    
                    # Store the data
                    companies[ticker]['filings'][date]['extracted_data'] = {
                        'proved_reserves': reserves,
                        'annual_production': production
                    }
                    companies[ticker]['filings'][date]['extraction_log'] = result.get('log', '')
                    save_company_data(companies, DATA_FILE)
                    
                    # Check if we actually got valid numbers (not NaN)
                    import math
                    if not math.isnan(reserves) and not math.isnan(production):
                        message = f"✅ {ticker} {date}: Reserves: {reserves:,.0f} barrels, Production: {production:,.0f} barrels/year"
                    elif not math.isnan(reserves):
                        message = f"⚠️ {ticker} {date}: Reserves: {reserves:,.0f} barrels, Production: Not found"
                    elif not math.isnan(production):
                        message = f"⚠️ {ticker} {date}: Reserves: Not found, Production: {production:,.0f} barrels/year"
                    else:
                        message = f"⚠ No oil data found in {ticker} {date} filing"
                else:
                    # Store empty data to mark as attempted
                    companies[ticker]['filings'][date]['extracted_data'] = {
                        'proved_reserves': 0,
                        'annual_production': 0
                    }
                    companies[ticker]['filings'][date]['extraction_log'] = result.get('log', '') if result else 'No data extracted'
                    save_company_data(companies, DATA_FILE)
                    message = f"⚠ No oil data found in {ticker} {date} filing"
                    
            except Exception as e:
                companies[ticker]['filings'][date]['extraction_log'] = f"Error: {str(e)}"
                message = f"❌ Error extracting from {ticker} {date}: {str(e)}"
            
            return companies, message
            
        except Exception as e:
            print(f"Error in extract_single_filing: {e}")
            return no_update, f"❌ Error: {str(e)}"

    @app.callback(
        Output('select-companies', 'options'),
        Input('company-store', 'data'),
        prevent_initial_call=False
    )
    def update_dropdown_options(store_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Update dropdown options for companies with oil data."""
        try:
            companies = dict(store_data) if store_data else {}
            return get_dropdown_options(companies)
        except Exception as e:
            print(f"Error updating dropdown options: {e}")
            return []

    @app.callback(
        Output('edgar-chart', 'figure'),
        [Input('select-companies', 'value')],
        [State('company-store', 'data')],
        prevent_initial_call=True
    )
    def plot_reserve_life_chart(
        selected: List[str],
        all_companies: Dict[str, Any]
    ) -> go.Figure:
        """Plot reserve life time series chart with enhanced error handling."""
        import math
        
        try:
            if not selected:
                return go.Figure()
            
            fig = go.Figure()
            
            for ticker in selected:
                entry = all_companies.get(ticker, {})
                filings = entry.get("filings", {})
                
                if filings:
                    data_rows = []
                    # The key is ACCESSION NUMBER, not date
                    for accession, filing in filings.items():
                        extracted = filing.get('extracted_data', {})
                        proved_reserves = extracted.get('proved_reserves', 0)
                        annual_production = extracted.get('annual_production', 0)
                        
                        # Check for valid numbers (not NaN and not 0)
                        reserves_valid = isinstance(proved_reserves, (int, float)) and \
                                    not math.isnan(proved_reserves) and proved_reserves > 0
                        production_valid = isinstance(annual_production, (int, float)) and \
                                        not math.isnan(annual_production) and annual_production > 0
                        
                        if reserves_valid and production_valid:
                            try:
                                # Get the period_end date from the filing (this is the actual report date)
                                period_end = filing.get('period_end', '')
                                if not period_end:
                                    print(f"No period_end for {ticker} {accession}")
                                    continue
                                
                                date_obj = datetime.strptime(period_end, '%Y-%m-%d')
                                reserve_life = proved_reserves / annual_production
                                filing_type = filing.get('type', 'Unknown')
                                
                                data_rows.append({
                                    'date': date_obj,
                                    'proved_reserves': proved_reserves,
                                    'annual_production': annual_production,
                                    'reserve_life': reserve_life,
                                    'filing_type': filing_type,
                                    'accession': accession
                                })
                            except Exception as e:
                                print(f"Error processing filing {ticker} {accession}: {e}")
                                continue
                    
                    if data_rows:
                        df = pd.DataFrame(data_rows).sort_values('date')
                        
                        fig.add_trace(go.Scatter(
                            x=df['date'],
                            y=df['reserve_life'],
                            name=f"{ticker} Reserve Life",
                            mode='lines+markers',
                            hovertemplate=(
                                f'{ticker}<br>'
                                'Date: %{x|%Y-%m-%d}<br>'
                                'Filing Type: %{customdata[2]}<br>'
                                'Reserve Life: %{y:.1f} years<br>'
                                'Proved Reserves: %{customdata[0]:,.0f} barrels<br>'
                                'Annual Production: %{customdata[1]:,.0f} barrels'
                                '<extra></extra>'
                            ),
                            customdata=df[['proved_reserves', 'annual_production', 'filing_type']].values,
                        ))
                    else:
                        print(f"No valid data rows for {ticker}")
            
            fig.update_layout(
                title="Reserve Life Time Series (Proved Reserves ÷ Annual Production)",
                xaxis_title="Report Period End Date",
                yaxis_title="Reserve Life (Years)",
                hovermode='closest'
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            import traceback
            traceback.print_exc()
            return go.Figure()

    @app.callback(
        [Output('log-modal', 'is_open'),
        Output('log-modal-content', 'children')],
        [Input({'type': 'log-btn', 'ticker': ALL, 'date': ALL}, 'n_clicks')],
        [State('company-store', 'data'),
        State('log-modal', 'is_open')],
        prevent_initial_call=True
    )
    def display_log_modal(
        clicks_list: List[int],
        store_data: Dict[str, Any],
        is_open: bool
    ) -> Tuple[bool, html.Div]:
        """Display extraction log in modal when log button is clicked."""
        try:
            ctx = callback_context
            if not any(clicks_list) or not ctx.triggered:
                return False, html.Div()
            
            companies = dict(store_data) if store_data else {}
            
            # Parse the triggered button ID
            triggered_id = ctx.triggered[0]['prop_id']
            try:
                id_str = triggered_id.split('.')[0]
                button_id = json.loads(id_str)
                ticker = button_id['ticker']
                date = button_id['date']
            except:
                return False, html.Div("Error parsing button ID")
            
            if ticker not in companies or date not in companies[ticker].get('filings', {}):
                return False, html.Div("Filing not found")
            
            filing = companies[ticker]['filings'][date]
            extraction_log = filing.get('extraction_log', 'No log available')
            
            # Format the log content
            log_content = html.Div([
                html.H4(f"Extraction Log - {ticker} ({date})", style={'marginBottom': '15px'}),
                html.Div([
                    html.Pre(
                        extraction_log,
                        style={
                            'backgroundColor': '#f8f9fa',
                            'padding': '15px',
                            'borderRadius': '5px',
                            'border': '1px solid #e9ecef',
                            'fontSize': '12px',
                            'fontFamily': 'monospace',
                            'whiteSpace': 'pre-wrap',
                            'maxHeight': '400px',
                            'overflowY': 'auto'
                        }
                    ),
                    html.Div([
                        html.Button(
                            "Close",
                            id="close-log-modal",
                            style={
                                'backgroundColor': '#6c757d',
                                'color': 'white',
                                'border': 'none',
                                'padding': '8px 16px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'marginTop': '15px'
                            }
                        )
                    ])
                ])
            ])
            
            return True, log_content
            
        except Exception as e:
            print(f"Error in display_log_modal: {e}")
            return False, html.Div(f"Error: {str(e)}")

    @app.callback(
        Output('log-modal', 'is_open', allow_duplicate=True),
        [Input('close-log-modal', 'n_clicks')],
        prevent_initial_call=True
    )
    def close_log_modal(n_clicks):
        """Close the log modal when close button is clicked."""
        if n_clicks:
            return False
        return no_update