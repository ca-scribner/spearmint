from spearmint.classifiers.lookup_classifier import LookupClassifier
from spearmint.data.db_session import create_session
from spearmint.services.transaction import find_transactions_without_category, find_all_transactions


def classify_by_lookup(label_file, classify_if_not_null=False):
    clf = LookupClassifier.from_csv(label_file)

    if classify_if_not_null:
        trxs = find_all_transactions()
    else:
        trxs = find_transactions_without_category()
    
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
