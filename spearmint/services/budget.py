from spearmint.data_structures.budget import BudgetCollection
from spearmint.services.mock_budget_data import budget_definition


def get_income_budget_collection():
    return budget_definition.get_income_bc()


def get_expense_budget_collection():
    return budget_definition.get_expense_bc()


def get_excluded_budget_collection():
    return budget_definition.get_excluded_bc()


def get_unbudgeted_categories(categories):
    """
    Returns list of category names that are present in the categories passed, but are not represented in this budget

    Args:
        categories (list): List of string category names to assess whether they're in the budget

    Returns:
        (list): Elements of categories not in this budget
    """
    expenses = get_expense_budget_collection()
    incomes = get_income_budget_collection()
    exclusions = get_excluded_budget_collection()
    budgeted = expenses.categories + incomes.categories + exclusions.categories

    unbudgeted = [c for c in categories if c not in budgeted]
    return unbudgeted


def get_overall_budget_collection():
    """
    Returns a BudgetCollection that includes Income, Expense, and Excluded transactions
    """
    bc = BudgetCollection(name="Overall")
    bc.add_budget(get_income_budget_collection())
    bc.add_budget(get_expense_budget_collection())
    bc.add_budget(get_excluded_budget_collection())
    return bc
