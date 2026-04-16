"""应用入口"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10041))
    app.run(host='0.0.0.0', port=port, debug=True)
