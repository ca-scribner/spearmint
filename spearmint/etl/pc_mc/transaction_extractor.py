from spearmint.etl.transaction_extractor import TransactionExtractor


class PcMcTransactionExtractor(TransactionExtractor):

    def __init__(self, account_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_name = account_name

        self.parse_dates_from = {self.name_map["datetime"]: ["Date", "Time"]}

    def _get_raw_amount(self):
        return -self.df_raw[self.name_map["amount"]]

    def _get_raw_account_name(self):
        return self.account_name
