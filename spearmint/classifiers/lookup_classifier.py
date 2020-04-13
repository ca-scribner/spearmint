import pandas as pd


class LookupClassifier:
    def __init__(self, labels_as_series):
        self.labels_as_series = labels_as_series

    def predict(self, x):
        # Use reindex to get all labels corresponding to elements of x, with default value of None if x is not in
        # known labels

        # This doesn't actually make entries None, it makes them np.nan.  Not sure why apart from mistakenly using None
        # as the default indicator of np.nan?
        predicted = self.labels_as_series.reindex(x, fill_value=None)

        # Convert nan to None
        predicted = predicted.where(pd.notnull(predicted), None)

        return predicted

    @classmethod
    def from_csv(cls, csv_file):
        """
        Instantiates from a csv file with columns of "Description" (x) and "Category" (y)
        """
        df = pd.read_csv(csv_file, index_col="Description")
        ds = df["Category"]
        return cls(ds)
