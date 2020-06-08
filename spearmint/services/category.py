import click

from spearmint.data.category import Category
from spearmint.data.db_session import create_session, global_init
from spearmint.data.transaction import Transaction


def get_category_by_id(id: int) -> Category:
    """
    Returns the category with a given id

    Args:
        id:

    Returns:
        Category
    """
    s = create_session()
    q = s.query(Category).filter(Category.id == id)
    categories = q.all()
    if len(categories) == 1:
        return categories[0]
    else:
        raise ValueError(f"Could not find category with id={id}")


def get_categories(scheme=None):
    """
    Returns all category entries, optionally filtered

    Args:
        scheme (str): Scheme name to match

    Returns:
        List of Category instances
    """
    s = create_session()
    q = s.query(Category)
    if scheme:
        q = q.filter(Category.scheme == scheme)
    s.close()
    return q.all()


def get_accepted_categories():
    s = create_session()
    accepted_categories = s.query(Category).filter(Category.id.in_(s.query(Transaction.category_id))).all()
    s.close()
    return accepted_categories


def accept_current_chosen_categories(scheme="accepted"):
    """
    Moves all categories used by Transaction.category to the "accepted" scheme, removing any stale "accepted" categories

    Stale "accepted" categories are any categories in the accepted scheme now that are no longer attached to a
    Transaction.category

    Args:
        scheme (str): Scheme name for the "accepted" scheme

    Side Effects:
        Removes all categories in scheme that are no longer accepted
        Modifies all categories that are accepted to now be in the accepted scheme

    Returns:
        None
    """
    accepted_categories = get_accepted_categories()
    print(f"len(accepted_categories) = {len(accepted_categories)}")

    # Update anything that is accepted to the accepted scheme
    s = create_session()
    for c in accepted_categories:
        c.scheme = scheme
        s.merge(c)
        # s.add(c)
    s.commit()
    print("updated accepted schemes")

    # Remove anything that is in the accepted scheme but is no longer accepted
    stale_accepted = (s.query(Category)
                       .filter(Category.scheme == scheme)
                       .filter(Category.id.notin_(s.query(Transaction.category_id)))
                       .all())
    print(f"len(stale_accepted) = {len(stale_accepted)}")
    for c in stale_accepted:
        s.delete(c)
    s.commit()
    print("Deleted stale")


@click.group()
def cli():
    pass


@click.command()  # Can specify help here, or if blank will use docstring
@click.argument("DB_PATH")
@click.argument("scheme")
def accept_current(db_path, scheme):
    """
    Moves all categories used by Transaction.category to the "accepted" scheme, removing any stale "accepted" categories

    Stale "accepted" categories are any categories in the accepted scheme now that are no longer attached to a
    Transaction.category

    Args:
        db_path (str): Path to the DB to be edited
        scheme (str): Scheme name for the "accepted" scheme

    Side Effects:
        Removes all categories in scheme that are no longer accepted
        Modifies all categories that are accepted to now be in the accepted scheme

    Returns:
        None
    """
    # Initialize db connection
    global_init(db_path, False)
    accept_current_chosen_categories(scheme)


cli.add_command(accept_current)


if __name__ == '__main__':
    cli()
