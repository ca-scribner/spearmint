DEFAULT_BUDGET_COLLECTION_NAME = "Unnamed Budget"

# FUTURE: Put an ABC above Budget and BudgetCollection to enforce the commonalities in API?

class BudgetCollection:
    """
    Collection of Budget objects
    """
    def __init__(self, name=None):
        """
        Initialize empty BudgetCollection
        """
        self.budgets = []
        self.name = name if name else DEFAULT_BUDGET_COLLECTION_NAME

    @property
    def amount(self):
        total = 0
        for b in self.get_budgets():
            total += b.amount
        return total

    @property
    def categories(self):
        """
        FUTURE: Could cache this instead if I don't want to always traverse.  Then update whenever we add_budget
        """
        categories = []
        for b in self.budgets:
            categories.extend(b.categories)
        return categories

    @property
    def categories_flat_dict(self):
        """
        Returns a flat dict of the nested structure of all categories in the BudgetCollection

        Ex:
            {
                "Item-1": ["Item-1-1", "Item-1-2", ...],
                "Item-1-1": ["Item-1-1-1", "Item-1-1-2", ...],
                ...
            }
        """
        categories = {self.name: [b.name for b in self.budgets]}
        for b in self.budgets:
            try:
                deeper_categories = b.categories_flat_dict
                categories.update(deeper_categories)
            except AttributeError:
                # Recursing on something that doesn't have categories to report.  Don't go deeper
                pass

        return categories


    def add_budget(self, b, raise_on_duplicate_categories=True):
        """
        Add a Budget to the collection, optionally raising if this budget overlaps an existing category

        FUTURE: I think this can also take a BudgetCollection object and work transparently.  Need to test
            They might mess with .to_str().
        Args:
            b (Budget):
            raise_on_duplicate_categories (bool): If True, raise if b has a category already included in this collection

        Returns:
            None
        """
        if raise_on_duplicate_categories:
            known_categories = set(self.categories)
            for cat in b.categories:
                if cat in known_categories:
                    raise ValueError("Budget {b} has category {cat} that is already in this BudgetCollection")
        self.budgets.append(b)

    def get_budgets(self):
        return self.budgets

    def extend(self, bs):
        """
        Extend this BudgetCollection by adding all Budget objects from another BudgetCollection to this one

        This means the contents of bs

        Args:
            bs (BudgetCollection): Another BudgetCollection instance

        Returns:
            None
        """
        for b in bs.get_budgets():
            self.add_budget(b)

    # Original code had:
    # def add_budgets:

    def to_str(self, amount=True, categories=True, total=True, header=True):
        """
        Convert Budgets instance to a string summary, optionally including amount and/or categories

        :param amount: Boolean
        :param categories: Boolean
        :param total: Boolean
        :return: Formatted string of Budgets instance
        """
        ret = ""
        if header:
            ret = f"{self.name}\n"
        for i, b in enumerate(self.get_budgets()):
            if i > 0:
                ret += "\n"
            # Handle both cases of child Budget and BudgetCollection
            try:
                ret += b.to_str(amount=amount, categories=categories, total=False, header=False)
            except TypeError:
                ret += b.to_str(amount=amount, categories=categories)
        if total:
            line = "-".join([""]*31)
            ret += f"\n{line}"
            ret += f"\n{'Total':30s} | ${self.amount:>8.2f}"
        return ret

    def display(self, amount=True, categories=True):
        """
        Display to screen the contents of this object
        :return: None
        """
        print(self.to_str(amount=amount, categories=categories))


class Budget:
    def __init__(self, amount, categories, name=None, amount_type="Monthly"):
        """
        Initialize Budget instance

        :param amount: Monthly budgeted dollar amount of spending
        :param categories: List of categories to include in budget
        :param amount_type: Specifies how amount is specified, eg:
                                Monthly: X dollars per month
                                Yearly: X dollars per year (converted internally to monthly)
        """
        self.categories = categories
        if amount_type == "Yearly":
            amount = amount / 12.0
        elif amount_type == "Monthly":
            pass
        else:
            raise ValueError("Invalid value for amount_type ('{0}')".format(amount_type))
        self.amount = amount
        if name is None:
            self.name = ", ".join(self.categories)
        else:
            self.name = name

    def to_str(self, amount=True, categories=True):
        """
        Return a string representation of the Budget, optionally including some pieces
        :return:
        """
        ret = f"{self.name:30s}"
        if amount:
            ret += f" | ${self.amount:>8.2f}"
        if categories:
            ret += f" | {str(self.categories)}"
        return ret

    def __str__(self):
        """
        Return a string representation of the Budget
        :return: String
        """
        return self.to_str()