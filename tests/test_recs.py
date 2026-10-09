"""Рекомендации без данных и без базы: в CI датасета нет, он в DVC. Схема проверяется на маленьком образце."""
import pandas as pd
import pandera.pandas as pa
import pytest

from diabetes import db
from diabetes.recs.data import EXPORT, ROWS, clean
from diabetes.recs.metrics import ranking_metrics


@pytest.fixture()
def articles():
    """Минимальный справочник товаров для clean()."""
    return pd.DataFrame({
        "article_id": ["0790583001", "0878681001", "0924675001"],
        "prod_name": ["Striped Top", "Denim Jeans", "Knit Sweater"],
    })


@pytest.fixture()
def raw():
    """Три строки сырой выгрузки H&M: две валидные покупки и одна с нулевой ценой."""
    return pd.DataFrame({
        "t_dat": ["2020-07-15", "2020-07-16", "2020-07-17"],
        "customer_id": ["abc123", "def456", "ghi789"],
        "article_id": ["0790583001", "0878681001", "0924675001"],
        "price": [0.0508, 0.1016, 0.0],
        "sales_channel_id": [2, 1, 2],
    })


def test_clean_keeps_only_purchases(raw, articles):
    """clean() убирает строки с нулевой ценой."""
    df = clean(raw, articles)
    # Остались строки 0 и 1: у них цена > 0
    assert len(df) == 2
    # CustomerID — строка (хеш)
    assert pd.api.types.is_string_dtype(df["CustomerID"])
    # InvoiceNo сгенерирован как HM + 8 цифр
    assert all(inv.startswith("HM") for inv in df["InvoiceNo"])
    # StockCode дополнен до 10 цифр
    assert all(len(s) == 10 for s in df["StockCode"])
    ROWS.validate(df)


def test_price_out_of_range_is_caught(raw, articles):
    """Цена вне диапазона 0.0001..1.0 ловится схемой."""
    bad = clean(raw, articles).assign(UnitPrice=2.0)
    with pytest.raises(pa.errors.SchemaErrors) as e:
        ROWS.validate(bad, lazy=True)
    assert "UnitPrice" in set(e.value.failure_cases["column"])


def test_small_export_is_rejected(raw, articles):
    """Меньше 100 тысяч строк — EXPORT не проходит."""
    with pytest.raises(pa.errors.SchemaErrors) as e:
        EXPORT.validate(clean(raw, articles), lazy=True)
    assert "меньше 100 тысяч строк: выгрузка неполная" in set(e.value.failure_cases["check"])


def test_metrics_lecture_example():
    """Пример из лекции 4.3: список A..E, потом куплены B, D и F."""
    m = ranking_metrics({0: ["A", "B", "C", "D", "E"]}, {0: {"B", "D", "F"}}, k=5, n_items=10)
    assert m["precision"] == pytest.approx(0.40)
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["hitrate"] == 1
    assert m["ndcg"] == pytest.approx(0.4982, abs=1e-3)


def test_recommend_known_customer(client, monkeypatch):
    monkeypatch.setattr(
        db, "fetch_recommendations",
        lambda cid, k: ([("0790583001", "Striped Top")] * k, "als", "recs-v2"),
    )
    r = client.get("/v1/recommend/abc123?k=3")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "als"
    assert body["customer_id"] == "abc123"
    assert len(body["items"]) == 3
    assert body["model_version"] == "recs-v2"


def test_recommend_not_published_is_503(client, monkeypatch):
    monkeypatch.setattr(db, "fetch_recommendations", lambda cid, k: None)
    assert client.get("/v1/recommend/abc123").status_code == 503


def test_recommend_k_out_of_range_is_422(client):
    assert client.get("/v1/recommend/abc123?k=50").status_code == 422