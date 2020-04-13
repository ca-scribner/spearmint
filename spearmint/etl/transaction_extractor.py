import pandas as pd

from spearmint.data.transaction import Transaction


COLUMN_NAME_MAP = {
    "amount": "Amount",
    "datetime": "Datetime",
    "description": "Description",
    "account_name": "Account Name",
    "filename": "Source File",
}


class TransactionExtractor():

    def __init__(self):
        self.df = None
        self.filename = None

        # Column names used for output parsed dataframe (self.df)
        self.name_map = COLUMN_NAME_MAP

        # Column(s) to parse the datetime column from.  Passed to pandas.read_csv
        # Can be overridden in subclasses
        self.parse_dates_from = [self.name_map["datetime"]]

    def get_dataframe(self, deep=True):
        return self.df.copy(deep=deep)

    def populate_from_csv(self, filename):
        self.filename = filename
        self.df_raw = pd.read_csv(filename, parse_dates=self.parse_dates_from)
        self._parse_raw_df()

    def _parse_raw_df(self):
        data = {
            self.name_map["amount"]: self._get_raw_amount(),
            self.name_map["description"]: self._get_raw_description(),
            self.name_map["datetime"]: self._get_raw_datetime(),
            self.name_map["account_name"]: self._get_raw_account_name(),
            self.name_map["filename"]: self._get_raw_filename(),
        }

        self.df = pd.DataFrame(data)

    @classmethod
    def read_csv(cls, filename):
        te = cls()
        te.populate_from_csv(filename)
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

    def _get_raw_filename(self):
        return self.filename
