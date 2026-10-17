"""Данные по диабету: сырая выгрузка, очищенный слой и его схема pandera.

  uv run python -m diabetes.data      шаг validate: чистка, проверка, отчёт в MLflow; при нарушениях код выхода 1

Сырой слой datasets/diabetes_prediction_dataset.csv лежит в DVC и руками не правится.
Чистка: возраст больше нуля.
Схема проверяет уже очищенный слой.
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pandera.pandas as pa

DIABETES_PATH = Path(os.getenv("DIABETES_DATA_PATH", "datasets/diabetes_prediction_dataset.csv"))
EXPERIMENT = os.getenv("DIABETES_EXPERIMENT", "diabetes")
os.environ["MLFLOW_TRACKING_URI"] = "http://mlflow.localhost:5000"
os.environ["MLFLOW_REGISTRY_URI"] = "http://mlflow.localhost:5000"

# правила для каждой строки: их можно проверить и на маленьком образце в CI
ROWS = pa.DataFrameSchema(
    {
        "gender": pa.Column(str, pa.Check.isin(["Male", "Female", "Other"])),
        "age": pa.Column(int, pa.Check.greater_than_or_equal_to(0)),
        "hypertension": pa.Column(int),
        "heart_disease": pa.Column(int),
        "smoking_history": pa.Column(str, pa.Check.str_length(min_value=1)),
        "bmi": pa.Column(float),
        "HbA1c_level": pa.Column(float, pa.Check.greater_than(0.0)),
        "blood_glucose_level": pa.Column(int, pa.Check.greater_than(0)),
        "diabetes": pa.Column(int, pa.Check.isin([0, 1])),
    },
    strict=True,
)

def check_diabetes_ratio(df: pd.DataFrame) -> bool:
    # Проверка: доля диабетиков (diabetes == 1) должна быть от 2% до 50%. 
    # Это защита от сломанной выгрузки, где фильтр случайно удалил всех больных или всех здоровых.
    ratio = (df["diabetes"] == 1).mean()
    return 0.02 <= ratio <= 0.50

# правила для выгрузки целиком: объём и распределение, на образце не проверить
EXPORT = pa.DataFrameSchema(
    ROWS.columns,
    checks=[
        pa.Check(lambda df: len(df) >= 5_000, error="меньше 5 тысяч строк: выгрузка неполная"),
        pa.Check(check_diabetes_ratio, error="доля диабета вне диапазона 0.05-0.50: данные смещены или сломаны"),
    ],
    strict=True,
)


def file_md5(path: Path) -> str:
    """Тот же md5, что DVC пишет в .dvc-файл: по нему видно, на какой версии данных обучена модель."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_raw(path: Path = DIABETES_PATH) -> pd.DataFrame:
    """Загружаем данные анализов пациентов"""
    return pd.read_csv(path, sep=',', encoding='utf-8')


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Все преобразования здесь. Сырые данные на входе — чистые на выходе."""
    df = raw.copy()

    # 1. Базовая чистка: возраст больше нуля
    df = df[df["age"] > 0]


    # 2. Приведение типов
    return df.assign(
        gender=df["gender"].astype("str"),
        age=df["age"].astype(int),
        hypertension=df["hypertension"].astype(int),
        heart_disease=df["heart_disease"].astype(int),
        smoking_history=df["smoking_history"].astype(str),
        bmi=df["bmi"].astype(float),
        HbA1c_level=df["HbA1c_level"].astype(float),
        blood_glucose_level=df["blood_glucose_level"].astype(int),
    ).reset_index(drop=True)


def load_clean(path: Path = DIABETES_PATH) -> pd.DataFrame:
    raw = load_raw(path)
    return EXPORT.validate(clean(raw), lazy=True)


def main() -> int:
    import mlflow

    raw = load_raw()

    df = clean(raw)

    md5_diabetes = file_md5(DIABETES_PATH)


    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="validate_diabetes"):
        mlflow.log_params({
            "step": "validate",
            "diabetes": str(DIABETES_PATH),
            "diabetes_md5": md5_diabetes,
        })
        mlflow.log_metrics({"raw_rows": len(raw), "clean_rows": len(df)})

        try:
            EXPORT.validate(df, lazy=True)
        except pa.errors.SchemaErrors as e:
            fc = e.failure_cases
            summary = fc.groupby(["column", "check"], dropna=False).size().rename("cases").reset_index()
            with tempfile.TemporaryDirectory() as tmp:
                fc.head(1000).to_csv(Path(tmp) / "failure_cases_diabetes.csv", index=False)
                mlflow.log_artifact(str(Path(tmp) / "failure_cases_diabetes.csv"))
            mlflow.log_metric("failed_checks", len(summary))
            mlflow.set_tag("valid", "false")
            print("данные не прошли проверку, отчёт failure_cases_diabetes.csv в MLflow:")
            print(summary.to_string(index=False))
            return 1

        mlflow.set_tag("valid", "true")
        mlflow.log_metric("patients", len(df))

        if not df.empty:
            mlflow.log_metric("total_patients_in_file", len(df))
            if "age" in df.columns:
                mlflow.log_metric("avg_patients_age", df["age"].mean())

    result = {"valid": True, "diabetes_md5": md5_diabetes, 
              "clean_rows": len(df),
              "patients": len(df),
              "avg_patients_age": df["age"].mean()
              }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())