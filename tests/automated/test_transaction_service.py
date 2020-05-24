# TODO: Need to flesh this out more.  Only tests a small subset

import pytest

from spearmint.data.category import Category
from spearmint.data.db_session import global_init, global_forget, create_session
from spearmint.data.transaction import Transaction
from spearmint.services.transaction import get_unique_transaction_categories_as_string


@pytest.fixture
def db_init():
    # global_init builds tables and populates session factory
    global_init('', echo=True)
    yield
    global_forget()


LABELED_TRANSACTIONS = [
    {"description": "CatMe0", "category": 0, "accept_category": True},
    {"description": "CatMe1", "category": 1},
    {"description": "CatMe1-2", "category": 1},
    {"description": "CatMe2", "category": 2, "accept_category": True},
]


@pytest.fixture
def db_with_desc_cat(db_init):
    s = create_session()
    trxs = []
    for labeled_trx in LABELED_TRANSACTIONS:
        print(f"labeled_trx = {labeled_trx}")
        category = Category(category=str(labeled_trx['category']), scheme="from_test")

        kwargs = {k: v for k, v in labeled_trx.items() if k not in ["category", "accept_category"]}
        trx = Transaction(**kwargs)

        trx.categories_suggested.append(category)
        if labeled_trx.get("accept_category", None):
            trx.category = category

        trxs.append(trx)
    s.add_all(trxs)
    s.commit()


def test_lookup_classifier(db_with_desc_cat):
    # Check that we get the right categories and that we're not getting just a full list
    expected_categories = set(str(trx["category"]) for trx in LABELED_TRANSACTIONS)
    actual_categories = get_unique_transaction_categories_as_string()
    assert expected_categories == set(actual_categories)
    assert len(expected_categories) == len(actual_categories)
