import sqlalchemy as sa
import datetime as datetime_package

from spearmint.data.modelbase import SqlAlchemyBase
from spearmint.data.big_integer_type import BigIntegerType


class Transaction(SqlAlchemyBase):
    # TODO: Enforce types.  I think I had a pattern from this in the pypi?
    __tablename__ = "transaction"

    id: int = sa.Column(BigIntegerType, primary_key=True, autoincrement=True)
    datetime: datetime_package.datetime = sa.Column(sa.DateTime)  # raises when I typeset datetime to datetime.datetime.  Not sure why
    description: str = sa.Column(sa.String)
    amount: float = sa.Column(sa.Float)
    category: str = sa.Column(sa.String, index=True)  # Should be index to category table
    account_name: str = sa.Column(sa.String, index=True)  # Could be index to account table
    source_file: str = sa.Column(sa.String)  # Could be index of source_file table

    def __repr__(self):
        return f"Transaction id={self.id}; cat={self.category}; amount={self.amount}; desc={self.description}; " \
               f"acct_name={self.account_name}; datetime={self.datetime}; source_file={self.source_file}"
