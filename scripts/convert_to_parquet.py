"""Конвертация CSV файлов H&M в Parquet с правильными типами данных.

Использование:
    python scripts/convert_to_parquet.py
    
Или через uv:
    uv run python scripts/convert_to_parquet.py
"""
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def convert_transactions_chunked(input_path: Path, output_path: Path, chunk_size: int = 2_000_000) -> None:
    """Конвертируем transactions.csv в parquet, читая чанками."""
   
    
    # Удаляем старый файл если есть
    if output_path.exists():
        output_path.unlink()
    
    total_rows = 0
    writer = None
    
    # Читаем CSV чанками
    for chunk in pd.read_csv(
        input_path,
        dtype={
            "t_dat": str,
            "customer_id": str,
            "article_id": str,
            "price": float,
            "sales_channel_id": int,
        },
        chunksize=chunk_size,
    ):
        total_rows += len(chunk)
        print(f"  Обработано {total_rows:,} строк...")
        
        # Конвертируем pandas DataFrame в PyArrow Table
        table = pa.Table.from_pandas(chunk)
        
        # Первый чанк создаёт writer, последующие дозаписывают
        if writer is None:
            writer = pq.ParquetWriter(
                output_path,
                table.schema,
                compression="snappy"
            )
        
        writer.write_table(table)
    
    # Закрываем writer
    if writer is not None:
        writer.close()


def convert_articles(input_path: Path, output_path: Path) -> None:
    """Конвертируем articles.csv в parquet."""
    
    df = pd.read_csv(
        input_path,
        dtype={
            "article_id": str,  # Ведущие нули!
        },
        usecols=[
            "article_id",
            "product_code",
            "prod_name",
            "product_type_no",
            "product_type_name",
            "product_group_name",
            "graphical_appearance_no",
            "graphical_appearance_name",
            "colour_group_code",
            "colour_group_name",
            "perceived_colour_value_id",
            "perceived_colour_value_name",
            "perceived_colour_master_id",
            "perceived_colour_master_name",
            "department_no",
            "department_name",
            "index_code",
            "index_name",
            "index_group_no",
            "index_group_name",
            "section_no",
            "section_name",
            "garment_group_no",
            "garment_group_name",
            "detail_desc"
        ],
    )
    
    
    df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)


def convert_customers(input_path: Path, output_path: Path) -> None:
    """Конвертируем customers.csv в parquet."""
    
    df = pd.read_csv(
        input_path,
        dtype={
            "customer_id": str,  # Хеш, оставляем строкой
        },
        usecols=[
            "customer_id",
            "FN",
            "Active",
            "club_member_status",
            "fashion_news_frequency",
            "age",
            "postal_code"
        ],
    )
    
    
    df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)


def main() -> None:
    """Конвертируем все CSV файлы в parquet."""
    datasets_dir = Path("datasets")
    
    # Проверяем наличие CSV файлов
    csv_files = {
        "transactions": datasets_dir / "transactions_train.csv",
        "articles": datasets_dir / "articles.csv",
        "customers": datasets_dir / "customers.csv",
    }
    
    missing = [name for name, path in csv_files.items() if not path.exists()]
    if missing:
        print(f"Отсутствуют файлы: {', '.join(missing)}")
        sys.exit(1)
    
    # Конвертируем каждый файл
    convert_transactions_chunked(
        csv_files["transactions"], 
        datasets_dir / "transactions.parquet"
    )
   
    
    convert_articles(
        csv_files["articles"],
        datasets_dir / "articles.parquet"
    )
    
    convert_customers(
        csv_files["customers"],
        datasets_dir / "customers.parquet"
    )


if __name__ == "__main__":
    main()