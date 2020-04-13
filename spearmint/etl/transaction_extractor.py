import pandas as pd

from spearmint.data.transaction import Transaction


class TransactionExtractor():

    def __init__(self):
        self.df = None
        self.filename = None

        self.column_amount = "Amount"
        self.column_datetime = "Datetime"
        self.column_description = "Description"
        self.column_account_name = "Account Name"

        # Column(s) to parse the datetime column from.  Passed to pandas.read_csv
        self.parse_dates_from = [self.column_datetime]

    def get_transactions(self):
        return [self._row_dict_to_transaction(row_dict) for row_dict in self.df.to_dict("records")]

    def populate_from_csv(self, filename):
        self.filename = filename
        self.df = pd.read_csv(filename, parse_dates=self.parse_dates_from)


    @classmethod
    def read_csv(cls, filename):
        te = cls()
        te.populate_from_csv(filename)
        return te

    def get_amount(self, row_dict):
        return row_dict[self.column_amount]

    def get_description(self, row_dict):
        return row_dict[self.column_description]

    def get_datetime(self, row_dict):
        return row_dict[self.column_datetime]

    def get_account_name(self, row_dict):
        return row_dict[self.column_account_name]

    def _row_dict_to_transaction(self, row_dict):
        transaction = Transaction(
            datetime=self.get_datetime(row_dict),
            description=self.get_description(row_dict),
            amount=self.get_amount(row_dict),
            account_name=self.get_account_name(row_dict),
            source_file=self.filename,
        )
        return transaction
