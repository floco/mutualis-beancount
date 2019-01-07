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
    # TODO: deal with REVO's "Paid Out (EUR)"
    csv_importer.CsvImporter(bank='REVO',rules_path=os.environ["RULES"],chars_to_replace={"�":""}, column_titles=['Completed Date', 'Paid Out|Paid In', '', 'Reference', 'Category', 'Category'], skip=['Payment from Julien Coupard.*','Payment from M Et Mme Julien Coupard.*'], date_format='%Y %B %d', locale='fr_FR'),
    csv_importer.CsvImporter(bank='KEYT',rules_path=os.environ["RULES"],chars_to_replace={"�":"", "*":" ", "+":" "}, column_titles=['Date', 'Montant', 'Devise', 'Description', 'Compte', 'Compte'], skip=[], date_format='%d.%m.%Y', locale='fr_FR'),
    csv_importer.CsvImporter(bank='RABO',rules_path=os.environ["RULES"],chars_to_replace={"�":"é", "*":" ", "+":" "}, column_titles=['Date op', 'Montant', 'Devise', 'Type op', 'Compte contrepartie', 'Communication partie 1'], skip=[], date_format='%d/%m/%Y', locale='fr_FR'),
    csv_importer.CsvImporter(bank='INGB',rules_path=os.environ["RULES"],chars_to_replace={"�":"é", "*":" ", "+":" "}, column_titles=['Date comptable', 'Montant', 'Devise', 'Libellés', 'Détails du mouvement', 'Compte partie adverse'], skip=[], date_format='%d/%m/%Y', locale='fr_FR'),
]
