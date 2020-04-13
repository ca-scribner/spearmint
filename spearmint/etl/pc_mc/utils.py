import pandas as pd
import datetime

from spearmint.data.transaction import Transaction


ACCOUNT_NAME = "PC Financial"
DATETIME_COLUMN = "Date_Time"


def get_transactions(csv_file):
    raw = pd.read_csv(csv_file, parse_dates=[["Date", "Time"]])
    return [_row_dict_to_transaction(row_dict, csv_file) for row_dict in raw.to_dict("records")]


def _get_amount(row_dict):
    # All transactions in pc_mc are as +ve for charge, -ve for repayment.  Reverse them
    return -row_dict["Amount"]


def _row_dict_to_transaction(row_dict, source_file=None):
    transaction = Transaction(
        datetime=row_dict[DATETIME_COLUMN],
        description=row_dict["Description"],
        amount=_get_amount(row_dict),
        account_name=ACCOUNT_NAME,
    )
    if source_file:
        transaction.source_file = source_file

    return transaction









    # def _row_dict_to_transaction(self, row_dict, source_file=None):
    #     transaction = Transaction(
    #         datetime=row_dict[DATETIME_COLUMN],
    #         description=row_dict["Description"],
    #         amount=_get_amount(row_dict),
    #         account_name=ACCOUNT_NAME,
    #     )
    #     if source_file:
    #         transaction.source_file = source_file
    #     return transaction
    #
    #
    #
    #
    # def get_transactions(self):
    #     raise NotImplementedError