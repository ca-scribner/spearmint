from typing import List
import pandas as pd
import click
from sqlalchemy import inspect, distinct
from sqlalchemy.orm import joinedload

from spearmint.data.category import Category
from spearmint.data.db_session import create_session, global_init
from spearmint.data.transaction import Transaction
from spearmint.etl.transaction_extractor import PARSED_NAME_MAP
from spearmint.etl.transaction_extractor import TransactionExtractor
from spearmint.etl.mint.transaction_extractor import MintTransactionExtractor
from spearmint.etl.pc_mc.transaction_extractor import PcMcTransactionExtractor


# Enumerators (to be moved somewhere that makes more sense)
FROM_FILE = "from_file"


def dataframe_to_transactions(df: pd.DataFrame, accept_category: bool = False, column_name_map: dict = PARSED_NAME_MAP):
    return [_row_dict_to_transaction(row_dict, column_name_map, accept_category) for row_dict in df.to_dict("records")]


def _row_dict_to_transaction(row_dict: dict, column_name_map: dict, accept_category: bool = False):
    # If we have a category specified in the file, create a Category instance
    if row_dict[column_name_map["category"]]:
        category = Category(
            scheme=FROM_FILE,
            category=row_dict[column_name_map["category"]],
        )
    else:
        category = None

    transaction = Transaction(
        datetime=row_dict[column_name_map["datetime"]],
        description=row_dict[column_name_map["description"]],
        amount=row_dict[column_name_map["amount"]],
        account_name=row_dict[column_name_map["account_name"]],
        source_file=row_dict[column_name_map["source_file"]],
    )

    if category:
        transaction.categories_suggested.append(category)

        if accept_category:
            transaction.category = category
    return transaction


def add_transactions_from_dataframe(df: pd.DataFrame, accept_category: bool = False):
    """
    Puts rows of df to the transactions db, with any categories added as suggested categories in the category table

    Optionally, can accept the categories and attach them to transactions as the selected category.  Otherwise, accepted
    category is left blank

    TODO: This is directly tied to the transaction extractor (implicitly linked by assuming the df naming conventions),
          should this just be a method on that class?  Or, I should move the nomenclature definition somewhere central

    Args:
        df (pd.DataFrame): Pandas dataframe with rows of transactions
        accept_category (bool): If True, any categories in the DataFrame will also be "accepted" on the committed
                                transactions

    Returns:
        None
    """
    transactions = dataframe_to_transactions(df, accept_category)

    s = create_session()
    s.add_all(transactions)
    s.commit()
    s.close()


def get_transactions_without_category() -> List[Transaction]:
    s = create_session()
    # transactions = s.query(Transaction).all()
    transactions = s.query(Transaction).filter(Transaction.category.is_(None)).all()
    s.close()
    return transactions


def get_transactions_with_category(return_type='list', lazy=False) -> List[Transaction]:
    return get_transactions(return_type=return_type, lazy=lazy, filters=(Transaction.category.has(),))


def get_transaction_by_id(transaction_id) -> Transaction:
    s = create_session()
    trx = s.query(Transaction).filter(Transaction.id == transaction_id).first()
    s.close()
    return trx


def get_unique_transaction_categories_as_string(category_type='all') -> List[str]:
    """
    Returns list of all unique categories used in the transaction table as string category labels

    Args:
        category_type (str): all: returns all unique category names from the category table
                             accepted: returns only category names from "accepted" categories in the transaction table
    """
    s = create_session()
    if category_type == 'all':
        categories = s.query(Category.category).distinct().all()
    elif category_type == 'accepted':
        accepted_cat_ids = flatten(s.query(Transaction.category_id).all())
        categories = (s.query(Category.category)
                       .filter(Category.id.in_(accepted_cat_ids))
                       .distinct()
                       .all()
                      )
    else:
        raise ValueError(f"Unsupported category_type '{category_type}'")
    s.close()

    # Category is just the first element of the tuples returned
    categories = [x[0] for x in categories]
    return categories


def get_transactions_by_id(return_type='list', lazy=False, filters=tuple(), ids=tuple()) -> List[Transaction]:
    """
    Returns all transactions with given id as specified type

    Args:
        return_type (str): One of:
                            list: returns as [Transaction]
                            df: returns as pd.DataFrame with one row per transaction and all attributes as columns
        lazy (bool): If True, lazily load transactions (thus information about linked categories will not be available).
                     If False, eagerly load the category objects as well using joinedload
        filters: Iterable of arguments to pass to query.filter, such as (transaction.category.is_(None),)
        ids (iterable): Iterable of id's to include in the query
    Returns:
        (list): Transactions matching the search
    """
    # Add filter by id
    filters = list(filters)
    filters.append(Transaction.id.in_(ids))

    return get_transactions(return_type, lazy, filters)


def get_transactions(return_type='list', lazy=False, filters=tuple()) -> List[Transaction]:
    """
    Returns all transactions as specified type

    # TODO: Consolidate other get's to this one?

    Args:
        return_type (str): One of:
                            list: returns as [Transaction]
                            df: returns as pd.DataFrame with one row per transaction and all attributes as columns
        lazy (bool): If True, lazily load transactions (thus information about linked categories will not be available).
                     If False, eagerly load the category objects as well using joinedload
        filters: Iterable of arguments to pass to query.filter, such as (transaction.category.is_(None),)

    Returns:
        See return_type
    """
    s = create_session()
    q = s.query(Transaction)
    for f in filters:
        q = q.filter(f)
    if not lazy:
        q = q.options(
            joinedload(Transaction.category),
            joinedload(Transaction.categories_suggested),
        )

    trxs = q.all()
    s.close()

    # Should test this first, but lazy...
    if return_type == 'list':
        pass
    elif return_type == 'df':
        trxs = transactions_to_dataframe(trxs)
    else:
        raise ValueError(f"Invalid return_type {return_type}")
    return trxs


def transactions_to_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    print("WARNING: transactions as df not tested after moving categories to category table.  Behaviour unknown")

    trxs_as_dicts = [_sa_obj_as_dict(trx) for trx in transactions]

    df = pd.DataFrame(trxs_as_dicts)
    return df


def to_csv(csv_filename: str):
    """
    Exports transactions into a CSV file that fits the basic transaction_extractor format

    Args:
        csv_filename (str): Name of csv to generate

    Returns:
        None
    """
    print("\n******************************************************************************************************")
    print("WARNING: This was loosely tested, but no round-trip testing completed.  If you need round-trip safety, test "
          "it more")
    print("******************************************************************************************************\n")
    get_transactions('df').to_csv(csv_filename, index=False)

# Helpers
def _sa_obj_as_dict(sa_obj, include_category_relationships=True):
    """
    Converts a SqlAlchemy object (eg: a row of a table from SqlAlchemy) to a dict

    From https://stackoverflow.com/a/37350445/5394584

    Args:
        sa_obj: SqlAlchemy object
        include_category_relationships (bool): If True, will also try to add entries for relationships which have a
                                               .category attribute (used for category and suggested category)

    Returns:
        (dict)
    """
    inspected = inspect(sa_obj)
    d = {c.key: getattr(sa_obj, c.key) for c in inspected.mapper.column_attrs}

    if include_category_relationships:
        for k in inspected.mapper.relationships:
            try:
                d[k.key] = getattr(getattr(sa_obj, k.key), 'category')
            except AttributeError:
                pass

    return d


def get_sa_obj_keys(sa_obj):
    return (prop.key for prop in inspect(sa_obj).mapper.column_attrs)


def flatten(lst):
    return [x[0] for x in lst]


@click.group()
def cli():
    pass


@click.command()  # Can specify help here, or if blank will use docstring
@click.argument("DB_PATH")
@click.argument("CSV_FILE")
@click.argument("CSV_FLAVOR")
@click.option(
    "--account_name",
    default=None,
    help="Account Name applied to all loaded transactions.  Used only for pc_mc csv flavor"
)
@click.option(
    "--accept/--no_accept",
    default=False,
    help="Optionally accept categories loaded as accepted categories"
)
def add(db_path, csv_file, csv_flavor, account_name, accept):
    """
    Add transactions to a database from a csv file, creating the database if required

    Args: \n
        db_path (str): Path to the database to add transactions to \n
        csv_file (str): Path to the csv file to load and extract transactions from\n
        csv_flavor (str): One of:\n
            mint: Mint-formatted csv file\n
            pc_mc: PC Mastercard formatted csv file\n
    """
    # Initialize db connection
    global_init(db_path, False)

    df = import_csv_as_df(csv_file, csv_flavor, account_name)

    print(df)

    add_transactions_from_dataframe(df, accept_category=accept)


def import_csv_as_df(csv_file, csv_flavor, account_name=None):
    if csv_flavor == "pc_mc":
        te = PcMcTransactionExtractor.read_csv(csv_file, account_name=account_name)
    elif csv_flavor == "mint":
        te = MintTransactionExtractor.read_csv(csv_file)
    elif csv_flavor == "base":
        te = TransactionExtractor.read_csv(csv_file)
    else:
        raise ValueError(f"Unknown csv_flavor '{csv_flavor}'")
    return te.to_dataframe(deep=True)


@click.command()
@click.argument("db_path")
@click.argument("csv_file")
def export_to_csv(db_path, csv_file):
    """
    Exports database to CSV.  WARNING: Not tested fully for round-trip

    Args:
        db_path (str): Path to source DB
        csv_file (str): Filename to write db to
    """
    global_init(db_path)
    to_csv(csv_file)


cli.add_command(add)
cli.add_command(export_to_csv)


if __name__ == '__main__':
    cli()
