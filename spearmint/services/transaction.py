from typing import List

import click

from spearmint.data.db_session import create_session, global_init
from spearmint.data.transaction import Transaction
from spearmint.etl.transaction_extractor import PARSED_NAME_MAP
from spearmint.etl.transaction_extractor import TransactionExtractor
from spearmint.etl.mint.transaction_extractor import MintTransactionExtractor
from spearmint.etl.pc_mc.transaction_extractor import PcMcTransactionExtractor


def dataframe_to_transactions(df, column_name_map=PARSED_NAME_MAP):
    return [_row_dict_to_transaction(row_dict, column_name_map) for row_dict in df.to_dict("records")]


def _row_dict_to_transaction(row_dict, column_name_map):
    transaction = Transaction(
        datetime=row_dict[column_name_map["datetime"]],
        description=row_dict[column_name_map["description"]],
        amount=row_dict[column_name_map["amount"]],
        account_name=row_dict[column_name_map["account_name"]],
        source_file=row_dict[column_name_map["source_file"]],
        category=row_dict[column_name_map["category"]],
    )
    return transaction


def add_transactions_from_dataframe(df):
    transactions = dataframe_to_transactions(df)

    s = create_session()
    s.add_all(transactions)
    s.commit()
    s.close()


def find_transactions_without_category() -> List[Transaction]:
    s = create_session()
    # transactions = s.query(Transaction).all()
    transactions = s.query(Transaction).filter(Transaction.category.is_(None)).all()
    s.close()
    return transactions


def find_transaction_by_id(transaction_id) -> Transaction:
    s = create_session()
    trx = s.query(Transaction).filter(Transaction.id == transaction_id).first()
    s.close()
    return trx


def find_all_transactions() -> List[Transaction]:
    s = create_session()
    trxs = s.query(Transaction).all()
    s.close()
    return trxs


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
        db_path (str): String path to the database to add transactions to \n
        csv_file (str): String path to the csv file to load and extract transactions from\n
        csv_flavor (str): One of:\n
            mint: Mint-formatted csv file\n
            pc_mc: PC Mastercard formatted csv file\n
    """
    # Initialize db connection
    global_init(db_path)

    df = import_csv_as_df(csv_file, csv_flavor, account_name)

    add_transactions_from_dataframe(df)


cli.add_command(add)


def import_csv_as_df(csv_file, csv_flavor, account_name=None):
    if csv_flavor == "pc_mc":
        te = PcMcTransactionExtractor.read_csv(csv_file, account_name=account_name)
    elif csv_file == "mint":
        te = MintTransactionExtractor.read_csv(csv_file)
    elif csv_file == "base":
        te = TransactionExtractor.read_csv(csv_file)
    else:
        raise ValueError(f"Unknown csv_flavor '{csv_flavor}'")
    return te.to_dataframe(deep=True)


if __name__ == '__main__':
    cli()
