"""Испорченная выгрузка для проверки шага validate: источник тихо перешёл с число лет на число месяцев с рождения

  uv run python scripts/break_export.py

Перезаписывает datasets/diabetes_prediction_dataset.csv, ни одной ошибки при этом не возникает: файл читается,
типы те же, строк столько же. Ловит такое только проверка значений и распределения.
Вернуть как было: git checkout -- datasets/diabetes_prediction_dataset.dvc && uv run dvc checkout
"""
from pathlib import Path

import pandas as pd

PATH = Path("datasets/diabetes_prediction_dataset.csv")
df = pd.read_csv(PATH, sep=',')
df["age"] = df["age"] * 12
df.to_csv(PATH, index=False, sep=',')
print(f"{PATH}: возраст завышен, медиана {df['age'].median():.0f}, строк {len(df)}")