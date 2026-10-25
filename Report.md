Распишем все по пунктам в проекте

| Пункт | Доказательство |
|---------|----------------|
| Платформа одной командой | ![alt text](image.png) |
| Метрики и дашборд | ![alt text](./images%20for%20monitoring%20ML%20Platform/image-3.png) |
| Данные в DVC и S3 | <img src="./images%20for%20monitoring%20ML%20Platform/image-1.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-2.png" width="600"> |
| Проверка данных | <img src="./images%20for%20monitoring%20ML%20Platform/image-4.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-5.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-6.png" width="600"><br>**Зеленая job:** <br> https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/39064529663/job/117489263903 |
| Конвевейер переобучения в Airflow | **Новая версия модели лучше:**<br><img src="./images%20for%20monitoring%20ML%20Platform/image-8.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-11.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-14.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-15.png" width="600"><br>**Гейт не пустил:**<img src="./images%20for%20monitoring%20ML%20Platform/image-9.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-10.png" width="600"><br>**Плохая выгрузка:**<br><img src="./images%20for%20monitoring%20ML%20Platform/image-12.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-13.png" width="600"><br><img src="./images%20for%20monitoring%20ML%20Platform/image-7.png" width="600"> |
| CI/CD целиком | Зеленый прогон: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/39130430352 |


|Переделка| Что сделано |
|---------|----------------|
| Изменено название теста | Изменено название теста в test_smoke.py на test_predict_handles_missing_gender |
| Блок Quickstart находится в Readme.md | Дополнено описание Quickstart в Readme и указано откуда можно скачать датасет |
