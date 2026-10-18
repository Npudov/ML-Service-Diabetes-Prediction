# ML Platform With Monitoring

## Платформа одной командой (Quickstart)
Склонируйте репозиторий командой

```bash
git clone https://github.com/Npudov/ML-Service-Diabetes-Prediction.git
```
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
uv run dvc remote modify --local laptop access_key_id <значение из S3_KEY>
uv run dvc remote modify --local laptop secret_access_key <значение из S3_SECRET>
```


Запуск github runner (указать свой REPO_URL). Предварительно создайте токен Github runner и пароль для базы через secret DB_PASSWORD (он позволит прмиенять изменения через CI прямо к локальному кластеру kind). 

Для создания DB_PASSWORD зайдите в Github в Settings-Secrets and Variables-Actions наберите имя секрета DB_PASSWORD и передайте туда свой пароль, сохраните

Для создания RUNNER_TOKEN зайдите в Github в Settings-Actions-Runners, нажмите New Self Hosted Runner, выберите свою платформу (например Linux X64, у нас кластер в docker) и скопируйте себе токен из --token, это токен github runner, он понадобится ниже. 

Имя кластера у нас diabetes-ml-platform-monitoring, но сам раннер назван diabetes-ml-platform в данном случае

```bash
docker run -d --name gh-runner --network kind --group-add 0 --restart unless-stopped -v /var/run/docker.sock:/var/run/docker.sock -e REPO_URL=https://github.com/Npudov/ML-Service-Diabetes-Prediction.git -e RUNNER_TOKEN=ALX65S66OQOTFVZ4YVHLYSLKXVUG2 ghcr.io/actions/actions-runner:2.337.0 bash -c '[ -f .runner ] || ./config.sh --unattended --url $REPO_URL --token $RUNNER_TOKEN --name diabetes-ml-platform --labels kind; ./run.sh'
```
После выполнения данных действий для проверки можете зайти в Airflow и запустить dag diabetes_retrain. Если он пройдет успешно в MLFlow вы увидите вашу модель и эксперимент (run).


## Метрики и дашборд
Выберем бакеты для задержки в prometheus из расчёта,что наш сервис отвечает за 50-200 мс в зависимости от нагрузки

Запустим команду (отмена через CTRL + C)

```bash
uv run python scripts/traffic.py --url http://diabetes.localhost --rps 10 --bad 0.1
```

По результатам исполнения команды получим следующие метрики в Grafana

![alt text](./images%20for%20monitoring%20ML%20Platform/image-3.png)



## Данные в DVC и S3 кластер
Данные находятся в RustFS, посмотрим на примере diabetes_prediction_dataset.csv

Видим, каков md5 хэш у нашего файла

![alt text](./images%20for%20monitoring%20ML%20Platform/image.png)

Находим его в RustFS, как видим папка находится по первым двум значениям хэша, а внутри уже весь оставшийся хэш объекта

![alt text](./images%20for%20monitoring%20ML%20Platform/image-1.png)


Запустим команду для того,чтобы убедиться что самих данных в образе нет, а есть только dvc

```bash
docker run --rm dibetes-service:1.0 ls datasets/
```

Вывод команды

![alt text](./images%20for%20monitoring%20ML%20Platform/image-2.png)

Сами данные хранятся в RustFS и в образе их нет

## Проверка данных
Запустим команду для невалидных данных и посмотрим что будет в MLFlow. Для того,чтобы все заработало - предварительно прокиньте до кластере соединение командой:

```bash
kubectl port-forward svc/mlflow -n mlops 5000:5000
```

```bash
DIABETES_DATA_PATH=datasets/diabetes_bad_dataset.csv uv run python -m diabetes.data
```

![alt text](./images%20for%20monitoring%20ML%20Platform/image-4.png)

В MLFlow тег valid=false

![alt text](./images%20for%20monitoring%20ML%20Platform/image-5.png)

А теперь прогон с тэгом valid=true

![alt text](./images%20for%20monitoring%20ML%20Platform/image-6.png)


Прогон CI с тестами для экземляров данных - https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/39064529663/job/117489263903


## Конвейер переобучения в Airflow
Запустим DAG в Airflow (airflow.localhost)


Новая версия модели лучше:

![alt text](./images%20for%20monitoring%20ML%20Platform/image-8.png)

![alt text](./images%20for%20monitoring%20ML%20Platform/image-11.png)

Дашборд в Grafana с версией модели:

![alt text](./images%20for%20monitoring%20ML%20Platform/image-14.png)


Вывод скрипта с генерацией трафика:

![alt text](./images%20for%20monitoring%20ML%20Platform/image-15.png)


Гейт не пустил:

![alt text](./images%20for%20monitoring%20ML%20Platform/image-9.png)

![alt text](./images%20for%20monitoring%20ML%20Platform/image-10.png)

Битая (плохая выгрузка):
Выполним команду

```bash
cp datasets/diabetes_bad_dataset.csv datasets/diabetes_prediction_dataset.csv
dvc add datasets/diabetes_prediction_dataset.csv
dvc push
```

Далее выполним коммит в git и посмотрим что при запуске задачи выведет Airflow

![alt text](./images%20for%20monitoring%20ML%20Platform/image-12.png)

![alt text](./images%20for%20monitoring%20ML%20Platform/image-13.png)

Откатим коммит назад и применим изменения в dvc:

```bash
git revert HEAD --no-edit
dvc checkout
dvc push
git push
```

после повторного запуска Airflow увидим следующее:

![alt text](./images%20for%20monitoring%20ML%20Platform/image-7.png)


## CI/CD целиком

Успешный деплой показан здесь - https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/39130430352

## Ключевые моменты

1. Как восстановить ровно тот код и те данные, на
которых она обучена? Чтобы восстановить обучение, берём run_id модели из MLflow, где в параметрах прогона жестко зафиксированы хеш Git-коммита и md5-хеш датасета. Затем делаем делаем git checkout <hash> и dvc checkout (или dvc pull), чтобы получить ровно тот код и те данные.

2. Если сделать git push раньше dvc push данных не окажется в объектном хранилище и на этапе выполнения dag airflow файл с данными для обучения модели не будет найден и возникнет ошибка file not found error

3. Порог в нашем проекте для прогнозирования диабета был выбран из расчета, что не менее 90% истинных больных диабетом должны быть обнаружены. Бинарные проверки контролируют типы данных и строгие категории (например, gender только "Male"/"Female"). Пороговые проверки следят за объемом (минимум 5000 строк) и распределением (доля диабета 2–50%), которые я выбрал на основе статистики исходного датасета. Если порог сделать слишком строгим, пайплайн будет постоянно падать на валидных, но слегка аномальных выгрузках, необоснованно блокируя обновление модели.

4. Pandera проверяет качество всего батча данных на этапе обучения, предотвращая обучение модели на сломанных или смещенных выгрузках. Pydantic валидирует каждый отдельный входящий HTTP-запрос в сервисе, защищая приложение от крашей из-за некорректных типов или отсутствующих полей у клиента. Обе схемы нужны, так как они защищают разные границы системы: границу данных и границу API.

5. Обучение вынесено в отдельный под, так как Airflow — это оркестратор, а не вычислительный кластер и ему может не хватить ресурсов собственных workers на обучение. Также при обучении в собственных workers есть риски конфликта собсвенных зависимостей Airflow с зависимостями библиотек сервиса. Мы используем тот же Docker-образ, чтобы гарантировать полную идентичность окружения и зависимостей при обучении и инференсе. Выкат не требует пересборки образа, потому что при рестарте под просто загружает актуальную версию модели с alias @champion напрямую из реестра MLflow, а код приложения остается прежним.

6. Инфраструктурные метрики — это CPU и память пода; метрики сервиса — latency и HTTP-статусы; метрики модели — распределение вероятностей (score) и текущая model_version. request_id категорически нельзя класть в метки Prometheus, так как это данные с высокой кардинальностью (уникальны для каждого запроса). Это быстро приведет к сильному росту временных рядов, переполнению ненужными данными Prometheus и рискам его падения.

7. Во время выката Kubernetes создает новые поды, ждет их готовности (readiness probe) и только потом плавно завершает старые. Хук preStop с небольшой задержкой дает приложению время корректно дослать ответы по текущим запросам после получения команды от Kubernetes на уничтожение подов. Без него балансировщик может направить трафик на уже умирающий контейнер, что приведет к разрыву соединения и ошибкам 502/503 у клиента.

8. Самый вероятный отказ в проде — это data drift или получение «мусорных» данных от источника, из-за чего модель начинает выдавать аномальные предсказания. Я замечу это в течение 15 минут наблюдений на дашборде Grafana по резкому сдвигу распределения diabetes_score или по красному статусу задачи validate в Airflow. Первым делом я вручную переключу алиас @champion в MLflow на предыдущую стабильную версию, чтобы стабилизировать сервис, и начну расследование качества входных данных.

## Возможные проблемы (Журнал проблем)

1. Делать dvc push после git push, в результате файла в S3 хранилище нет и в airflow в dag возникнет ошибка File not found error
2. Неправильная последовательность команд в dag, ошибка в условиях. Необходимо проверять, что перезапуск подов с новой версией модели происходит после срабатывания promoted, где зашита логика прохождения гейта для модели
3. Забыть создать config.local для dvc по аналогии с ключами для S3 в up.sh, в результате dvc не имеет доступа к S3 хранилищу