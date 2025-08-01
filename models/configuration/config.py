"""
Important pathways configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # This points to project root

# Main directories
TEMPLATE_FOLDER_PATH = os.path.join(BASE_DIR, 'template')
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'maintenance_skills.db')}"

# File processing paths
TRAINING_PLANS_CSV = os.path.join(BASE_DIR, 'merged_training_plans.csv')
TRAINING_PLANS_XLSX = os.path.join(BASE_DIR, 'database', 'loadsheets', 'merged_training_plans1.xlsx')
SKILLS_MATRIX = os.path.join(BASE_DIR, 'database', 'loadsheets', 'skills_matrix.xlsx')
# Configuration settings
COPY_FILES = False
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'xlsx', 'csv'}  # Allowed file extensions