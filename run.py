"""Application entry point."""
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"Starting Hotel & Restaurant Management Server on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=debug)
