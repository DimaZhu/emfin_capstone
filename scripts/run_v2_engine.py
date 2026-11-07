"""Compatibility entry point; the installable engine lives in emfin_capstone.engine."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from emfin_v2.default_run import main
if __name__ == '__main__':
    main()
