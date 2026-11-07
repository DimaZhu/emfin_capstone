"""Installed package resources, independent of repository/cwd layout."""
from pathlib import Path
import os

PACKAGE_DIR=Path(__file__).resolve().parent
RESOURCE_DIR=PACKAGE_DIR/'resources'
DATA_DIR=RESOURCE_DIR/'data'
CONFIG_DIR=RESOURCE_DIR/'configs'
# Never write to site-packages, including when installed read-only.
CACHE_DIR=Path(os.environ.get('EMFIN_V2_CACHE',str(Path.home()/'.cache/emfin-v2')))
SECRETS_FILE=Path.home()/'.config/emfin-v2/secrets.env'
