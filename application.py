"""Oil Companies Reserve Life Tracker - Main Application."""
import dash
import dash_bootstrap_components as dbc

from app.ui_components import create_app_layout
from app.callbacks import register_callbacks

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Reserve Life Tracker"
)

application = app.server

# Set layout
app.layout = create_app_layout()

# Register all callbacks
register_callbacks(app)

if __name__ == "__main__":
    application.run(debug=True, port=8050)