import sqlalchemy as sa
from sqlalchemy import Column, DateTime, String, Float, ForeignKey
from sqlalchemy.orm import relationship
import datetime as datetime_package

from spearmint.data.modelbase import SqlAlchemyBase
from spearmint.data.big_integer_type import BigIntegerType


class Transaction(SqlAlchemyBase):
    # TODO: Enforce types.  I think I had a pattern from this in the pypi?
    __tablename__ = "transaction"

    id: int = Column(BigIntegerType, primary_key=True, autoincrement=True)
    datetime: datetime_package.datetime = Column(DateTime)  # raises when I typeset datetime to datetime.datetime.  Not sure why
    description: str = Column(String)
    amount: float = Column(Float)
    account_name: str = Column(String, index=True)  # Could be index to account table
    source_file: str = Column(String)  # Could be index of source_file table

    # Sets a uni-directional relation.  We will know a single (uselist=False) accepted category, accessible as an object
    # in python via .category, but that Category won't know we are using it.
    category_id: int = Column(BigIntegerType, ForeignKey("category.id"))
    category = relationship("Category",
                            uselist=False,  # one-to-one
                            foreign_keys=[category_id]
                            )

    # Sets a bi-directional relation.  suggested_categories here will have category objects, while each label object will
    # record which transaction they're a suggestion for by having a .transaction_id.  Because Transaction has two
    # uses of the Transaction foreign key, we need to set the primaryjoin arg explicitly (primaryjoin is implicitly
    # set by sqlalchemy when it is not ambiguous)
    # Because a Transaction points to a Category and that same Category points to the same Transaction, we cannot add them
    # using only two INSERT statements (to add one requires the other to already exist and have its primary key).
    # To get around this, use the method from
    #   https://docs.sqlalchemy.org/en/13/orm/relationship_persistence.html#post-update,
    # as referenced in
    #   https://stackoverflow.com/questions/18284464/sqlalchemy-exc-circulardependencyerror-circular-dependency-detected
    # We set post_update=True, which tells sqlalchemy to INSERT both with empty references, then do an UPDATE to
    # populate the references.  THey also mention this is prefereably done from the many side of a many to one relation,
    # so I think they'd prefer the relationship was defined from the category side?  Can redo later...
    categories_suggested_id: int = Column(BigIntegerType, ForeignKey("category.id"))
    categories_suggested: list = relationship("Category",
                                              backref="transaction",  # this trx is acccessible via label.transaction attr
                                              primaryjoin="Transaction.id==Category.transaction_id",  # unambiguous relation
                                              post_update=True,  # Because circular reference
                                              )


    def __repr__(self):
        try:
            category = self.category.category
        except AttributeError:
            if self.category:
                category = "(PRESENT)"
            else:
                category = "None"
        return f"Transaction id={self.id}; category={category}; amount={self.amount}; " \
               f"desc={self.description}; acct_name={self.account_name}; datetime={self.datetime}; " \
               f"source_file={self.source_file}, len(categories_suggested)={len(self.categories_suggested)}"
