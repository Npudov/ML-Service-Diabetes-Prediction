# ML SERVICE - Diabetes Prediction

## Quickstart
Склонируйте репозиторий командой

```bash
git clone https://github.com/Npudov/ML-Service-Diabetes-Prediction.git
```

Датасеты для обучения скачайте по ссылке: https://drive.google.com/drive/folders/1QxY-ghizpP0KeEdWXbPQXqUkKBVAF9xZ?usp=sharing и положите их все в папку datasets/

Далее выполните команду 
```bash
uv sync
```

После разверните МЛ платформу кластере запустив

```bash
bash platform/up.sh
```
После выполнения данного скрипта у вас будет доступно следующие сервисы с их endpoint
http://mlflow.localhost, http://diabetes.localhost, http://grafana.localhost, http://airflow.localhost, http://s3.localhost, http://s3-console.localhost. 

Для захода в интерфейс объектного хранилища вводите http://s3-console.localhost

Если вы используете windows в файле etc/hosts следует указать следующие строки:
```text
127.0.0.1 mlflow.localhost
127.0.0.1 diabetes.localhost
127.0.0.1 grafana.localhost
127.0.0.1 airflow.localhost
127.0.0.1 s3.localhost
127.0.0.1 s3-console.localhost
```

Далее указать в локальном конфиге (.dvc/config.local) dvc те поля, что указаны в S3_KEY и S3_SECRET скрипта platform/up.sh

```bash
uv run dvc remote modify --local laptop access_key_id dvc-key-123
uv run dvc remote modify --local laptop secret_access_key dvc-secret-456
```


Запуск github runner (указать свой REPO_URL). Предварительно создайте токен Github runner и пароль для базы через secret DB_PASSWORD (он позволит прмиенять изменения через CI прямо к локальному кластеру kind). 

Для создания DB_PASSWORD зайдите в Github в Settings-Secrets and Variables-Actions наберите имя секрета DB_PASSWORD и передайте туда свой пароль, сохраните

Для создания RUNNER_TOKEN зайдите в Github в Settings-Actions-Runners, нажмите New Self Hosted Runner, выберите свою платформу (например Linux X64, у нас кластер в docker) и скопируйте себе токен из --token, это токен github runner, он понадобится ниже. 

Имя кластера у нас diabetes-ml-platform-monitoring, но сам раннер назван diabetes-ml-platform в данном случае (Нужно указать свой адрес репо в REPO_URL, например форк репозитория)

```bash
docker run -d --name gh-runner --network kind --group-add 0 --restart unless-stopped -v /var/run/docker.sock:/var/run/docker.sock -e REPO_URL=https://github.com/Npudov/ML-Service-Diabetes-Prediction.git -e RUNNER_TOKEN=ALX65S66OQOTFVZ4YVHLYSLKXVUG2 ghcr.io/actions/actions-runner:2.337.0 bash -c '[ -f .runner ] || ./config.sh --unattended --url $REPO_URL --token $RUNNER_TOKEN --name diabetes-ml-platform --labels kind; ./run.sh'
```
После выполнения данных действий для проверки можете зайти в Airflow и запустить dag diabetes_retrain. Если он пройдет успешно в MLFlow вы увидите вашу модель и эксперимент (run).

Далее вызовите утилиту k9s командой:

```bash
k9s
```

Предварительно установите её командой:

```bash
winget install Derailed.k9s
```

Для проверки работы сервиса выполните команды:

```bash
curl http://diabetes.localhost/health
curl http://diabetes.localhost/ready
```

Также можно запустить скрипт командой (отмена через CTRL + C)

```bash
uv run python scripts/traffic.py --url http://diabetes.localhost --rps 10 --bad 0.1
```

Если все прошло успешно, значит проект поднялся.

Далее для получения первого champion в MLFlow запустите команду:

```bash
MLFLOW_TRACKING_URI=http://mlflow.localhost uv run python -m diabetes.train
```

Далее перейдите на mlflow.localhost в раздел runs для просмотра результатов эксперимента обучения

## Сборка проекта
Для воссоздания окружения с нужными зависимостями запустите команду из терминала в корне проекта

```bash
uv sync
```
![alt text](./images/image.png)

Предварительно была зафиксирована версия Python (появится файл .python-version в корне проекта) через

```bash
uv python pin 3.11
```
![alt text](./images/image-1.png)

Предварительно стоит выйти и зайти вновь в терминал для автоматической активации окружения venv после `uv sync`. Проверим, что импорты корректно работают через команду

```bash
uv run python -c "import diabetes; print('ok')"
```
![alt text](./images/image-2.png)

Запустим тесты проекта

```bash
uv run pytest
```

Запустим наше приложение на FastApi на порту 8000

```bash
uv run uvicorn diabetes.service.app:app --port 8000
```

В Doсkerfile у нас прописано 

```bash
uv run --no-sync uvicorn diabetes.service.app:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` - слушать все интерфейсы, обязательно нужно внутри контейнера

`diabetes.service.app:app` - путь до объекта: модуль двоеточие переменная

## Проверка работоспособности сервиса
Поскольку мы подняли наш мл сервис предсказания диабета, необходимо проверить его доступность через написанный API сервиса

Откроем терминал git bash

Доступность проверяется

```bash
curl localhost:8000/health
```

![alt text](./images/image-3.png)

Для проверки работы сервиса передадим тестовый экземляр в формате json в тело POST запроса на endpoint localhost:8000/v1/predict к сервису и посмотрим на результат работы мл модели с сервисом

```bash
curl -X POST localhost:8000/v1/predict -H "Content‐Type: application/json" -d @good.json
```
![alt text](./images/image-4.png)


Также передадим экземляр, который не удовлетворяем схеме входных данных сервиса

```bash
curl -i -X POST localhost:8000/v1/predict -H "Content‐Type: application/json" -d "{\"age\": ‐1}"
```
![alt text](./images/image-5.png)

## Сборка и запуск контейнера с docker образом
В корне проекта имеется написанный Dockerfile для сборки docker-образа нашего приложения. Образ собирается командой

```bash
docker build -t diabetes-service:1.0 .
```
![alt text](./images/image-6.png)

После сборки образа необходимо запустить контейнер с флагом `--rm`, который позволяет удалить контейнер после остановки

```bash
docker run --rm -p 8000:8000 diabetes-service:1.0
```

![alt text](./images/image-7.png)

Порядок слоёв в Dockerfile необходимо держать следующим - сначала зависимости, потом код. В этом случае при изменении кода зависимости будут браться из кэша и повторная сборка образа пройдет значительно быстрее.

## Развертывание сервиса через Docker Compose
Поднимаем docker compose с нашим сервисом на FastApi и базой Postgres для логирования запросов модели с предсказаниями. Docker compose разворачивает компоненты services в виде контейнеров

```bash
docker compose up -d --build
```

![alt text](./images/image-8.png)

Проверяем наличие строк в базе (предварительно вновь сделаем запрос, но уже к поднятому контейнеру)

```bash
curl -X POST localhost:8000/v1/predict -H "Content‐Type: application/json" -d @good.json
```

![alt text](./images/image-9.png)

```bash
docker compose exec db psql -U postgres -d diabetes \
-c "SELECT request_id, score, latency_ms, status_code FROM predictions;"
```

![alt text](./images/image-10.png)


## Создание кластера kubernetes на kind

Создаём кластер с именем diabetes-service-cluster через kubernetes kind

```bash
kind create cluster --name diabetes-service-cluster
```
![alt text](./images/image-11.png)

## Развертывание мл сервиса на узлах кластера kind

Загружаем докер-образ нашего мл сервиса на узлы кластера

```bash
kind load docker-image diabetes-service:1.0 --name diabetes-service-cluster
```
![alt text](./images/image-12.png)

Если необходимо удалить кластер, то нужно вызвать команду

```bash
kind delete cluster --name diabetes-service-cluster
```

Далее необходимо применить написанные манифесты для kubernetes к нашему кластеру из папки k8s

```bash
kubectl apply -f k8s/
```
![alt text](./images/image-13.png)

Для получения информации о подах кластера вызвать

```bash
kubectl get pods
```
![alt text](./images/image-14.png)

Дожидаемся конца выката

```bash
kubectl rollout status deploy/diabetes‐service
```

![alt text](./images/image-15.png)

Создаем туннель с порта 8080 нашей машины до порта 80 сервиса нашего кластера

```bash
kubectl port-forward svc/diabetes-service 8080:80
```
![alt text](./images/image-16.png)

На пути запросов три порта: наш 8080, который идёт на 80 порт сервиса кластера и оттуда на 8000 порт контейнера

## Мониторинг кластера с подами сервиса
Для удобного мониторинга нашего кластера необходимо установить утилиту k9s

```bash
winget install Derailed.k9s
```

Вызов утилиты производится командой

```bash
k9s
```

![alt text](./images/image-17.png)

Делаем далее запрос и видим его в логах одного из подов через k9s

```bash
curl -X POST localhost:8080/v1/predict -H "Content‐Type: application/json" -d @good.json
```

![alt text](./images/image-18.png)

## Нагрузочное тестирование сервиса через locust
Далее проведём нагрузочное тестирование через locust. Запустим его командой с выводом в консоль, предварительно нужно поднять наш сервис на порту 8000 (можно через docker compose)

```bash
uv run locust -f locustfile.py --headless -u 10 -r 5 -t 60s --csv run10 -H http://127.0.0.1:8000
```


```bash
uv run locust -f locustfile.py --headless -u 50 -r 10 -t 60s --csv run50 -H http://127.0.0.1:8000
```

```bash
uv run locust -f locustfile.py --headless -u 100 -r 20 -t 60s --csv run100 -H http://127.0.0.1:8000
```

| Тест | Тип | Имя | Запросов | Ошибок | Медиана (мс) | Среднее (мс) | Мин (мс) | Макс (мс) | Ср. размер (Б) | Запросов/с | 50% | 75% | 90% | 95% | 98% | 99% | 99.9% | 100% |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | POST | `/v1/predict` | 729 | 0 | 7 | 10.56 | 4.98 | 347.53 | 138.90 | 12.95 | 7 | 10 | 12 | 15 | 28 | 41 | 350 | 350 |
| **Run 2** | POST | `/v1/predict` | 3719 | 0 | 11 | 20.67 | 5.15 | 860.24 | 138.92 | 62.69 | 11 | 16 | 24 | 30 | 94 | 280 | 850 | 860 |
| **Run 3** | POST | `/v1/predict` | 7130 | 0 | 29 | 55.80 | 5.39 | 464.23 | 139.00 | 120.24 | 29 | 64 | 140 | 200 | 290 | 330 | 450 | 460 |

Команда запустила тест предсказаний мл сервиса. Тестируемый endpoint описан в locustfile


По итогам нагрузочных тетсирований Failure Count = 0 во всех трех запусках.


Базовая скорость (Run 1, ~13 RPS): Медиана 7 мс, P95 = 15 мс. Это очень быстрый отклик, характерный для хорошо оптимизированного инференса или кэшированных ответов.


Средняя нагрузка (Run 2, ~63 RPS): Медиана выросла незначительно (до 11 мс), P95 = 30 мс. 
Сервис чувствует себя комфортно, деградация минимальна.


Пиковая нагрузка (Run 3, ~120 RPS): Здесь начинается заметная деградация.

Медиана выросла до 29 мс (все еще хорошо).
Среднее время (55.8 мс) стало почти в 2 раза выше медианы (29 мс). Это классический признак появления "длинного хвоста" (long tail) задержек. Очередь запросов начинает расти. 
P95 скакнул до 200 мс

Аномалия - максимальное время отклика на средней нагрузке run2 вдвое больше, чем на пиковой run3 (860 мс против 464 мс). Возможно произошёл какой-то сбой

## Деплой обновленного сервиса на кластер
Далее осуществим выкат новой версии нашего сервера на кластер kubernetes. Поскольку мы прописали новый файл с нагрузочным тестированием, то можем собрать новый докер образ нашего сервиса. Сначала соберем новый докер образ c тегом 1.1 командой:

```bash
docker build -t diabetes-service:1.1 .
```
![alt text](./images/image-19.png)

Далее загрузим образ в node кластера (это не раскатка, а лишь помещение нашего образа в кластер для последующей раскатки) командой

```bash
kind load docker-image diabetes-service:1.1 --name diabetes-service-cluster
```

![alt text](./images/image-20.png)

Осуществим постепенную выкатку на поды командой

```bash
kubectl set image deploy/diabetes-service api=diabetes-service:1.1
```
![alt text](./images/image-21.png)

Видно, что началась раскатка новых подов

Дождемся конца выката

```bash
kubectl rollout status deployment/diabetes-service
```
![alt text](./images/image-22.png)

Посмотрим в логи подов на кластере

![alt text](./images/image-23.png)

Также видно,что версия контейнера в подов поменялась на 1.1

![alt text](./images/image-24.png)

Выкатка прошла успешно. После выкатки нужно не забывать вновь поднять туннель через port-forward, если необходимо подключиться и проверить работу сервиса (так как прошлые поды после выкатки умерли)

## Откат обновления на кластере
Откатимся теперь на прошлую версию в кластере командой 

```bash
kubectl rollout undo deploy/diabetes-service
```

![alt text](./images/image-25.png)

Пошел откат

Посмотрим в подах какая версия контейнера и видим, что вернулись на 1.0

![alt text](./images/image-26.png)

Выведем историю выкаток командой

```bash
kubectl rollout history deploy/diabetes-service
```
![alt text](./images/image-27.png)


## Журнал проблем
Не загружался докер образ в кластер kind, оказалось неверно указал тэг при загрузке образа, исправил тэг и всё заработало.