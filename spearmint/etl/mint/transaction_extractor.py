from spearmint.etl.transaction_extractor import TransactionExtractor


class MintTransactionExtractor(TransactionExtractor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parse_dates_from = {self.parsed_name_map["datetime"]: ["Date"]}

    def _get_raw_amount(self):
        """
        Mint files have +ve values for all amounts and a debit/credit column to denote sign for amount.
        """
        temp_amount = self.df_raw["Amount"].copy()
        temp_amount.loc[self.df_raw["Transaction Type"] == 'debit'] = \
            -temp_amount.loc[self.df_raw["Transaction Type"] == 'debit']
        return temp_amount
