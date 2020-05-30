import pandas as pd
import numpy as np

from spearmint.data.db_session import global_init
from spearmint.services.transaction import get_transactions_with_category

# Default column names
FEATURE = "x"
LABEL = "y"


class CommonUsageClassifier:
    def __init__(self):
        """
        Classifier that returns classifications based on the the n-most common labels for the data

        """
        self._df = None

    def fit(self, feature_column, label_column):
        """
        "Fit"s the classifier by storing the usage table

        Args:
            feature_column (iterable): A 1D iterable of the feature to be classified.  Likely strings
            label_column (iterable): A 1D iterable of the same shape as feature containing the labels for the features
        """
        df_temp = pd.DataFrame({FEATURE: feature_column, LABEL: label_column})
        self._df = get_most_frequent_as_df(df_temp, FEATURE, LABEL)

    def predict(self, x, n=1):
        if n:
            # Get the first n columns, but pad in case we have <n
            df_padded = pad_df(df=self._df, columns=range(n), pad_with=np.nan, inplace=False)
            columns_to_return = df_padded.columns[:n]
        else:
            df_padded = self._df
            columns_to_return = df_padded.columns

        # Select the rows to return by using the input feature x as the index on columns_to_return
        predicted = df_padded.loc[x, columns_to_return]

        # Is this helpful?  Had it before...
        # # Convert nan to None
        # predicted = predicted.where(pd.notnull(predicted), None)

        return predicted

    @classmethod
    def from_db(cls, db_file, feature_column='description', label_column='category'):
        """
        Returns a classifier fitted to the records in db_file

        Args:
            db_file (str): Path to a database file
            feature_column (str): Name of the db column to use as a feature
            label_column (str): Name of the db column to use as a label

        Returns:
            Fitted CommonUsageClassifier
        """
        global_init(db_file, echo=False)
        df = get_transactions_with_category(return_type='df')
        clf = cls()
        clf.fit(df[feature_column], df[label_column])
        return clf


# Helpers
def get_grouped_frequency_series(df, by, col_to_count, n_most_frequent=None):
    """
    Returns the n most frequent occurrences of col_to_count in each group of by in df

    Ex:
        df = pd.DataFrame({"x": [f"x{i}" for i in [0, 0, 0, 0, 1, 1, 1]],
                           "y": [f"y{i}" for i in [0, 1, 1, 2, 1, 2, 2]]
                           })
        get_grouped_frequency_series(df, "x", "y", 2)

    Results in:
            x   y   y_counts
        0   x0  y1  2
        1   x0  y0  1
        3   x1  y2  2
        4   x1  y1  1

    See get_most_frequent_as_df for description of args
    """
    result = (df
              .groupby(by)[col_to_count]
              .value_counts()
              .rename(f"{col_to_count}_counts") # Series of cat_count vs (Description,Cat), within each group sorted by cat_count
              .reset_index()             # As a dataframe with Desc and Cat as columns
              )
    if n_most_frequent:
        result = result.groupby(by).head(n_most_frequent)  # Keeping only the top n from each group

    return result


def get_most_frequent_as_df(df, by, col_to_count, n_most_frequent=None, pad_to_n_columns=True):
    """
    Returns the n most frequent items in col_to_count for each group of by in df, as a dataframe where columns are in order of frequency rank

    Ex:
        df = pd.DataFrame({"x": [f"x{i}" for i in [0, 0, 0, 0, 1, 1, 1]],
                           "y": [f"y{i}" for i in [0, 1, 1, 2, 1, 2, 2]]
                           })
        get_most_frequent_as_df(df, "x", "y", 2)

    Results in:

              0    1
        x
        x0   y1   y0
        x1   y2   y1

    Args:
        df (pd.DataFrame): Data to find frequent values from
        by (str): The name of the column to groupby when partitioning to find values
        col_to_count (str): The name of the column to count the value frequencies of
        n_most_frequent (int): Number of items to return per group
        pad_to_n_columns (bool): If True, will add columns if no group has
                                 n_most_frequent unique entries.
                                 If False, dataframe may return < n_most_frequent

    Returns:
        A pd.DataFrame with rows of by groups and <=n_most_frequent columns of entries
        in col_to_count, from most frequent (leftmost column) to least frequent
        (rightmost column)
    """
    # Get grouped as a series
    by_series = get_grouped_frequency_series(df, by, col_to_count, n_most_frequent)

    # Convert to the 2D frame
    df_returned = (by_series
                   .groupby(by)[col_to_count]
                   .apply(lambda x: pd.Series(x.values))  # Building the cat vs rank structure
                   .unstack(-1)  # And changing to a dataframe
                   )

    # Pad columns if needed
    if pad_to_n_columns and n_most_frequent:
        columns = range(n_most_frequent)
        df_returned = pad_df(df_returned, columns, inplace=True)
    return df_returned


def pad_df(df, columns, pad_with=np.nan, inplace=False):
    """
    Returns df padded by columns of pad_with for any column in columns that is not already a column in df

    Args:
        df (pd.DataFrame): DataFrame to pad
        columns (list): List of column names to ensure that the df returned has
        pad_with: Value to put into the columns added
        inplace (bool): If True, modify df in place.  Else, return a copy
    """
    df = df if inplace else df.copy()

    for c in columns:
        if c not in df:
            df[c] = pad_with
    return df



# Temp for debugging
if __name__ == '__main__':
    lc = CommonUsageClassifier.from_db("../../secrets/db/db.sqlite")
