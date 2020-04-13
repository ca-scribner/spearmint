from spearmint.data.transaction import Transaction
from spearmint.etl.transaction_extractor import PARSED_NAME_MAP


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
