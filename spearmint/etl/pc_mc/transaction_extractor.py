from spearmint.etl.transaction_extractor import TransactionExtractor


class PcMcTransactionExtractor(TransactionExtractor):

    def __init__(self, account_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_name = account_name

        self.parse_dates_from = {self.column_datetime: ["Date", "Time"]}

    def get_amount(self, row_dict):
        return -row_dict[self.column_amount]

    def get_account_name(self, row_dict):
        return self.account_name
