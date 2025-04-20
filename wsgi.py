import sys
import os

path = "/home/mo0hie/ai_researcher"
if path not in sys.path:
    sys.path.append(path)

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_DEBUG"] = "False"

from run import app as application
