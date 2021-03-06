import os
import pdb
import numpy as np
import pandas as pd
from argparse import ArgumentParser
from libxmp.utils import file_to_dict
from libxmp.consts import (
    XMP_NS_EXIF_Aux,
    XMP_NS_Photoshop,
    XMP_NS_EXIF,
    XMP_NS_XMP,
    XMP_NS_DC,
    XMP_NS_XMP_MM,
    XMP_NS_CameraRaw,
    XMP_NS_TIFF
)

META_NAMES = []
ALL_PROPERTIES = [XMP_NS_EXIF, XMP_NS_EXIF_Aux, XMP_NS_Photoshop, XMP_NS_XMP, XMP_NS_DC, XMP_NS_XMP_MM, XMP_NS_CameraRaw, XMP_NS_TIFF]
PROPERTIES = [XMP_NS_EXIF, XMP_NS_TIFF]
FN_DESIRED_FIELDS = os.path.join(os.path.dirname(__file__), "res", "desired_labels")
DESIRED_FIELDS = pd.read_csv(FN_DESIRED_FIELDS, names=["dtype", "field"])


def xmp_extract(fns):
    data = []
    columns = []
    for fn in fns:
        c, d = xmp_to_vec(fn)
        columns.append(c)
        data.append(d)
    return columns, data


def convert_types(df):

    def str_to_float(s):
        if isinstance(s, (str, unicode)):
            if "/" in s:
                # parse a ratio to its float value
                num, den = s.split("/")
                return [float(num) / float(den)]
            elif "," in s:
                # parse a csv variable into multiple new columns
                return [float(el) for el in s.split(",")]
            else:
                # parse to float directly
                return [float(s)]
        else:
            # parse to float directly
            return [float(s)]

    converted = []
    columns = []
    for column, dtype in zip(df.columns, DESIRED_FIELDS["dtype"]):
        if dtype == "categorical":
            values = pd.get_dummies(df[column]).values.tolist()
            converted.extend(zip(*values))
            columns.extend(["{}_{}".format(column, i) for i in xrange(len(values[0]))])
        elif dtype == "binary":
            converted.append(df[column].replace({"True": 1, "False": 0}).astype(int).values.tolist())
            columns.append(column)
        elif dtype == "numerical":
            values = df[column].replace('', np.nan).apply(str_to_float).values.tolist()
            lengths = np.array([len(val) if isinstance(val, list) else 1 for val in values])
            target_len = np.max(lengths)
            columns.extend(["{}_{}".format(column, i) for i in xrange(target_len)])
            if np.any(lengths > 1):
                for i, val in enumerate(values):
                    if lengths[i] < target_len:
                        values[i] = [None] * target_len
            values = zip(*values)
            converted.extend(values)
        else:
            raise TypeError("Unexpected type {} for property {}".format(dtype, column))

        if len(converted) != len(columns):
            raise RuntimeError("The number of data columns and the number of data column names is different.")

    return columns, converted


def xmp_to_vec(fn):
    # read in the core data of interest from the XMP file.
    xmp_data = file_to_dict(fn)
    df = pd.DataFrame([tup[:2] for _, data in xmp_data.items() for tup in data], columns=["field", "value"])

    # filter down to the desired properties only.
    df = df.merge(DESIRED_FIELDS, how="inner", on="field")

    return df["field"].values, df["value"].values


def main():
    args = parse_args()
    with open(args.fn) as fp:
        fns = fp.read().splitlines()
    columns, data = xmp_extract(fns)
    df = pd.DataFrame(np.empty(shape=(len(data), len(DESIRED_FIELDS))), columns=DESIRED_FIELDS["field"])
    for i, (c, d) in enumerate(zip(columns, data)):
        df.loc[i, c] = d

    # convert the data types
    columns, data = convert_types(df)
    df = pd.DataFrame(data).transpose()
    df.columns = columns
    import pdb; pdb.set_trace()


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-f", "--file", dest="fn", help="Path to a file which contains a list of XMP files to parse (one per line).")
    return parser.parse_args()


if __name__ == "__main__":
    main()
