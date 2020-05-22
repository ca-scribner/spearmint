import sqlalchemy as sa
from sqlalchemy import Column, DateTime, String, Float, ForeignKey
import datetime as datetime_package

from spearmint.data.modelbase import SqlAlchemyBase
from spearmint.data.big_integer_type import BigIntegerType


class Category(SqlAlchemyBase):
    __tablename__ = "category"

    id: int = Column(BigIntegerType, primary_key=True, autoincrement=True)
    # raises when I typeset datetime to datetime.datetime.  Not sure why
    datetime: datetime_package.datetime = Column(DateTime)
    scheme: str = Column(String, nullable=False)
    confidence: float = Column(Float, nullable=False)
    category: str = Column(String, nullable=False)  # Should be index to category table

    transaction_id = Column(BigIntegerType, ForeignKey("transaction.id"))

    def __repr__(self):
        # TODO
        return "TODO"
               # f"Transaction id={self.id}; cat={self.category}; amount={self.amount}; desc={self.description}; " \
               # f"acct_name={self.account_name}; datetime={self.datetime}; source_file={self.source_file}"
