"""
Configure here all the importers you need
"""
import os, sys

# if using smart importer
from smart_importer.predict_postings import PredictPostings
from smart_importer.predict_payees import PredictPayees

# beancount doesn't run from this directory
sys.path.append(os.path.dirname(__file__))

# importers located in the importers directory
from importers import csv_importer

# csv_importer = PredictPostings(suggest_accounts=False)(CsvImporter)
CONFIG = [
    csv_importer.CsvImporter(bank='INGB',rules_path=os.environ["RULES"],chars_to_replace={"é":"à", "�":"é", "*":" ", "+":" "}, column_titles=['Date comptable', 'Montant', 'Devise', 'Libell�s', 'D�tails du mouvement'], skip=['Souscription.*']),
    csv_importer.CsvImporter(bank='KEYT',rules_path=os.environ["RULES"],chars_to_replace={"�":"", "*":" ", "+":" "}, column_titles=['Date', 'Montant', 'Devise', 'Description', 'Compte'], skip=['Souscription.*']),
]
