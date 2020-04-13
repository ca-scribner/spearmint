import pandas as pd
import os


PARSED_NAME_MAP = {
    "amount": "Amount",
    "datetime": "Datetime",
    "description": "Description",
    "account_name": "Account Name",
    "source_file": "Source File",
}

RAW_NAME_MAP = dict(PARSED_NAME_MAP)


class TransactionExtractor():

    def __init__(self):
        self.df = None
        self.source_file = None

        # Column names used for output parsed dataframe (self.df)
        # Without dict(), would these be references to the mutable global, effectively making them class variables that
        # can not be edited locally?  I think so?
        self.parsed_name_map = dict(PARSED_NAME_MAP)
        self.raw_name_map = dict(RAW_NAME_MAP)

        # Column(s) to parse the datetime column from.  Passed to pandas.read_csv
        # Can be overridden in subclasses
        self.parse_dates_from = [self.parsed_name_map["datetime"]]

    def to_dataframe(self, deep=True):
        return self.df.copy(deep=deep)

    def populate_from_csv(self, source_file):
        self.source_file = source_file
        self.df_raw = pd.read_csv(source_file, parse_dates=self.parse_dates_from)
        self._parse_raw_df()

    def _parse_raw_df(self):
        data = {
            self.parsed_name_map["amount"]: self._get_raw_amount(),
            self.parsed_name_map["description"]: self._get_raw_description(),
            self.parsed_name_map["datetime"]: self._get_raw_datetime(),
            self.parsed_name_map["account_name"]: self._get_raw_account_name(),
            self.parsed_name_map["source_file"]: self._get_raw_source_file(),
        }

        self.df = pd.DataFrame(data)

    @classmethod
    def read_csv(cls, source_file):
        te = cls()
        te.populate_from_csv(source_file)
        return te

    # Internal methods for getting data from a raw file.  Meant to be overridden by subclasses to implement custom
    # parsing behaviour
    # Must return data series with the requested data
    # TODO: docstrings
    def _get_raw_amount(self):
        return self.df_raw[self.raw_name_map["amount"]]

    def _get_raw_description(self):
        return self.df_raw[self.raw_name_map["description"]]

    def _get_raw_datetime(self):
        return self.df_raw[self.raw_name_map["datetime"]]

    def _get_raw_account_name(self):
        return self.df_raw[self.raw_name_map["account_name"]]

    def _get_raw_source_file(self):
        return os.path.basename(self.source_file)
