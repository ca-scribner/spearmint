export PYTHONPATH=$PYTHONPATH:`pwd`../../

python -m spearmint.services.transaction add test.sqlite secrets/pc_mc_small_sample.csv pc_mc myPcAccount
