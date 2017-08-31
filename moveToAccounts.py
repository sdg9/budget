import os
import json
from pprint import pprint
import time
import datetime

'''
Manual Effort notes
- Must rename Paypal to Paypal (Stef) or Paypal (Steven) as necessary
- Manually update college fund transfer to Chase checking as transaction, TODO see if YNAB can automatically do this

OLD
    - Categorize as "Transfer" if I want to auto categorize as transfer in YNAB
    - Categorize as a subcategory of "Transfer" if I want to treat it as two separate transactions in YNAB
NEW
    - No auto transfers are kicked off from mint, instead since mince posts everything as a transaction (e.g. a transfer would show 2 transactions, in in to and one in from account) do likewise in YNAB

'''

#Constants
mydir = 'D:\Dropbox\YNAB\Steven\'s Budget~0AE9A757.ynab4'
replaceMemo = True #Should strip account information out of memo
replaceAccount = True #Should move account information from "Import From Mint" to appropriate account

#Globals
memo_to_account_mapping_dict = {
    'College Fund':'College Fund',
    'PayPal (Steven)':'PayPal (Steven)',
    'PayPal (Stef)':'PayPal (Stef)',
    'Car Fund':'Ally Savings - Car Fund',
    'DP PREMIUM SAVINGS':'Discover Savings',
    'Discover Card (Steven)':'Discover Card',
    'Discover IT':'Discover IT',
    'Amazon Visa 2':'Amazon Visa',
    'Barclaycard Rewards':'Barclaycard',
    'Emergency Fund':'Emergency Fund',
    'Cash':'Cash', #Not sure what to do
    'Savings':'Ally Savings', #Not sure what to do
    'XXXX5123':'HSA Bank',
    'DP CASHBACK CHECKING':'Discover Checking',
    'Chase Freedom':'Chase Freedom',
    'Chase Checking':'Chase Checking',
    'Freedom Unlimited':'Freedom Unlimited',
    'XXX-XXXX-979':'Kohl\'s Credit',
}

def main():
    print("Options: ")
    print("1: Move 'Import from Mint' transactions to appropriate accounts")
    print("2: Move transactions back to 'Import from Mint'")
    var = float(input("Enter option: "))

    if var == 1:
        mint_to_accounts()
    elif var == 2:
        accounts_to_mint()


'''
Moves all transactions from "Import from Mint" account to appropriate accounts
'''
def mint_to_accounts():
    fileName = findYNABFiles()
    if fileName is None:
        print("File not found")
        return
    with open(fileName) as data_file:
        data = json.load(data_file)

    saveBackup(fileName, data) #TODO if error then break since we won't have backup

    account_dict = populateAccountEntityMappings(data)
    payee_dict = populatePayeeMappings(data)

    #Print accounts
    #for account in account_dict:
    #    print account, ":", account_dict[account]

    #Print payees
    #for payee in payee_dict:
    #    print payee, ":", payee_dict[payee]

    #Move transactions within "Imported From Mint" account to appropriate account based on memo text
    moveTransactionsToDestinationAccounts('Import From Mint', data, account_dict)

    save(fileName, data) #TODO if error then break since we won't have backup

'''
Moves all transactions from their accounts to "Import from Mint" account
'''
def accounts_to_mint():
    in_month = input("Enter month: ")
    in_year = input("Enter year: ")
    #in_month = 9
    #in_year = 2015

    in_date = str(in_month) + "/01/" + str(in_year)
    selected_month = datetime.datetime.strptime(in_date, "%m/%d/%Y")

    fileName = findYNABFiles()
    if fileName is None:
        print("File not found")
        return
    else:
        print("Working with filename:", fileName)
    with open(fileName) as data_file:
        data = json.load(data_file)

    saveBackup(fileName, data) #TODO if error then break since we won't have backup
    account_to_id_dict = populateAccountEntityMappings(data)
    id_to_account_dict = {v: k for k, v in account_to_id_dict.items()}
    account_name_to_memo_dict = {v: k for k, v in memo_to_account_mapping_dict.items()}

    count = 0
    error_count = 0
    for transaction in data['transactions']:
        transaction_date_string = transaction['date']
        transaction_date = datetime.datetime.strptime(transaction_date_string, "%Y-%m-%d")

        if transaction_date >= selected_month:
            result = moveTransactionToImportFromMint(transaction, id_to_account_dict, account_to_id_dict, account_name_to_memo_dict)
            if result == 0:
                count = count + 1
            if result != 0:
                error_count = error_count + 1
    print("Reverted", count, "accounts back to 'Import From Mint' with", error_count, "errors.")

    save(fileName, data) #TODO if error then break since we won't have backup

'''
Moves a transaction from it's current account back to 'Import From Mint' with a proper memo field so that it can be moved back to it's appropriate account later
'''
def moveTransactionToImportFromMint(transaction, id_to_account_dict, account_to_id_dict, account_name_to_memo_dict):
    current_account_id = transaction['accountId']
    current_account_name = id_to_account_dict[current_account_id]
    dest_account_id = account_to_id_dict['Import From Mint']

    if current_account_id == dest_account_id:
        #print "Error, transaction already categorized as Import From Mint"
        return -1
    #else:
        #print "Updating transaction"


    if 'importedPayee' in transaction:
        existing_memo = ""
        if 'memo' in transaction:
            existing_memo = transaction['memo']

        '''
        print "TRANS:", transaction
        print "Current Account Id:", current_account_id
        print "Dest Account Id:", dest_account_id
        print "Current Account name:", current_account_name
        print "Dest account:", id_to_account_dict[dest_account_id]
        print "Memo:", existing_memo
        '''
        memo = account_name_to_memo_dict[current_account_name] + '::' + existing_memo

        #Update transaction
        transaction['memo'] = memo
        transaction['accountId'] = dest_account_id
        transaction['accepted'] = False

    return 0

'''
Moves all transactions from account specified by account_name to their proper accounts as determined in the memo field
'''
def moveTransactionsToDestinationAccounts(account_name, data, account_dict):
    count = 0
    for transaction in data['transactions']:
        date = transaction['date']
        amount = transaction['amount']
        account = transaction['accountId']
        #entity_id = transaction['entityId']
        dest_account_name = None

        if account_name not in account_dict:
            print("Account name", account_name, "doesn't exist")
            return

        #Only deal with transactions belonging to specified account_name
        if (account != account_dict[account_name]):
            continue

        #Destination account should be in memo, update appropriately and move tranaciton to appropriate account
        if 'memo' in transaction:
            memo = transaction['memo']
            if memo.find('::') != -1:
                #print("Account Name:", account_name)
                #print("Date:", date)
                #print("Amount:", amount)
                #print("Memo:", memo)
                #print("Memo Split:", memo.split("::")[0])
                if (memo.split("::")[0] in  memo_to_account_mapping_dict):
                    dest_account_name = memo_to_account_mapping_dict[memo.split("::")[0]]
                else:
                    print("Account Name:", account_name)
                    print("Date:", date)
                    print("Amount:", amount)
                    print("Memo:", memo)
                    print("Memo Split:", memo.split("::")[0])
                    print("ERROR, NOT IN MAPPING DICT!")
                    continue
                #update existing memo to remove account
                if replaceMemo:
                    transaction['memo'] = memo.split("::")[1]

                #move transaction to new account
                #print "Name:", dest_account_name, "Id: ", account_dict[dest_account_name]

                #if amount == -38.5:
                #    print transaction
                dest_account_id = account_dict[dest_account_name]
                #print "Account:", account
                if replaceAccount:
                    transaction['accountId'] = dest_account_id
                    transaction['accepted'] = True
                    count = count + 1
    print("Moved", count, "accounts to appropriate category")

def populateAccountEntityMappings(data):
    account_dict = {}
    #Read account types
    for account in data['accounts']:
        name = account['accountName']
        value = account['entityId']
        account_dict[name] = value
    return account_dict

def populatePayeeMappings(data):
    payee_dict = {}
    #Read payee types
    for payee in data['payees']:
        name = payee['name']
        value = payee['entityId']
        payee_dict[name] = value
    return payee_dict

def saveBackup(fileName, data):
    timestamp = time.strftime("%Y%m%d-%H-%M-%S")
    with open(fileName + '.' + timestamp + '.bak', 'w') as outfile:
        json.dump(data, outfile)

def save(fileName, data):
    with open(fileName, 'w') as outfile:
        json.dump(data, outfile)

'''
Finds the latest YNAB budget file
'''
def findYNABFiles():
    latestFile = None
    latestFileTS = None
    #print mydir
    for root, dirs, files in os.walk(mydir):
        for file in files:
            if file.endswith(".yfull"):
                filename = os.path.join(root, file)
                statbuf = os.stat(filename)
                if latestFile is None:
                    latestFile = filename
                    latestFileTS = statbuf.st_mtime
                elif statbuf.st_mtime > latestFileTS:
                    latestFile = filename
                    latestFileTS = statbuf.st_mtime
                #print "Modified time:", statbuf.st_mtime
    #print "File:", latestFile, "Modified time:", latestFileTS
    return latestFile

if __name__ == "__main__":
    main()
