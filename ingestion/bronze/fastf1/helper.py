import re
import pandas as pd

def to_snake_case(name: str) -> str:
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name)
    return s.lower()

def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]
    return df