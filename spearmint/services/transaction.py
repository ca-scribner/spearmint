from typing import List
import pandas as pd
import click
from sqlalchemy import inspect, distinct

from spearmint.data.db_session import create_session, global_init
from spearmint.data.transaction import Transaction
from spearmint.etl.transaction_extractor import PARSED_NAME_MAP
from spearmint.etl.transaction_extractor import TransactionExtractor
from spearmint.etl.mint.transaction_extractor import MintTransactionExtractor
from spearmint.etl.pc_mc.transaction_extractor import PcMcTransactionExtractor


def dataframe_to_transactions(df, column_name_map=PARSED_NAME_MAP):
    return [_row_dict_to_transaction(row_dict, column_name_map) for row_dict in df.to_dict("records")]


def _row_dict_to_transaction(row_dict, column_name_map):
    # Loop over all attributes requested from transaction to build a new transaction from this dict
    kwargs = {k: row_dict[column_name_map[k]] for k in get_sa_obj_keys(Transaction) if k is not 'id'}
    transaction = Transaction(**kwargs)
    return transaction


def add_transactions_from_dataframe(df):
    transactions = dataframe_to_transactions(df)

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


def get_transaction_by_id(transaction_id) -> Transaction:
    s = create_session()
    trx = s.query(Transaction).filter(Transaction.id == transaction_id).first()
    s.close()
    return trx


# Can I set output type dynamically using type of the Transaction.category property?
def get_transaction_categories() -> List[str]:
    """
    Returns list of all unique, valid categories in the transaction table
    """
    s = create_session()
    categories = s.query(Transaction.category).distinct()
    # The query returns a tuple per record.  Flatten
    categories = [tup[0] for tup in categories]
    s.close()
    return categories


def get_all_transactions(return_type='list') -> List[Transaction]:
    """
    Returns all transactions as specified type

    Args:
        return_type (str): One of:
                            list: returns as [Transaction]
                            df: returns as pd.DataFrame with one row per transaction and all attributes as columns

    Returns:
        See return_type
    """
    s = create_session()
    trxs = s.query(Transaction).all()
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
    trxs_as_dicts = [sa_obj_as_dict(trx) for trx in transactions]
    df = pd.DataFrame(trxs_as_dicts)
    return df


# Helpers
def sa_obj_as_dict(sa_obj):
    """
    Converts a SqlAlchemy object (eg: a row of a table from SqlAlchemy) to a dict

    From https://stackoverflow.com/a/37350445/5394584

    Args:
        sa_obj: SqlAlchemy object

    Returns:
        (dict)
    """
    return {c.key: getattr(sa_obj, c.key)
            for c in inspect(sa_obj).mapper.column_attrs}


def get_sa_obj_keys(sa_obj):
    return (prop.key for prop in inspect(sa_obj).mapper.column_attrs)



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
def add(db_path, csv_file, csv_flavor, account_name):
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

    add_transactions_from_dataframe(df)


cli.add_command(add)


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


if __name__ == '__main__':
    cli()
