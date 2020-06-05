from collections import OrderedDict
from spearmint.data_structures.budget import Budget, BudgetCollection


def get_income_bc():
    income_subcategory_bc_dict = OrderedDict()

    # Income
    name = "Income"
    income_bc = BudgetCollection(name=name)
    # 2225 * 2 * 26 / 12 ~= 9650
    # Notes:
    # * This is month income after paying CPP/OAP contributions.
    #   The ~4 months that we don't pay is the equivalent of ~225/month extra
    # * This omits tax refunds from RRSP contributions.  Not sure how much this will be, but I THINK based on savings rates:
    #   Contribution = 9750/person --> $3125/person/year refund (assuming only our contributions outside work apply)
    #                                 =$ 520/month total
    # ... ~745/month (or more, depending on RRSP/other tax refunds) available but not in below income
    income_bc.add_budget(Budget(9650, ["Paycheck"]))
    income_bc.add_budget(Budget(0, ["Bonus"]))
    income_bc.add_budget(Budget(200, ["Parents and Gifts"]))
    income_bc.add_budget(Budget(0, ["Tutoring"]))
    income_bc.add_budget(Budget(50, ["Interest Income", "Unknown Income", "Credit Card Rewards"], name="Other"))

    return income_bc


def get_expense_bc():
    expenses_subcategory_bc_dict = OrderedDict()

    # Car
    name = "Car"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-125, ["Auto Insurance"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-100, ["Gas & Fuel"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-15, ["Parking"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-90, ["Public Transportation"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-125, ["Service & Parts"]))
    # expenses_subcategory_bc_dict[name].add_budget(Budget(-300, ["Vehicle Property Tax"], amount_type='Yearly')) # Is this a thing in Canada?

    # Utilities / Monthly Software
    name = "Utilities & Monthly Software"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-90, ["Electricity"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-56, ["Internet"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-170, ["Mobile Phone"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-23, ["Natural Gas"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-65, ["Software Services"], name="Software Servcices"))

    # Home
    name = "Home"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-75, ["Home Services", "Home Insurance"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-1850, ["Mortgage & Rent"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-50, ["House Hunt", "Moving"], name="Moving/House Hunt"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-150, ["Furnishings", "Home Improvement", "Home Supplies"], name="Home Impr_Furn_Supplies"))

    # Personal Upkeep
    name = "Personal Upkeep"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-66, ["Hair"], name="Hair-Heather"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-5, ["Hair (Andrew)"], name="Hair-Andrew"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-100, ["All Medical Expenses", "Life Insurance"], name="Life Ins & Medical"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-875, ["Groceries"]))

    # Entertainment
    name = "Entertainment"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-50, ["Amusement", "Movies & DVDs"], name="Fun Activities"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-175, ["Restaurants", "Fast Food"], name='Food Out'))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-30, ["Coffee Shops"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-40, ["Food at Work"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-50, ["Gift"]))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-225, ["Sports"]))

    # Purchases
    name = "Purchases"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-30, ["Books", "Hobbies"], name="Books, Hobbies, Non-Software"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-100, ["Clothing (Heather)"], name="Clothing-Heather"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-75, ["Clothing (Andrew)"], name="Clothing-Andrew"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-40, ["Electronics & Software"], name="Electr, Games, Tech"))

    # Travel
    name = "Travel"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-800, ["Big Trip Stuff", "Beach 2017", "Europe Trip 2016", "Vancouver 2017", "Hawaii 2018", "Vacation", "Colorado 2019"], name="Vacations"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-200, ["Trips Home"]))

    # Misc
    name = "Misc"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    expenses_subcategory_bc_dict[name].add_budget(Budget(-225, ["Tuition"], name="Educational Expenses"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-30, ["Work Expenses", "Office Supplies"], name="Work, Home Office, Edu"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-10, ["ATM Fee", "Bank Fee", "Fees & Charges", "Finance Charge", "Late Fee", "Tickets"], name="Fees and Charges"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-0, ["Federal Tax", "Taxes", "State Tax"], name="All Taxes"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-15, ["Passport, License .."], name="Passport, License, etc"))
    expenses_subcategory_bc_dict[name].add_budget(Budget(-15, ["Cash & ATM", "Unknown Expense"], name="Unknown - Cash, etc"))

    # Extra Savings
    name = "Extra Savings"
    expenses_subcategory_bc_dict[name] = BudgetCollection(name=name)
    # Target 25% of total gross (180000) into savings, including pension contributions:
    # - Heather 3% total ((3% deduction + 3% match) / 2 (single salary)) <-- RRSP'd Savings
    # - Andrew ~4.5% (8.x on amount below ~60k, 10.x above / 2 (single salary)) <-- Pension (doesn't account for gov portion)
    # ... ~17.5% remaining -> ~2625/month
    # ... Contributed as:
    #           TFSA: $6000 each (~6.67% of gross)
    #           RRSP: $9750 each (~10.83% of gross) <--might not be even due to RRSP contributions
    expenses_subcategory_bc_dict[name].add_budget(Budget(-2625, ["Investment Transfer"], name="TFSA & RRSP"))

    # When do I need this?  Probably a relic from old way of organizing things
    expenses_subcategory_bc = BudgetCollection(name="Subcategorized Expenses")
    for name, bc in expenses_subcategory_bc_dict.items():
        expenses_subcategory_bc.extend(bc)
    # expenses_subcategory_bc.display()

    # Now build object one level up
    expenses_category_bc = BudgetCollection(name="Expenses")

    for name in expenses_subcategory_bc_dict:
        expenses_category_bc.add_budget(expenses_subcategory_bc_dict[name])
    # expenses_category_bc.display(categories=False)
    return expenses_category_bc


def get_excluded_bc():
    excluded_bc = BudgetCollection("Excluded Transactions")
    excluded_bc.add_budget(Budget(0, ['Transfer', 'Credit Card Payment', 'IGNORE_IN_MENTHOL', "House Sale",
                                      "Property Tax", "HOA Fees", "Auto Payment"]))
    return excluded_bc


if __name__ == '__main__':
    income_bc = get_income_bc()
    income_bc.display()

    expense_bc = get_expense_bc()
    expense_bc.display()

    print(expense_bc.categories)
    import pprint
    pprint.pprint(expense_bc.categories_flat_dict)