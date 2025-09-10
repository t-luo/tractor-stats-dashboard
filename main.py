#!/usr/bin/env python3
"""
Main entry point for TractorStats application.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app module to register routes
import src.app

# Import ui from nicegui and start the server
from nicegui import ui

if __name__ == "__main__":
    # Use environment port or default to 7860
    port = int(os.environ.get("PORT", 7860))
    
    ui.run(
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        show=False     # Don't try to open browser in cloud
    )