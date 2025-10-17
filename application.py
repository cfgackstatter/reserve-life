"""
Oil Companies Reserve Life Tracker - Main Application

A Dash web application for tracking oil company reserve life ratios.
"""

import dash
from dash import html, dcc, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Union, Optional
from functools import lru_cache

# Import custom modules
from utils import get_yahoo_info, load_company_data, save_company_data
from sec_data import get_cik_from_ticker, get_filings_in_date_range
from oil_extraction import extract_oil_data_from_filing
from ui_components import (
    render_company_table,
    render_filings_tabs,
    get_dropdown_options
)

# Configuration
DATA_FILE = "company_data.json"
DEFAULT_YEARS_BACK = 5

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__,
               external_stylesheets=[dbc.themes.BOOTSTRAP],
               suppress_callback_exceptions=True)
application = app.server

app.layout = create_app_layout()

if __name__ == "__main__":
    application.run(debug=True)