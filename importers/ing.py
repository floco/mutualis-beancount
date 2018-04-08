from beancount.core.number import D
from beancount.ingest import importer
from beancount.core import account
from beancount.core import amount
from beancount.core import flags
from beancount.core import data
from beancount.core.position import Cost

from dateutil.parser import parse

#from titlecase import titlecase

import csv
import yaml
import os
import re

from smart_importer.predict_postings import PredictPostings
from smart_importer.predict_payees import PredictPayees

import logging
LOG_LEVEL = logging.DEBUG
logging.basicConfig(format='%(message)s', level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# colorize the log output if the coloredlogs package is available
try:
    import coloredlogs
except ImportError as e:
    coloredlogs = None
if coloredlogs:
    coloredlogs.install(level=LOG_LEVEL)

class BankException(Exception):
    "Exception for Bank beancount importer"

# make this a more generic bank importer
class IngImporter(importer.ImporterProtocol):
    # @PredictPostings(training_data=os.environ["TRAINING_DATA"])
    # @PredictPayees(training_data=os.environ["TRAINING_DATA"])

    def __init__(self, account, rules_path):
        self.account = account
        self.rules_path = rules_path
        self.rules = []
        self.new_payees = {}

    def name(self):
        return('IngImporter')

    def identify(self, f):
        bank = os.path.basename(os.path.dirname(f.name))
        account = os.path.basename(f.name)
        if not re.match('INGB', bank):
            logging.info('Ignored: %s %s',bank,account)
            return False
        self.account = "Assets:"+bank+":"+account
        logging.info('Processing: %s %s',bank,account)
        return True

    def _import_rules(self):
        with open(os.path.expanduser(self.rules_path), 'r') as f:
            for index, row in enumerate(csv.DictReader(f,delimiter=';',fieldnames=['payee','account','desc','amount','currency'])):
                self.rules.append(row)

    def _guess_account_from_payee(self, payee, info):
        for rule in self.rules:
            #logging.info('Rule: %s Regex: %s',rule, ".*"+rule['payee']+".*")
            if re.match(".*"+payee+".*", rule['payee']):
                return rule
        # if we parsed all rules and not found any match, then we add the payee in the new payee dict
        if payee not in self.new_payees:
            self.new_payees.update({payee:info})
        #raise BankException('RuleNotFound')

    def find_payee(self, trans_desc):
        section = " ".join(trans_desc[80:160].split()) 
        if section.count(',') > 1:
            return section.split(",")[0]
        elif section.count('-') > 3:
            return section.split("-")[2]+section.split("-")[3]
        elif section.count('-') > 2:
            return section.split("-")[2]
        else:
            return section

    def extract(self, f):
        self._import_rules()
        entries = []
        accounts = {}

        #opn = data.Optional(meta=meta,date=parse("01/01/2000").date(),account=trans_acc,currencies=[trans_cur],booking=None)
        #entries.append(opn)

        with open(f.name) as f:

            for index, row in enumerate(csv.DictReader(f,delimiter=';')):
                # TODO: make the column configurable
                trans_date = parse(row['Date comptable']).date()
                # TODO: make the character replacement configurable
                trans_desc = row['Libell�s'].replace("é","à").replace("�","é").replace("*"," ").replace("+"," ")
                
                if re.match('.*avis en annexe.*', trans_desc):
                    trans_desc = row['D�tails du mouvement'].replace("é","à").replace("�","é").replace("*"," ").replace("+"," ")
                    trans_pay = " ".join(trans_desc[0:25].split()).replace("(","").replace(")","")
                else:
                    trans_pay  = self.find_payee(trans_desc).replace("\"","").strip()
                
                trans_desc_short = " ".join(trans_desc.split()).replace("\"","").replace(",",".")
                trans_amt  = row['Montant'].replace(",",".")
                trans_cur  = row['Devise']
               
                # Exceptions
                if trans_amt==0: continue
                if re.match('Souscription.*', trans_desc): continue

                extracted_account = self._guess_account_from_payee(trans_pay, (trans_desc_short,trans_amt,trans_cur))
                if extracted_account: 
                    trans_acc = extracted_account['account']
                    #logging.info('ACCOUNT %s MATCHED WITH %s (%s)',extracted_account,trans_pay,trans_desc_short)
                else:
                    logging.info('No match for %s (%s)',trans_pay,trans_desc_short)
                    trans_acc = "Expenses:Unmatched"    



                meta = data.new_metadata(f.name, index)

                #if index == 0:
                #    opn = data.Open(meta=meta,date=parse("01/01/2000").date(),account="Assets:Ing:Checking",currencies=[trans_cur],booking=None)
                #    entries.append(opn)

                if trans_acc not in accounts:
                    accounts.update({trans_acc:1})
                    opn = data.Open(meta=meta,date=parse("01/01/2000").date(),account=trans_acc,currencies=[trans_cur],booking=None)
                    entries.append(opn)

                txn = data.Transaction(
                    meta=meta,
                    date=trans_date,
                    flag=flags.FLAG_OKAY,
                    payee=trans_pay,
                    narration=trans_desc_short,
                    tags=set(),
                    links=set(),
                    postings=[],
                )

                txn.postings.append(
                    data.Posting(
                        self.account,
                        amount.Amount(D(trans_amt), trans_cur),
                        None, None, None, None
                    )
                )

                txn.postings.append(
                    data.Posting(
                        trans_acc,
                        None,
                        None, None, None, None
                    )
                )

                entries.append(txn)

        with open(self.rules_path, 'a', newline='') as csvfile:
            ruleswriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for payee,info in self.new_payees.items():
                trans_desc_short, trans_amt, trans_cur = info
                if D(trans_amt) > 0:
                    trans_act="Income:XXXXXXXXX"
                else:
                    trans_act="Expenses:XXXXXXXXX"    
                logging.info('New Payee: %s written in rules',payee)
                ruleswriter.writerow([payee, trans_act, trans_desc_short])
                
        # sort rules file at the end so duplicate can found
        
        return entries 

        

       

