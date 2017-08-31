import os
import sys
import csv
import datetime
import json
import requests
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import mintapi

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

cur_version = sys.version_info
#Make sure all Mint categories pertaining to income are listed here
cat_list_income = [
        'Bonus',
        'Gift Received',
        # 'HSA', #as of 1/6 no longer pull HSA money in as income as it's off budget, instead just manually sync up HSA off budget balance once a month.
        'Interest Income',
        'Paycheck',
        'Reimbursement', #refunds
        'Rental Income',
        'Returned Purchase',
        'Rewards Points',
        'Sold Item', #Sold Item
        'Tax Refund',
        'PD2Skills',
        'Rebate',
        ]

#Maps transactions to appropriate accounts
betterment_transfer_cateogry_dict = {
        'Xfer to Betterment': {
            '38.50': 'Betterment - Huntington Furnishings',
            '72.50': 'Betterment - Hot Tub',
            '130.00': 'Save For Car'
            },
        }
transfer_category_dict = {
        'Xfer to Chase CC': 'Chase Freedom',
        'Xfer to Paypal Stef': 'Paypal (Stef)',
        'Xfer to Paypal Steve': 'Paypal (Steven)',
        'Xfer to Chase Check': 'Chase Checking',
        'Xfer to Amazon Visa': 'Amazon Visa',
        'Xfer to Discover Crd': 'Discover Card',
        'Xfer to Barclay Card': 'Barclaycard',
        'Xfer from BrightDir': 'BrightDirections 529',
        #'Xfer from CYC': 'HSA Bank',
        'Xfer from Cash': 'Cash',
        'Xfer to Emergency': 'Emergency Fund',
        }

#This is the structure of the YNAB categories.  By default Mint categories names will map to a subcategory here ignoring parent category similarities or differences.
ynab_cat_dict = {
        'Pre-YNAB Debt': [
            'Transfer Placeholder',
            ],
        'Auto & Transport': [
            'Auto Insurance',
            'Auto Payment',
            'Gas & Fuel',
            'I-Pass/Tolls', #I-Pass
            'Parking',
            'Public Transportation',
            'License Registration',
            'Service & Parts',
            'Boat',
            'Parking',
            ],
        'Business Services': [
            'Steven\'s Business',
            ],
        'Bills & Utilities': [
            'Electric & Gas',
            'Electricity Bill',
            'Gas Bill', #electricity
            'Home Phone', #gas/oil
            'Internet',
            'Mobile Phone',
            'Television',
            'Trash Service', #trash
            'Utilities',
            'Water Bill',
            ],
        'Education': [
            'Books & Supplies',
            'Student Loan',
            'Tuition',
            'Vet School Misc',
            ],
        'Entertainment': [
            'Amusement',
            'Arts',
            'General Entertainmen',
            'Movies & DVDs',
            'Music',
            'Newspapers & Magazines',
            ],
        'Fees & Charges': [
            'ATM Fee',
            'Bank Fee',
            'Finance Charge',
            'Late Fee',
            'Service Fee',
            'Trade Commissions',
            'Bright Directions',
            'Parking Ticket',
            ],
        'Financial': [
            'Financial Advisor',
            'Life Insurance',
            'Personal Articles',
            'Umbrella Insurance',
            ],
        'Food & Dining': [
                #Food & Dining
                'Alcohol & Bars',
                'Groceries',
                'Eating Out',
                ],
        'Gifts & Donations': [
                'Charity',
                'Gift',
                'Tithing', #religeous donations
                'Wedding',
                ],
        'Health & Fitness': [
                'Dentist',
                'Doctor', #Doctor/Dentist
                'Eyecare', #<-- figure out where this belongs
                'Gym',
                'Health Insurance',
                'Pharmacy', #medicine/drugs
                'Sports', #Other
                'HSA Applicable',
                'HSA Reimbursable',
                ],
        'Home': [
                'Mortgage',
                'Property Tax',
                'Rental Taxes',
                'Landlord Misc',
                'Security Deposit',
                'Home Improvement',
                'Mundelein Repairs',
                'Maintenance',
                'Furnishings (Huntington) 3000/77',
                'Furnishings',
                'Smart Home',
                'Home Insurance',
                'Rental Taxes',
                'Lawn & Garden',
                'Tools',
                'Renovations',
                ],
        'Rental': [
                'Furnishings (Urbana)',
                'Rent',
                'Rental Insurance',
                ],
        'Investments': [ #TODO
                'Buy',
                'Deposit',
                'Dividents & Cap Gains',
                'Roth IRA',
                'Sell',
                'Withdrawal',
                ],
        'Kids': [
                'Steven\'s Allowance',
                'Steven\'s Computer',
                'Stef\'s Allowance',
                'Stef\'s Clothing',
                'Steven\'s Clothing',
                'Family Games',
                ],
        'Personal Care': [
                'Hair',
                'Laundry',
                'Spa & Massage',
                'Health and Beauty',
                ],
        'Pets': [
                'Pet Food & Supplies',
                'Pet Grooming',
                'Veterinary',
                ],
        'Shopping': [
                'Miscellaneous',
                #'General Shopping',
                'Household Goods',
				#'Electronics & Software',
                'Hobbies',
                'Sporting Goods',
                'Postage',
                'Electronics Fund',
                'Appliances',
                ],
        'Taxes': [
                'Federal Tax',
                'Local Tax',
                'Sales Tax',
                'State Tax',
                ],
        'Travel': [
                'Air Travel',
                'Hotel',
                'Rental Car & Taxi',
                'Vacation',
                ],
        'Business Services': [
                'Advertising',
                'Legal',
                'Office Supplies',
                'Printing',
                'Shipping',
                'Steven\'s Business',
                'Landlord'
                ],
        'Savings': [
                'Hot Tub 6000/145',
                'Fluff',
                'Nicer Bed 3000/167',
                'Car Fund',
                ]
        }

#If Mint names don't line up 100% with YNAB names translate here (e.g. 'mint low level category': 'YNAB low level category')
# Mint: YNAB
mint_to_ynab_cat_translation = {
        'Furnishings (Urbana)': 'Furnishings (Urbana)',
        'Furnishings (Hunting': 'Furnishings',
        'Wedding Gifts': 'Wedding',
        'Electronics & Software': 'Electronics Fund',
        'Steven Roth': 'Roth IRA',
        'Home Improvement': 'Renovations',
        'Mundelein Repairs': 'Maintenance',
        # 'Electricity Bill': 'Electric & Gas',
        'Hot Tub': 'Hot Tub 6000/145',
        'Huntington Furnishings': 'Furnishings (Huntington) 3000/77'
        }

memo_to_account_mapping_dict = {
    'College Fund':'College Fund',
    'PayPal (Steven)':'PayPal (Steven)',
    'PayPal (Stef)':'PayPal (Stef)',
    'Car Fund':'Car Fund',
    'DP PREMIUM SAVINGS':'Discover Savings',
    'Discover Card (Steven)':'Discover Card',
    'Amazon Visa 2':'Amazon Visa',
    'Barclaycard Rewards':'Barclaycard',
    'Emergency Fund':'Emergency Fund',
    'Cash':'Cash', #Not sure what to do
    'Savings':'Ally Savings', #Not sure what to do
    'XXXX5123':'HSA Bank',
    'DP CASHBACK CHECKING':'Discover Checking',
    'Chase Freedom':'Chase Freedom',
    'Chase Checking':'Chase Checking',
    'XXX-XXXX-979':'Kohl\'s Credit',
}

valid_skip_categories = [
    'Credit Card Payment',
    'Transfer',
    'HSA',
    'Bank to Bank Transfe',
    'Transfer to Paypal',
    '0'
]
valid_skip_description = [
    'Check 0'
]

'''
Maps a mint category into a YNAB category
ynab_cat_dict should reflect the structure of YNAB category heirarcy
'''
def categoryMapper(cat, txnType, date):
    #translate category if translation exists
    if (cat in mint_to_ynab_cat_translation):
        cat = mint_to_ynab_cat_translation[cat]

    for high_level_cat in ynab_cat_dict:
        if (cat in ynab_cat_dict[high_level_cat]):
            return high_level_cat + ':' + cat

    if (cat in cat_list_income):
        #print "Cat: {} Date: {}".format(cat, date)
        #return "Income: Available this month"
        return "Income: Available next month"


account_dict ={}

#No longer deal with transfers in this method so this method is outdated
'''
Maps transfer to updated Payee name for YNAB to leverage
'''
def transferCategoryMapper(category, amount, memo):

    if category in betterment_transfer_cateogry_dict and amount in betterment_transfer_cateogry_dict[category]:
        print(category, "in transfer dict wiht amount", amount, "category:", betterment_transfer_cateogry_dict[category][amount])
        return "Transfer: " + betterment_transfer_cateogry_dict[category][amount]
    elif category in transfer_category_dict:
        return "Transfer: " + transfer_category_dict[category]
    else:
        #"Determine from memo"
        #dest_account_name = memo.split("::")[0]
        #return "Transfer to: " + memo_to_account_mapping_dict[dest_account_name]
        #return category
        #print "No result for category:", category, "amount:", amount
        return ''

'''
Reads csv file of mint transactions and creats a ynab formatted csv
This is done at the month level
'''
def mint_csv_to_ynab(selected_date):
    csvRows = []
    if (cur_version <= (3,0,0)):
    	reader = csv.reader(open("transactions.csv", "rb"))
    else:
    	reader = csv.reader(open("transactions.csv", "r"))

    for row in reader:
        csvRows.append(row)

    filename = "ynabTransactions.%d.%02d.csv" % (selected_date.year, selected_date.month)
    improper_cat_filename = "improperCategory.%d.%02d.txt" % (selected_date.year, selected_date.month)
    if (cur_version <= (3,0,0)):
    	writer = csv.writer(open(filename, "wb"))
    else:
    	writer = csv.writer(open(filename, "w", newline=''))

    ynabCsv = []
    ynabCsv.append(['Date', 'Payee', 'Category', 'Memo', 'Outflow', 'Inflow', 'Account']);

    writer.writerow(ynabCsv[0])

    if (cur_version <= (3,0,0)):
        fOut = open(improper_cat_filename, 'w')
    else:
        fOut = open(improper_cat_filename, 'w', newline='')


    count = 0
    error_count = 0
    for i in range(1, len(csvRows)):
        date = csvRows[i][0];

        #SKIP Record if not proper date
        date_time = datetime.datetime.strptime(date, "%m/%d/%Y");
        if (date_time.year != selected_date.year or date_time.month != selected_date.month):
            continue

        #reference same id on purpose
        payee = csvRows[i][1]
        description = csvRows[i][1]

        category = csvRows[i][5]
        if (cur_version <= (3,0,0)):
            memo = csvRows[i][8].encode('string_escape')
            memo = memo.replace("\\r\\n", ", ")
        else:
            memo = csvRows[i][8].replace('\n', ', ').replace('\r', ', ')
            #memo = memo.replace("\\r\\n", ", ")
            #.encode('unicode_escape').replace("\\r\\n", ", ")
            #if (memo):
            #  print(memo)
            #  return
            #memo = csvRows[i][8].encode('string_escape')
            #memo = memo.replace("\\r\\n", ", ")
            #memo = csvRows[i][8].encode('unicode_escape')
        #memo = csvRows[i][8];
        #replace newline characters

        account = csvRows[i][6]

        #if account in accounts:
            #memo = accounts[account] + ":: " + memo
        #else:
        memo = account + ":: " + memo
        account_dict[account] = 1

        outflow = ''
        inflow = ''
        txnType = csvRows[i][4];
        amount = csvRows[i][3];
        if (txnType == 'debit'):
            outflow = amount;
        elif (txnType == 'credit'):
            inflow = amount;

        '''if category == 'Transfer':
            updatedCategory = 'Transfer'
            payee = transferCategoryMapper(payee, amount, memo)
            memo = memo + category + " " + description
            '''
        if (category in betterment_transfer_cateogry_dict or category in transfer_category_dict):
        #if (category in cat_list_transfer):
            updatedCategory = 'Native YNAB Transfer'
            payee = transferCategoryMapper(category, amount, memo)
            memo = memo + category + " " + description
        else:
            updatedCategory = categoryMapper(category, txnType, date)

        if (updatedCategory is not None):
            if updatedCategory == 'Native YNAB Transfer':
                updatedCategory = ''
            writer.writerow([date, payee, updatedCategory, memo, outflow, inflow, account]);
            count = count + 1
        elif (category in valid_skip_categories):
            print "Allowed category to skip"
        elif (payee in valid_skip_description):
            print "Allowed category to skip"
        else:
            fOut.write("\nOmitting: ")
            fOut.write(', '.join([date, payee, category, memo, outflow, inflow, account]))
            error_count = error_count + 1

    print("Successfully exported", count, "transactions with", error_count, "errors.")

class MintHTTPSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, **kwargs):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, ssl_version=ssl.PROTOCOL_SSLv3, **kwargs)

def download_txn(email, password):
    mint = mintapi.Mint(email, password)
    #1 Login
    #mint.login_and_get_token(email, password)
    print mint

    # 2: Download transactions as csv
    response = mint.get('https://wwws.mint.com/transactionDownload.event?queryNew=&offset=0&filterType=cash&comparableType=8')
    res = open('transactions.csv','wb')
    res.write(response.content)
    res.close()

def import_to_ynab(selected_month):
    filename = "ynabTransactions.%d.%02d.csv" % (selected_month.year, selected_month.month)
    cwd = os.getcwd()
    csv_file = cwd + '\\' + filename
    #Run autoit script
    os.system('launchYNAB.au3 "' + csv_file + '"')

def main():
    #if len(sys.argv) >= 3:
    #    email, password = sys.argv[1:]
    #else:
        #email = raw_input("Mint email: ")
        #password = getpass.getpass("Password: ")
    email = "steveng9@gmail.com"
    password = "mntpwd06A"

    if (cur_version <= (3,)):
	    in_month = raw_input("Enter month: ")
	    in_year = raw_input("Enter year: ")
    else:
	    in_month = input("Enter month: ")
	    in_year = input("Enter year: ")

    in_date = in_month + "/01/" + in_year
    selected_month = datetime.datetime.strptime(in_date, "%m/%d/%Y")

    print("Options: ")
    print( "1: Download transactions and convert to ynab")
    print( "2: Download only")
    print( "3: Convert only")
    if (cur_version <= (3,)):
	    var = float(raw_input("Enter option: "))
    else:
	    var = float(input("Enter option: "))

    if (var == 1 or var == 2):
        transactions = download_txn(email, password)

    if (var == 1 or var == 3):
        mint_csv_to_ynab(selected_month)
        import_to_ynab(selected_month)

    #for account in account_dict:
        #print account

if __name__ == "__main__":
    main()


'''Old Stuff'''
