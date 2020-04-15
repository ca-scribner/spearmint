import pandas as pd
import pytest
import tempfile

from spearmint.data.db_session import global_init, global_forget, create_session
from spearmint.data.transaction import Transaction
from spearmint.services.classification import classify_db_by_lookup
from spearmint.services.transaction import find_transactions_without_category


@pytest.fixture
def db_init():
    # global_init builds tables and populates session factory
    global_init('', echo=True)
    yield
    global_forget()


LABELED_TRANSACTIONS = [
    {"Description": "CatMe0", "Category": 0},
    {"Description": "CatMe1", "Category": 1},
]


@pytest.fixture
def db_with_unclassified(db_init):
    s = create_session()
    trxs = [
        Transaction(description="Ignore0", category="something"),
        Transaction(description="NoCatAvail0"),
    ]
    for labeled_trx in LABELED_TRANSACTIONS:
        description = labeled_trx["Description"]
        trxs.append(Transaction(description=description))
    s.add_all(trxs)
    s.commit()


@pytest.fixture
def create_label_file():
    with tempfile.TemporaryFile('w+') as ftemp:
        print(f"ftemp = {ftemp}")
        df_labels = pd.DataFrame(LABELED_TRANSACTIONS).set_index("Description")
        print(df_labels)
        df_labels.to_csv(ftemp)
        ftemp.seek(0)
        yield ftemp


def test_lookup_classifier(db_with_unclassified, create_label_file):
    print(f"db_with_unclassified = {db_with_unclassified}")
    print(f"create_label_file = {create_label_file}")

    # Check before just to make sure we have 3/4 uncategorized
    s = create_session()
    trxs = find_transactions_without_category()
    assert len(trxs) == 3

    classify_db_by_lookup(create_label_file)

    trxs = find_transactions_without_category()
    assert len(trxs) == 1

    # Spot check we didnt overwrite
    all_trxs = s.query(Transaction).all()
    assert all_trxs[0].category == "something"
