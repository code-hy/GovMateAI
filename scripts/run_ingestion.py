import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ingestion.pipeline import run_ingestion

if __name__ == "__main__":
    print("Starting Ingestion Pipeline...")
    run_ingestion()
