"""Тесты схемы pandera без использования реального датасета."""
import pandas as pd
import pytest
import pandera.pandas as pa

from diabetes.data import ROWS, EXPORT


def get_valid_sample() -> pd.DataFrame:
    """Генерирует минимальный валидный образец данных для тестов."""
    return pd.DataFrame({
        "gender": ["Female", "Female", "Male"],
        "age": [80, 54, 44],
        "hypertension": [0, 0, 0],
        "heart_disease": [1, 0, 0],
        "smoking_history": ["never", "No info", "never"],
        "bmi": [25.19, 27.32, 19.31],
        "HbA1c_level": [6.6, 6.6, 6.5],
        "blood_glucose_level": [140, 80, 200],
        "diabetes": [0, 0, 1]
    })


def test_valid_rows_pass():
    """Тест 1: Хорошие строки проходят валидацию ROWS."""
    df = get_valid_sample()
    ROWS.validate(df)


def test_invalid_bmi_is_caught():
    """Тест 2: Испорченное значение (BMI = 5.0) должно быть поймано."""
    df = get_valid_sample()
    df.loc[0, "age"] = -1.0
    
    with pytest.raises(pa.errors.SchemaError):
        ROWS.validate(df)


def test_small_export_is_rejected():
    """Тест 3: Маленькая выгрузка (всего 3 строки) должна быть отвергнута схемой EXPORT."""
    df = get_valid_sample()
    
    with pytest.raises(pa.errors.SchemaError):
        EXPORT.validate(df)