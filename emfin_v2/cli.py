"""Installed command entry point. Existing flags remain backward compatible."""
def main():
    from emfin_v2.default_run import main as run
    run()
