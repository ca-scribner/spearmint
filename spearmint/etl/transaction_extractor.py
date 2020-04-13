import pandas as pd

from spearmint.data.transaction import Transaction


COLUMN_NAME_MAP = {
    "amount": "Amount",
    "datetime": "Datetime",
    "description": "Description",
    "account_name": "Account Name",
    "source_file": "Source File",
}


class TransactionExtractor():

    def __init__(self):
        self.df = None
        self.source_file = None

        # Column names used for output parsed dataframe (self.df)
        self.name_map = COLUMN_NAME_MAP

        # Column(s) to parse the datetime column from.  Passed to pandas.read_csv
        # Can be overridden in subclasses
        self.parse_dates_from = [self.name_map["datetime"]]

    def get_dataframe(self, deep=True):
        return self.df.copy(deep=deep)

    def populate_from_csv(self, source_file):
        self.source_file = source_file
        self.df_raw = pd.read_csv(source_file, parse_dates=self.parse_dates_from)
        self._parse_raw_df()

    def _parse_raw_df(self):
        data = {
            self.name_map["amount"]: self._get_raw_amount(),
            self.name_map["description"]: self._get_raw_description(),
            self.name_map["datetime"]: self._get_raw_datetime(),
            self.name_map["account_name"]: self._get_raw_account_name(),
            self.name_map["source_file"]: self._get_raw_source_file(),
        }

        self.df = pd.DataFrame(data)

    @classmethod
    def read_csv(cls, source_file):
        te = cls()
        te.populate_from_csv(source_file)
        return te

    # Internal methods for getting data from a raw file.  Meant to be overridden by subclasses to implement custom
    # parsing behaviour
    def _get_raw_amount(self):
        return self.df_raw[self.name_map["amount"]]

    def _get_raw_description(self):
        return self.df_raw[self.name_map["description"]]

    def _get_raw_datetime(self):
        return self.df_raw[self.name_map["datetime"]]

    def _get_raw_account_name(self):
        return self.df_raw[self.name_map["account_name"]]

    def _get_raw_source_file(self):
        return self.source_file
