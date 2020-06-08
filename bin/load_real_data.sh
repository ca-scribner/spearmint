# Needed if running from inside ./bin
#export PYTHONPATH=$PYTHONPATH:`pwd`../

db_file="./secrets/db/db.sqlite"

rm $db_file

# Load and accept mint
csv_file="./secrets/mint_start_to_2020-05-12.csv"
python -m spearmint.services.transaction add $db_file $csv_file mint --accept

# Load but do not accept (because there isn't any) pc
#csv_file="./secrets/pc_start_to_2019-09-12.csv"  # DO NOT LOAD - these are included in mint

csv_file="./secrets/pc_2019-09-13_to_2020-05-11.csv"
python -m spearmint.services.transaction add $db_file $csv_file pc_mc --account_name "PC Financial Mastercard"

# Compute classifications (as suggestions)
python -m spearmint.services.classification model $db_file rf ./secrets/2020-06-02_rf.joblib --if_scheme_exists raise
python -m spearmint.services.classification most-common $db_file most_common --n_classifications_per_trx 2 --if_scheme_exists raise
