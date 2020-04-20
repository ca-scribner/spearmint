import click

from spearmint.classifiers.lookup_classifier import LookupClassifier
from spearmint.data.db_session import create_session, global_init
from spearmint.services.transaction import get_transactions_without_category, get_all_transactions


def classify_db_by_lookup(label_file, classify_if_not_null=False):
    clf = LookupClassifier.from_csv(label_file)

    if classify_if_not_null:
        trxs = get_all_transactions()
    else:
        trxs = get_transactions_without_category()
    
    descriptions = [trx.description for trx in trxs]
    categories = clf.predict(descriptions)

    # Edit transactions here, but they're disconnected from db so need to "add" them after
    trxs_to_push = []
    for trx, category in zip(trxs, categories):
        # I think this avoids recommitting things that dont get changed.  But not sure
        if category is not None:
            trx.category = category
            trxs_to_push.append(trx)

    # Update anything we changed
    if trxs_to_push:
        s = create_session()
        s.add_all(trxs_to_push)
        s.commit()


@click.command()
@click.argument("DB_PATH")
@click.argument("LABEL_FILE")
@click.option(
    "--classify_if_not_null",
    is_flag=True,
    default=False,
    type=bool,
    help="If set, classifies all data in database even if it already has a classification"
)
def classify_db_by_lookup_cli(db_path, label_file, classify_if_not_null):
    """
    Classify transactions in a database given a description->label mapping file as input

    Args:\n
        db_path (str): Path to the database to classify data in\n
        label_file (str): Path to the csv description->label file
    """
    global_init(db_path)
    classify_db_by_lookup(label_file, classify_if_not_null)


if __name__ == '__main__':
    classify_db_by_lookup_cli()
