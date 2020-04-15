export PYTHONPATH=$PYTHONPATH:`pwd`/../..

db_file="test.sqlite"

rm $db_file
python -m spearmint.services.transaction add $db_file ../../secrets/pc_mc_small_sample.csv pc_mc --account_name myPcAccount
python -m spearmint.services.transaction add $db_file ../../secrets/mint_small_sample.csv mint

python -m spearmint.services.classification $db_file ../../secrets/labeledTransactions.csv
