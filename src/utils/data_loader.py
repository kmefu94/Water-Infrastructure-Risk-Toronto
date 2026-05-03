import pandas as pd
from pathlib import Path
import csv


def get_sources(base_path):
    """
    Return dataset folder paths inside the given base path.

    Parameters:
        base_path (str or Path): Path to raw data directory

    Returns:
        list[Path]: Sorted dataset folder paths
    """
    base_path = Path(base_path)

    if not base_path.exists():
        raise FileNotFoundError(f"Base path does not exist: {base_path}")

    if not base_path.is_dir():
        raise NotADirectoryError(f"Base path is not a directory: {base_path}")

    return sorted(
        [folder for folder in base_path.iterdir() if folder.is_dir()],
        key=lambda x: x.name.lower()
    )


def read_files(source_path, extensions=None):
    """
    Return readable file paths from a dataset folder and print them grouped by type.
    Excel files include the number of worksheets.

    Parameters:
        source_path (str or Path): Path to a dataset folder
        extensions (set[str], optional): Allowed file extensions

    Returns:
        list[Path]: Sorted readable file paths
    """
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_path}")

    if extensions is None:
        extensions = {".csv", ".xlsx", ".xls"}

    _excel = {".xlsx", ".xls"}
    files = sorted(
        [f for f in source_path.iterdir() if f.is_file() and f.suffix.lower() in extensions],
        key=lambda x: x.name.lower()
    )

    csv_files = [f for f in files if f.suffix.lower() == ".csv"]
    excel_files = [f for f in files if f.suffix.lower() in _excel]

    if csv_files:
        print("CSV")
        for f in csv_files:
            print(f"  {f.name}")

    if excel_files:
        print("Excel")
        for f in excel_files:
            try:
                n = len(pd.ExcelFile(f).sheet_names)
                print(f"  {f.name}  ({n} worksheet{'s' if n != 1 else ''})")
            except Exception:
                print(f"  {f.name}")

    return files


def pull_data(source_path):
    """
    Load all readable files from a dataset folder into a dictionary of DataFrames.

    Parameters:
        source_path (str or Path): Path to a dataset folder

    Returns:
        dict[str, pd.DataFrame]: key = file stem, value = DataFrame
    """
    source_path = Path(source_path)
    files = read_files(source_path)
    data = {}

    for file in files:
        try:
            if file.suffix.lower() == ".csv":
                try:
                    df = pd.read_csv(file, on_bad_lines="skip", encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(file, on_bad_lines="skip", encoding="latin1")
            elif file.suffix.lower() in {".xlsx", ".xls"}:
                df = pd.read_excel(file)
            else:
                continue
            data[file.stem] = df
        except Exception as e:
            print(f"\n❌ Error loading {file.name}")
            print(e)
            if file.suffix.lower() == ".csv":
                print("🔎 Scanning for bad rows...")
                with open(file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    expected_len = len(next(reader))
                    for i, row in enumerate(reader, start=2):
                        if len(row) != expected_len:
                            print(f"\n⚠️ Bad row at line {i}:")
                            print(row)
                            break

    return data
