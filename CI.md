# CI
Здесь указана информация о ci сервиса с прогонами тестов, билда образа и деплоя. Ci написан в файле ci.yml. Тесты прогоняются при pull request в ветку main. Тесты вместе с билдом образа и деплоем прогоняются после слияния с веткой main. Дополнительно в /health сервиса добавили информацию о конфигах из configmap, интеграционный тест с проверкой кода ответа сервиса при Post запросе и полями блока features, которые пришли в бд при логировании предсказаний модели. Также в пайплайне реализован smoke, который проверяет, что возвращаемое значение во входной поток находится в диапазоне от 0.0 до 1.0 (вероятность диабета у человека)


## Базовый пайплайн
Успешный пайплайн со всеми этапами тестов, сборки, деплоя доступен по ссылке: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36246382124
Образ сервиса с sha коммита находится в packages по ссылке: https://github.com/Npudov/ML-Service-Diabetes-Prediction/pkgs/container/ml-service-diabetes-prediction/1298549548?tag=sha-0290f5f993c7fbd6be122ab8c59e321da2e15e41

## Возможные ошибки в пайплайне

### Сломанные тесты
Давайте сломаем наши тесты и увидим, что пайплайн с тестами не проходит pull request, а затем починим тесты
Ссылка на pull request: https://github.com/Npudov/ML-Service-Diabetes-Prediction/pull/16

### Сломанный configMap
Давайте неверно укажем путь к модели в configMap и посмотрим,что произойдет с нашим пайплайном при Pull request и при деплое. Затем починим ошибку

Ссылка на неуспешный job: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36228734579/job/108367793365
Ссылка на успешный job: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36229765656

В логах увидим, что при job deploy наш пайплайн не нашёл нашу модель на шаге `сервис` и выкинет исключение FileNotFoundError: [Errno 2] No such file or directory: 'artifacts/baseline_logreg.joblib'


### Неверное имя secrets по сравнению с именем в кластере
Давайте неверно укажем имя секрета в secretRef, чтобы оно не совпало с именем diabetes-secrets, которое задает пайплайн и узнаем,что будет с нашим деплоем. Затем починим ошибку.

Ссылка на неуспешный job: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36230064635
Ссылка на успешный job: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36230455841

В логах увидим, что при job deploy наш пайплайн упал на шаге `сервис` и в нём увидим, что наш под diabetes-service в статусе CreateContainerConfigError, ErrImagePull, ImagePullBackOff и также информация, что в нашем container с именем api Error from server (BadRequest): container "api" in pod "diabetes-service-585b8955cb-w7czp" is waiting to start: image can't be pulled

### Неверное указание requests
Давайте неверно укажем requests (зададим значение таким (1000000000000Mi), которое превышает физически доступное) и посмотрим, что будет с деплоем. Затем починим ошибку

Ссылка на неуспешный job: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36230733335
Ссылка на успешный job: https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36231171654

В логах увидим, что при job deploy наш пайплайн упал на шаге `сервис` и в нём увидим, что The Deployment "diabetes-service" is invalid: spec.template.spec.containers[0].resources.requests: Invalid value: "976562500Gi": must be less than or equal to memory limit of 512Mi
service/diabetes-service created


Это означает, что ресурсов для пода не хватило и он не создался. Логи подов показали, что пода нет Error from server (NotFound): deployments.apps "diabetes-service" not found
error: error from server (NotFound): deployments.apps "diabetes-service" not found in namespace "default"




### Важные моменты
1. Job Build в первом прогоне шёл 1 минута 32 секунды (https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36227975366/job/108365645779), во втором - 21 секунду (https://github.com/Npudov/ML-Service-Diabetes-Prediction/actions/runs/36228734579). Из Dockerfile кэшировались слои с установкой uv, переход в рабочую директорию /app, и установка зависимостей по файлу uv.lock. Данные слои кэшировались поскольку в нижние слои мы положили реже изменяющийся набор зависимостей и если изменились верхние слои (например код, а зависимости нет), то на нижних слоях будет использоваться кэширование поскольку зависимости там не менялись, а вот тому,что завязано на изменившимся коде придется пересобираться. Поэтому то, что меняется редко класть первым вниз, а то,что чаще - наверх.
2. Поды при успешных прогонах находятся в ImagePullBackOff поскольку kubernetes не мог их скачать из реестра поскольку данные образа не были загружены в kind через load docker-image (при применении манифестов образы недоступны в кластере вот Kind И создал под них поды со статусом ImagePullBackOff, далее уэе загружается конкретный образ с хэш коммита)
3. Пароль от базы помещается в переменную контейнера postgres с именем переменной POSTGRES_PASSWORD,туда он приходит из diabetes-secrets кластера kind по ключу POSTGRES_PASSWORD. В кластере Kind в diabetes-secrets по literal POSTGRES_PASSWORD значение приходит из secrets Github с ключом DB_PASSWORD, там пароль находится в зашифрованном виде. Поэтому путь это Secrets Github - secrets kind diabetes-secrets - переменная окружения POSTGRES_PASSWORD контейнера postgres. У Database_url путь аналогичен, только там из Github приходит только пароль, далее эта конфигурация попадает в виде переменной окружения DATABASE_URL в diabetes-service с контейнером api и уже далее pydantic_settings по имени вытаскивает database_url в конфиг приложения и он используется уже самим сервисом внутри себя.
4. Build делается после test благодаря конструкции needs в ci.yml. Это необходимо для того,чтобы избежать негативного сценария, когда мы запушили образ раньше, чем успешно прошли тесты, в результате deploy будет идти без предварительной проверки и приложение выкатится с ошибками тестирования (сломанным), а образ в регистре контейнеров будет с кодом сломанного приложения
5. В Pull request проверяются только тесты поскольку это предложение на слияние с веткой и на этом этапе достаточно проверить, что код не ломает существующую функциональность. Проверять build и deploy на каждом PR избыточно и регистр контейнеров будет забиваться множеством лишних образов
6. pg_advisory_xact_lock необходимо,чтобы одна из реплик получила лок на ресурсы, сделала свои операции,далее лок получает вторая реплика и продолжает выполнение своего кода. Это полезно, поскольку обе реплики могут попытаться создать одновременно таблицы и одна будет постоянно падать с ошибкой так как таблица уже создана. pg_advisory_xact_lock является транзакционным локом и снимается, когда происходит commit транзакции или rollback  
7.  Поды diabetes-service были в статусе diabetes-service not found (при неверном requests), ErrImagePull (ошибка при скачивании образа) и СreateContainerConfigError (ошибка конфига контейнера) (при невреном имени secrets в deployment diabetes-service), CrashLoopBackOff (бесконечно стартует и падает по кругу, неверное указание пути в configMap для модели)


### Возникшие проблемы
Также ещё отмечу ошибку, что в ходе написания ci сервиса возникла проблема, что забыл указать в deployment откуда брать для переменных окружения контейнера значения (не указал secretRef), в результате на job deploy на шаге smoke при проверке числа записей в логах предсказания окажется, что таблица не создана поскольку именно из secretRef мы бы получили database_url (строка соединения к бд с паролем к базе), а поскольку мы не получили эти значения, то и соединиться не смогли. 