"""Installed command entry point. Existing flags remain backward compatible."""
def main():
    from emfin_capstone.engine import main as run
    run()
