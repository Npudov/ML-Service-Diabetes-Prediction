"""Данные рекомендаций: сырая выгрузка, очищенный слой и его схема pandera.

  uv run python -m churn.recs.data      шаг validate: чистка, проверка, отчёт в MLflow; при нарушениях код выхода 1

Сырой слой datasets/transactions.parquet лежит в DVC и руками не правится.
Чистка: без строк без клиента, цена больше нуля, генерация InvoiceNo из пары (клиент, день),
джойн описаний товаров из articles.parquet. Схема проверяет уже очищенный слой.
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pandera.pandas as pa

TRANSACTIONS_PATH = Path(os.getenv("RECS_DATA_PATH", "datasets/transactions.parquet"))
ARTICLES_PATH = Path(os.getenv("RECS_ARTICLES_PATH", "datasets/articles.parquet"))
CUSTOMERS_PATH = Path(os.getenv("RECS_CUSTOMERS_PATH", "datasets/customers.parquet"))
EXPERIMENT = os.getenv("RECS_EXPERIMENT", "recs")

# правила для каждой строки: их можно проверить и на маленьком образце в CI
ROWS = pa.DataFrameSchema(
    {
        "InvoiceNo": pa.Column(str, pa.Check.str_matches(r"^HM\d{8}$")),
        "StockCode": pa.Column(str, pa.Check.str_matches(r"^\d{9,10}$")),
        "Description": pa.Column(str, pa.Check.str_length(min_value=1)),
        "InvoiceDate": pa.Column("datetime64[ns]", pa.Check.in_range(
            pd.Timestamp("2018-09-20"), pd.Timestamp("2020-09-22")
        )),
        "UnitPrice": pa.Column(float, pa.Check.in_range(0.0001, 1.0)),
        "CustomerID": pa.Column(str),
    },
    strict=True,
)

# правила для выгрузки целиком: объём и распределение, на образце не проверить
EXPORT = pa.DataFrameSchema(
    ROWS.columns,
    checks=[
        pa.Check(lambda df: len(df) >= 100_000, error="меньше 100 тысяч строк: выгрузка неполная"),
        pa.Check(lambda df: df["CustomerID"].nunique() >= 1_000, error="меньше 1000 клиентов"),
    ],
    strict=True,
)


def file_md5(path: Path) -> str:
    """Тот же md5, что DVC пишет в .dvc-файл: по нему видно, на какой версии данных обучена модель."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_raw(path: Path = TRANSACTIONS_PATH) -> pd.DataFrame:
    """Загружаем транзакции. Даты парсим из строки."""
    return pd.read_parquet(path)


def load_articles(path: Path = ARTICLES_PATH) -> pd.DataFrame:
    """Загружаем справочник товаров."""
    return pd.read_parquet(path)


def load_customers(path: Path = CUSTOMERS_PATH) -> pd.DataFrame:
    """Загружаем метаданные клиентов для логирования статистики."""
    return pd.read_parquet(path)


#def hash_customer_id(customer_id: str) -> int:
#    """Преобразуем хеш клиента в детерминированный int64."""
#    if pd.isna(customer_id) or not customer_id:
#       return -1
#    return int(hashlib.md5(str(customer_id).encode()).hexdigest()[:16], 16) % (10**18)


def clean(raw: pd.DataFrame, articles: pd.DataFrame) -> pd.DataFrame:
    """Все преобразования здесь. Сырые данные на входе — чистые на выходе."""
    df = raw.copy()

    # 1. Базовая чистка: без строк без клиента, цена больше нуля
    df = df.dropna(subset=["customer_id", "article_id"])
    df = df[df["price"] > 0]

    # 2. Переименовываем колонки под схему
    df = df.rename(columns={
        "customer_id": "CustomerID",
        "article_id": "StockCode",
        "t_dat": "InvoiceDate",
        "price": "UnitPrice",
    })

    # 3. Парсим даты
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], format="%Y-%m-%d")

    # 4. Генерация InvoiceNo: одна пара (клиент, день) = один чек
    df["_order_key"] = df.groupby(["CustomerID", "InvoiceDate"]).ngroup()
    df["InvoiceNo"] = df["_order_key"].apply(lambda x: f"HM{x:08d}")
    df = df.drop(columns=["_order_key", "sales_channel_id"], errors="ignore")

    # 5. Джойним описания товаров из articles
    if not articles.empty:
        art = articles[["article_id", "prod_name"]].drop_duplicates(subset=["article_id"])
        art["Description"] = art["prod_name"].fillna("").str.strip()
        df = df.merge(art[["article_id", "Description"]], left_on="StockCode", right_on="article_id", how="left")
        df["Description"] = df["Description"].fillna("")
        df = df.drop(columns=["article_id"], errors="ignore")
    else:
        df["Description"] = ""


    # 7. Преобразуем CustomerID в числовой идентификатор
    #df["CustomerID"] = df["CustomerID"].apply(hash_customer_id)

    # 8. Приведение типов
    return df.assign(
        CustomerID=df["CustomerID"].astype("str"),
        InvoiceDate=df["InvoiceDate"].astype("datetime64[ns]"),
        Description=df["Description"].astype(str).str.strip(),
        StockCode=df["StockCode"].astype(str).str.zfill(10),
    ).reset_index(drop=True)


def load_clean(path: Path = TRANSACTIONS_PATH) -> pd.DataFrame:
    raw = load_raw(path)
    articles = load_articles()
    return EXPORT.validate(clean(raw, articles), lazy=True)


def main() -> int:
    import mlflow

    raw = load_raw()
    articles = load_articles()
    customers = load_customers()
    df = clean(raw, articles)

    md5_trans = file_md5(TRANSACTIONS_PATH)
    md5_articles = file_md5(ARTICLES_PATH) if ARTICLES_PATH.exists() else "N/A"
    md5_customers = file_md5(CUSTOMERS_PATH) if CUSTOMERS_PATH.exists() else "N/A"

    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="validate"):
        mlflow.log_params({
            "step": "validate",
            "transactions": str(TRANSACTIONS_PATH),
            "articles": str(ARTICLES_PATH),
            "customers": str(CUSTOMERS_PATH),
            "transactions_md5": md5_trans,
            "articles_md5": md5_articles,
            "customers_md5": md5_customers,
        })
        mlflow.log_metrics({"raw_rows": len(raw), "clean_rows": len(df)})

        try:
            EXPORT.validate(df, lazy=True)
        except pa.errors.SchemaErrors as e:
            fc = e.failure_cases
            summary = fc.groupby(["column", "check"], dropna=False).size().rename("cases").reset_index()
            with tempfile.TemporaryDirectory() as tmp:
                fc.head(1000).to_csv(Path(tmp) / "failure_cases.csv", index=False)
                mlflow.log_artifact(str(Path(tmp) / "failure_cases.csv"))
            mlflow.log_metric("failed_checks", len(summary))
            mlflow.set_tag("valid", "false")
            print("данные не прошли проверку, отчёт failure_cases.csv в MLflow:")
            print(summary.to_string(index=False))
            return 1

        mlflow.set_tag("valid", "true")
        mlflow.log_metrics({"clients": df["CustomerID"].nunique(), "items": df["StockCode"].nunique()})

        if not customers.empty:
            mlflow.log_metric("total_customers_in_file", len(customers))
            if "club_member_status" in customers.columns:
                mlflow.log_metric("active_customers", (customers["club_member_status"] == "ACTIVE").sum())
            if "age" in customers.columns:
                mlflow.log_metric("avg_customer_age", customers["age"].mean())

    result = {"valid": True, "transactions_md5": md5_trans, "articles_md5": md5_articles,
              "customers_md5": md5_customers, "clean_rows": len(df),
              "clients": int(df["CustomerID"].nunique()),
              "items": int(df["StockCode"].nunique()), "last_date": str(df["InvoiceDate"].max())}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())