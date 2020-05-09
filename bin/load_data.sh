# Needed if running from inside ./bin
#export PYTHONPATH=$PYTHONPATH:`pwd`../


db_file="./secrets/db/db.sqlite"
# Make this into a loop on these
csv_file="./secrets/2018-01-14_All_Transactions.csv"

rm $db_file
python -m spearmint.services.transaction add $db_file $csv_file mint

# Classify using lookup
python -m spearmint.services.classification $db_file ./secrets/labeledTransactions.csv
