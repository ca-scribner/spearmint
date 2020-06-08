# Needed if running from inside ./bin
#export PYTHONPATH=$PYTHONPATH:`pwd`../

# WARNING: Will convert any categories that are accepted to be verified, delete all unaccepted categories, and then
# create new predicted categories

db_file="./secrets/db/db_TEMP2.sqlite"

# Load DB backup
# TODO

# Accept "accepted" categories by moving them out of previous schemes (to avoid conflict with below suggestions)
python -m spearmint.services.category accept-current $db_file accepted

# Load mint
#csv_file="./secrets/mint_start_to_2020-05-12.csv"
#python -m spearmint.services.transaction add $db_file $csv_file mint

## Load pc
#csv_file="./secrets/pc_2019-09-13_to_2020-05-11.csv"
#python -m spearmint.services.transaction add $db_file $csv_file pc_mc --account_name "PC Financial Mastercard"

# Compute classifications (as suggestions)
python -m spearmint.services.classification model $db_file rf ./secrets/2020-06-02_rf.joblib --if_scheme_exists replace
python -m spearmint.services.classification most-common $db_file most_common --n_classifications_per_trx 2 --if_scheme_exists replace
