import os, sys

# beancount doesn't run from this directory
sys.path.append(os.path.dirname(__file__))

# importers located in the importers directory
from importers import ing

CONFIG = [
    ing.IngImporter(bank='INGB',rules_path=os.environ["RULES"],chars_to_replace={"é":"à","�":"é","*":" ","+":" "}),
]
