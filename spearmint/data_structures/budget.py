from typing import Union, Tuple, List

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

    def get_budget_by_name(self, name, recurse=True):
        """
        Returns the Budget or BudgetCollection named name in this BudgetCollection if it exists, else raises KeyError.

        Optionally check for nested budgets.

        Note that there is no checking in place to prevent multiple budgets of the same name.  This will return the
        first budget of the requested name found according to:
            -   checking all the direct children of this BudgetCollection in order they were added
            -   (returse=True) depth-first search of the direct children of this BudgetCollection (search the first
                completely beore checking the second, ...)

        Args:
            name (str): Name of budget to look for
            recurse (bool): If true, search children BudgetCollections for this budget as well

        Returns:
            (Budget or None)
        """
        for b in self.get_budgets():
            if b.name == name:
                return b
            else:
                if recurse:
                    try:
                        # If successful, we can return what we get from recursion
                        return b.get_budget_by_name(name, recurse)
                    except (AttributeError, KeyError):
                        # Otherwise, we continue looking elsewhere
                        # AttributeError: This is a Budget not a BudgetCollection
                        # KeyError: This BudgetCollection doesn't have what we want...
                        pass

        # If we get to the end, we found nothing
        raise KeyError("Cannot find budget named '{name}'")

    def get_leaf_budgets(self):
        """
        Returns a list of the leaf budgets (budgets at the lowest level in this collection)
        """
        leaf_budgets = []
        for b in self.get_budgets():
            try:
                leaf_budgets.extend(b.get_leaf_budgets())
            except AttributeError:
                # No deeper budgets
                leaf_budgets.append(b)
        return leaf_budgets

    def slice_by_budgets(self, budgets: Union[Tuple, List] = tuple()):
        """
        Returns a new BudgetCollection that is a flat subset of the current BudgetCollection

        Only budgets called out by name in the budgets iterable are included in the returned BC

        Args:
            budgets (Iterable): Iterable of string budget names to be included in the return.  Defaults to an empty
                                tuple

        Returns:
            (BudgetCollection)
        """
        new_bc = BudgetCollection(self.name)
        bs = [b for b in self.get_leaf_budgets() if b.name in budgets]
        for b in bs:
            new_bc.add_budget(b)
        return new_bc

    def flatten(self):
        """
        Returns a new BudgetCollection composed of all the leaf budgets in the current collection.

        This BudgetCollection will cover the same categories as the original BudgetCollection, but will not have the
        hierarchy
        """
        bc = BudgetCollection(self.name)
        for b in self.get_leaf_budgets():
            bc.add_budget(b)
        return bc

    def aggregate_categories_to_budget(self, categories):
        """
        Returns the budget name that corresponds to each category provided and None if a category is not in the BC.

        If any element of categories is missing from the BudgetCollection's budget, it is returned as None

        Args:
            categories: List of category names to be aggregated into budget names.

        Returns:
            TODO
            (list?)
        """
        category_to_budget = {}

        for b in self.get_leaf_budgets():
            for c in b.categories:
                category_to_budget[c] = b.name

        budgets = [category_to_budget.get(c, None) for c in categories]
        return budgets
        #
        # # Find all the lowest budget:category mapping
        # to_search = self.get_budgets()
        # while to_search:
        #     b = to_search.pop()
        #     try:
        #         to_search.extend(b.get_budgets())
        #     except AttributeError:
        #         budget_to_category[b] = b.categories


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

    def __eq__(self, other):
        try:
            return (self.name == other.name and
                    self.budgets == other.budgets
                    )
        except:
            return False


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

    def __eq__(self, other):
        try:
            return ((self.categories == other.categories) and
                    (self.amount == other.amount) and
                    (self.name == other.name)
                    )
        except:
            return False

    def __str__(self):
        """
        Return a string representation of the Budget
        :return: String
        """
        return self.to_str()