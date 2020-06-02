from spearmint.data.category import Category
from spearmint.data.db_session import create_session


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
    return q.all()
