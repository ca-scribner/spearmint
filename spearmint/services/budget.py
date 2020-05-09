from spearmint.services.mock_budget_data import budget_definition


def get_income_budget_collection():
    return budget_definition.get_income_bc()


def get_expense_budget_collection():
    return budget_definition.get_expense_bc()
