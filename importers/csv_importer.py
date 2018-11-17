""" 
Importer for CSV files
Tested only with my banks: INGB, KEYT
"""

from beancount.core.number import D
from beancount.ingest import importer
from beancount.core import account
from beancount.core import amount
from beancount.core import flags
from beancount.core import data
from beancount.core.position import Cost

from dateutil.parser import parse

# from titlecase import titlecase

import csv
import yaml
import os
import re

import logging
LOG_LEVEL = logging.DEBUG
#logging.basicConfig(filename='import.log',filemode='w',format='%(message)s', level=LOG_LEVEL)


logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler("import.log","w"),
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

# colorize the log output if the coloredlogs package is available
try:
    import coloredlogs
except ImportError as e:
    coloredlogs = None
if coloredlogs:
    coloredlogs.install(level=LOG_LEVEL)


class CsvImporter(importer.ImporterProtocol):

    def __init__(self, bank, rules_path, chars_to_replace, column_titles, skip, delimiter=';'):
        self.bank = bank
        self.rules_path = rules_path
        self.rules_path_new = rules_path + "_new"
        self.chars_to_replace = chars_to_replace
        self.column_titles = column_titles
        self.skip = skip
        self.delimiter = delimiter
        self.rules = []
        self.new_payees = {}
        open(self.rules_path_new, 'w').close()

    def name(self):
        return('CsvImporter')

    def identify(self, f):
        dirname = os.path.basename(os.path.dirname(f.name))
        filename = os.path.basename(f.name)
        if not re.match("(?i)"+self.bank, dirname):
            logging.info('Ignored: %s %s', dirname, filename)
            return False
        account = filename.split(" ")[0]
        self.account = "Assets:" + self.bank + ":" + account
        logging.info('Processing: %s %s', self.bank, account)
        return True

    def _import_rules(self):
        with open(os.path.expanduser(self.rules_path), 'r') as f:
            for index, row in enumerate(csv.DictReader(filter(lambda row: row[0]!='#',f),delimiter=';', fieldnames=['payee', 'account', 'desc', 'amount', 'currency'])):
                self.rules.append(row)
        logging.info('Imported %s rules',len(self.rules))

    def _guess_account_from_payee(self, payee, info):
        for rule in self.rules:
            # try first to find pattern in guessed payee
            if rule['payee'] and payee and re.match(".*(?i)"+rule['payee']+".*", payee):
                logging.info('Pattern %s found in payee: %s', rule['payee'], payee)
                return rule
            # then try to find pattern in short description
            if rule['payee'] and info and re.match(".*(?i)"+rule['payee']+".*", info[0]):
                logging.info('Pattern %s found in info: %s', rule['payee'], info[0])
                return rule
        # if we parsed all rules and not found any match, then we add the payee in the new payee dict
        if payee.count(' ') > 0:
            payee = payee.split(" ")[0]
        if payee not in self.new_payees:
            self.new_payees.update({payee:info})

    # TODO: make this generic
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
        
        logging.info('BEGIN Processing: %s %s', self.bank, os.path.basename(f.name))
        
        self.rules = []
        self.new_payees = {}
        entries = []
        accounts = {}
        self._import_rules()


        # opn = data.Optional(meta=meta,date=parse("01/01/2000").date(),account=trans_acc,currencies=[trans_cur],booking=None)
        # entries.append(opn)

        with open(f.name, "r", encoding='utf-8', errors='ignore') as f:

            for index, row in enumerate(csv.DictReader(f, delimiter=self.delimiter)):
                
                # get the date
                trans_date = parse(row[self.column_titles[0]]).date()
                
                # get the amount & currency (skip if 0)
                trans_amt  = row[self.column_titles[1]].replace(".","").replace(",",".")
                if trans_amt==0: continue
                trans_cur  = row[self.column_titles[2]]
                
                # get the description
                trans_desc = row[self.column_titles[3]]
                # ignore transactions to skip
                for skip in self.skip:
                    if re.match("(?i)"+skip, trans_desc): continue
                # replace all characters required
                for oldchar, newchar in self.chars_to_replace.items():
                    trans_desc = trans_desc.replace(oldchar, newchar)
                
                # sometimes the meaningful part is in annex
                if re.match('.*(?i)avis en annexe.*', trans_desc):
                    trans_desc = row[self.column_titles[4]].replace("é","à").replace("�","é").replace("*"," ").replace("+"," ")
                    trans_pay = " ".join(trans_desc[0:25].split()).replace("(","").replace(")","")
                else:
                    trans_pay  = self.find_payee(trans_desc).replace("\"","").strip()
                
                # reformat the description
                trans_desc_short = " ".join(trans_desc.split()).replace("\"","").replace(",",".")

                # try to guess the account
                extracted_account = self._guess_account_from_payee(trans_pay, (trans_desc_short, trans_amt, trans_cur))
                if extracted_account: 
                    trans_acc = extracted_account['account']
                    trans_pay = extracted_account['payee']
                    #logging.info('ACCOUNT %s MATCHED WITH %s (%s)',trans_acc,trans_pay,trans_desc_short)
                else:
                    #logging.info('No match for %s (%s)',trans_pay,trans_desc_short)
                    trans_acc = "Expenses:Unmatched" 
                    continue   



                meta = data.new_metadata(f.name, index)

                #if index == 0:
                #    opn = data.Open(meta=meta,date=parse("01/01/2000").date(),account="Assets:Ing:Checking",currencies=[trans_cur],booking=None)
                #    entries.append(opn)

                if trans_acc not in accounts:
                    accounts.update({trans_acc:1})
                    opn = data.Open(meta=meta,date=parse("01/01/2000").date(),account=trans_acc,currencies=[trans_cur],booking=None)
                    # entries.append(opn)

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

        # Add unknown payees in the rules file
        if len(self.new_payees) > 0:
            logging.info('Saving %s new rules...',len(self.new_payees))
            with open(self.rules_path_new, 'a', newline='') as csvfile:
                ruleswriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for payee,info in self.new_payees.items():
                    trans_desc_short, trans_amt, trans_cur = info
                    if D(trans_amt) > 0:
                        trans_act="Income:XXXXXXXXX"
                    else:
                        trans_act="Expenses:XXXXXXXXX"    
                    #logging.info('New Payee: %s written in rules',payee)
                    ruleswriter.writerow([payee, trans_act, trans_desc_short])
                csvfile.close()
            
                    
            # sort rules file at the end so duplicate can be found   
            # TODO: treat duplicates here (options: keep first word if long enough or two if not, keep always 8 chars ) 
            # TODO: change lambda by keyitems  
            logging.info('Sorting rules file ...')
            with open(self.rules_path_new, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=";", fieldnames=['payee', 'account', 'desc'])
                sortedRules = sorted(reader, key=lambda row:(row['payee'],row['account']), reverse=False)

            with open(self.rules_path_new, 'w', newline='') as csvfile:
                #fieldnames = ['column_1', 'column_2', 'column_3']
                #writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                #writer.writeheader()
                writer = csv.DictWriter(csvfile, delimiter=";", fieldnames=['payee', 'account', 'desc'])
                for index, row in enumerate(sortedRules):
                    writer.writerow(row)

        logging.info('END')

        return entries 

        

       

