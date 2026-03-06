import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from f1watch.api.premier_league_handler import lambda_handler

