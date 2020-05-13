from spearmint.data_structures.budget import BudgetCollection, Budget
import pytest


def sample_b():
    categories = [f"c{i}" for i in range(5)]
    amount = 20
    b = Budget(amount, categories, name='test budget')
    return {'b': b,
            'categories': categories
            }


def sample_bc():
    n_budgets = 6
    n_leaves_per_budget = 2

    budgets = [Budget(i, [f"category_{i}-{j}" for j in range(n_leaves_per_budget)], name=f"budget-{i}") for i in range(n_budgets)]

    bc_even = BudgetCollection("even")
    bc_odd = BudgetCollection("odd")
    bc_flat = BudgetCollection("flat")

    for b in budgets[::2]:
        bc_even.add_budget(b)
        bc_flat.add_budget(b)

    for b in budgets[1::2]:
        bc_odd.add_budget(b)
        bc_flat.add_budget(b)

    bc = BudgetCollection("top")
    bc.add_budget(bc_even)
    bc.add_budget(bc_odd)

    leaf_categories = [f"category_{i}-{j}" for i in range(n_budgets) for j in range(n_leaves_per_budget) ]
    leaf_budgets = bc_even.budgets + bc_odd.budgets

    return {
        'bc_even': bc_even,
        'bc_odd': bc_odd,
        'bc_flat': bc_flat,
        'bc': bc,
        'leaf_categories': leaf_categories,
        'leaf_budgets': leaf_budgets,
        'budgets': budgets,
    }


def test_budget_collection_get_leaf_budgets():
    sample = sample_bc()
    bc = sample['bc']
    leaf_budgets_expected = sample['leaf_budgets']

    leaves = bc.get_leaf_budgets()

    assert leaf_budgets_expected == leaves


def test_budget_collection_flatten():
    sample = sample_bc()
    bc = sample['bc']
    bc_flat_expected = sample['bc_flat']

    bc_flat = bc.flatten()

    assert len(bc_flat.budgets) == 6
    assert bc_flat.budgets == bc_flat_expected.budgets


def test_budget_collection_slice_by_budgets():
    sample = sample_bc()
    bc = sample['bc']
    bc_flat = sample['bc_flat']
    bc_even_expected = sample['bc_even']

    bc_sliced_full = bc.slice_by_budgets([b.name for b in bc_flat.budgets])
    bc_sliced_full.name = 'flat'  # Rename for comparison
    assert bc_sliced_full == bc_flat

    bc_even = bc.slice_by_budgets([b.name for b in bc_even_expected.budgets])

    assert bc_even_expected.categories == bc_even.categories


def test_budget_collection_aggregate_categories_to_budget():
    sample = sample_bc()
    bc = sample['bc']
    leaf_categories = sample['leaf_categories']
    mapped_expected = [f'budget-{i}' for i in range(6) for _ in range(2)]

    budgets = bc.aggregate_categories_to_budget(leaf_categories)
    assert mapped_expected == budgets

    mapped_with_empties = mapped_expected + [None, None, None]
    leaf_categories_with_empties = leaf_categories + ["Not a cat", "Neither am I", "Am I?  No..."]
    budgets = bc.aggregate_categories_to_budget(leaf_categories_with_empties)
    assert mapped_with_empties == budgets


def test_budget_collection_get_budget_by_name():
    sample = sample_bc()
    bc = sample['bc']
    budgets = sample['budgets']
    bc_even = sample['bc_even']

    # Test grabbing a BC from a BC by name (BC requested is a direct child)
    assert bc.get_budget_by_name(bc_even.name) == bc_even

    # Test grabbing a Budget from a BC by name (Budget requested is a grandchild)
    assert bc.get_budget_by_name(budgets[0].name) == budgets[0]

    # Test grabbing a Budget that does not exist from a BC by name
    with pytest.raises(KeyError):
        bc.get_budget_by_name("not a budget")


def test_budget_aggregate_categories_to_budget():
    sample = sample_b()
    categories = sample['categories']
    b = sample['b']

    assert [b.name] * len(categories) == b.aggregate_categories_to_budget(categories)
    assert [b.name] * len(categories) + [None, None] == b.aggregate_categories_to_budget(
        categories + ["not a category", "also not a category"]
    )
