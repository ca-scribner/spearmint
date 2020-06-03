import click
import joblib
import pandas as pd

from spearmint.classifiers.common_usage_classifier import CommonUsageClassifier
from spearmint.classifiers.lookup_classifier import LookupClassifier
from spearmint.data.category import Category
from spearmint.data.db_session import create_session, global_init
from spearmint.data.transaction import Transaction
from spearmint.services.category import get_categories
from spearmint.services.transaction import get_transactions_without_category, get_transactions, \
    transactions_to_dataframe


def classify_by_model(scheme, clf, if_scheme_exists="replace", n_classifications_per_trx=3):
    """
    Classifies transactions in the DB, putting these classifications into the DB as suggested categories

    Args:
        scheme (str): Scheme name to use for suggested categories
        clf: classification model that has a .predict method for turning descriptions into categories
        if_scheme_exists (str): One of:
                                    replace: Removes all existing classifications with scheme==scheme and then commits
                                             the new classifications
                                    raise: Raises a ValueError if any transactions already have suggested categories
                                           with this scheme
                                    ignore: Does nothing (these transactions will then be "added" to the existing ones
                                            in the same scheme)
        n_classifications_per_trx (int): Maximum number suggested categories to create per transactions

    Side Effects:
        db suggested categories table is updated

    Returns:
        None
    """
    if if_scheme_exists == 'raise':
        if get_categories(scheme=scheme):
            raise ValueError("Scheme already in use")
        else:
            suggested_to_delete = []
    elif if_scheme_exists == 'ignore':
        suggested_to_delete = []
    elif if_scheme_exists == 'replace':
        # Get all suggested categories already in this scheme.  If the classification goes successfully, we will remove
        # these records
        # TODO: Delay this till after clf but before committing new categories?
        suggested_to_delete = [s.id for s in get_categories(scheme=scheme)]
    else:
        raise ValueError(f"Invalid value for if_scheme_exists '{if_scheme_exists}")

    trxs = get_transactions()

    df_trxs = transactions_to_dataframe(trxs)

    # TODO: Need to change the CommonUsageClassifier to use the sklearn standards...
    if isinstance(clf, CommonUsageClassifier):
        predictions = clf.predict(df_trxs['description'], n=n_classifications_per_trx)
    else:
        if n_classifications_per_trx != 1:
            raise NotImplementedError(f"n_classifications_per_trx for general models not yet implemented")
        predictions = clf.predict(df_trxs['description'])
        predictions = pd.DataFrame(predictions, index=df_trxs['description'])
    category_objs_by_trx = predictions_to_category_objs(predictions, scheme=scheme)

    for trx, this_category_list in zip(trxs, category_objs_by_trx):
        trx.categories_suggested.extend(this_category_list)

    s = create_session()
    # This requires a separate insert per category, but bulk_save_objects() doesn't work across relationships.  To speed
    # this up, I'd have to build my own logic for inserting things separately as bulk ops and then updating them
    # accordingly(?).  But thankfully the scale I need now is fine as is.
    s.add_all(trxs)
    s.commit()

    # Remove old categories that shouldn't be there anymore
    if suggested_to_delete:
        # Delete, avoiding the ORM because it'll do each delete separately!
        delete_q = Category.__table__.delete().where(Category.id.in_(suggested_to_delete))
        s.execute(delete_q)
        s.commit()


def classify_by_most_common(scheme, if_scheme_exists="replace", n_classifications_per_trx=3):
    """
    Adds suggested categories to all transactions in database under scheme name scheme

    Args:
        scheme (str): Scheme name to use for suggested categories
        if_scheme_exists (str): One of:
                                    replace: Removes all existing classifications with scheme==scheme and then commits
                                             the new classifications
                                    raise: Raises a ValueError if any transactions already have suggested categories
                                           with this scheme
                                    ignore: Does nothing (these transactions will then be "added" to the existing ones
                                            in the same scheme)
        n_classifications_per_trx (int): Maximum number suggested categories to create per transactions

    Side Effects:
        db suggested categories table is updated

    Returns:
        None
    """
    clf = CommonUsageClassifier.from_db()
    classify_by_model(scheme=scheme,
                      clf=clf,
                      if_scheme_exists=if_scheme_exists,
                      n_classifications_per_trx=n_classifications_per_trx
                      )


def _to_categories(row, scheme):
    cat_names = row[row.notna()].values
    categories = [Category(scheme=scheme, category=cat_name) for cat_name in cat_names]
    return categories


def predictions_to_category_objs(predictions, scheme):
    return predictions.apply(_to_categories, axis=1, scheme=scheme)


def classify_db_by_lookup(label_file, classify_if_not_null=False):
    raise ValueError("Need to review this.  I think this does not fit the current workflow.  Should make suggested clf")
    clf = LookupClassifier.from_csv(label_file)

    if classify_if_not_null:
        trxs = get_transactions()
    else:
        trxs = get_transactions_without_category()
    
    descriptions = [trx.description for trx in trxs]
    categories = clf.predict(descriptions)

    # Edit transactions here, but they're disconnected from db so need to "add" them after
    trxs_to_push = []
    for trx, category in zip(trxs, categories):
        # I think this avoids recommitting things that dont get changed.  But not sure
        if category is not None:
            trx.category = category
            trxs_to_push.append(trx)

    # Update anything we changed
    if trxs_to_push:
        s = create_session()
        s.add_all(trxs_to_push)
        s.commit()


@click.group()
def cli():
    pass


@click.command()
@click.argument("DB_PATH")
@click.argument("LABEL_FILE")
@click.option(
    "--classify_if_not_null",
    is_flag=True,
    default=False,
    type=bool,
    help="If set, classifies all data in database even if it already has a classification"
)
def classify_db_by_lookup_cli(db_path, label_file, classify_if_not_null):
    """
    Classify transactions in a database given a description->label mapping file as input

    Args:\n
        db_path (str): Path to the database to classify data in\n
        label_file (str): Path to the csv description->label file
    """
    global_init(db_path)
    classify_db_by_lookup(label_file, classify_if_not_null)


@click.command()
@click.argument("DB_PATH")
@click.argument("scheme")
@click.option(
    "--n_classifications_per_trx",
    default=2,
    type=int,
    help="Number of suggested categories to create per transaction"
)
@click.option(
    "--if_scheme_exists",
    default="raise",
    type=str,
    help="Define what to do if the scheme exists"
)
def classify_by_most_common_cli(db_path, scheme, n_classifications_per_trx, if_scheme_exists):
    """
    Create suggested categories in a db by using the n most common accepted categories for that description

    Args:\n
        db_path (str): Path to the database to classify data in\n
        scheme (str): Scheme name for the created suggested categories
    """
    global_init(db_path)
    classify_by_most_common(scheme=scheme,
                            if_scheme_exists=if_scheme_exists,
                            n_classifications_per_trx=n_classifications_per_trx
                            )


@click.command()
@click.argument("DB_PATH")
@click.argument("scheme")
@click.argument("model")
@click.option(
    "--if_scheme_exists",
    default="raise",
    type=str,
    help="Define what to do if the scheme exists"
)
def classify_by_model_cli(db_path, scheme, model, if_scheme_exists):
    """
    Create suggested categories in a db by using a sklearn model

    Args:\n
        db_path (str): Path to the database to classify data in\n
        scheme (str): Scheme name for the created suggested categories
        model (str): Path to a model saved using joblib
    """
    global_init(db_path)
    clf = joblib.load(model)
    classify_by_model(scheme=scheme,
                      clf=clf,
                      if_scheme_exists=if_scheme_exists,
                      n_classifications_per_trx=1
                      )


cli.add_command(classify_db_by_lookup_cli, name="lookup")
cli.add_command(classify_by_most_common_cli, name="most-common")
cli.add_command(classify_by_model_cli, name="model")


if __name__ == '__main__':
    cli()
