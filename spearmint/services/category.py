from spearmint.data.category import Category
from spearmint.data.db_session import create_session


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
