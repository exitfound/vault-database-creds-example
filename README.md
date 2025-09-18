# Vault Database Dynamic/Static Creds Example

## Описание:

Это простейший пример, реализованный на Python, который забирает учетные данные из Vault и подставляет их в момент подключения к БД PostgreSQL. Поддерживает как динамические, так и статические секреты Vault в рамках подсистемы секретов Database. Но самое главное то, что, поскольку скрипт изначально крутится в бесконечном цикле, мы можем явным образом увидеть процесс ротации учетных данных в Vault, когда истекает срок жизни пароля или он был изменен вручную. И при этом приложение заново осуществялет запрос к Vault, получает вновь валидные данные и снова подключается к БД. Так что это сугубо ознакомительный пример с целью более детально понять, как приложение будет работать в сочетании с такими инструментами как Vault и PostgreSQL. Пример не предназначен для реального использования. И в целом был создан в рамках написания статьи, состаящей из двух частей ([1](https://telegra.ph/Integraciya-HashiCorp-Vault-s-BD-na-primere-PostgreSQL-CHast-5-06-13) и [2](https://telegra.ph/Integraciya-HashiCorp-Vault-s-BD-na-primere-PostgreSQL-CHast-52-06-29)), в которой подробно рассказывается о всевозможных настройках по интеграции между двумя вышеупомянутыми сервисами.

## Подготовка к запуску:

### 1. Настройка PostgreSQL

Запустите PostgreSQL в Docker для простоты настройки:

```bash
docker run --name postgres-vault \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -d postgres:16
```

### 2. Настройка динамических credentials

Включите Database Secrets Engine и настройте подключение к PostgreSQL:

```bash
# Включить Database Secrets Engine
vault secrets enable database

# Настроить подключение к PostgreSQL
vault write database/config/my-postgresql-database \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@localhost:5432/postgres?sslmode=disable" \
    allowed_roles="postgresql-role" \
    username="postgres" \
    password="postgres"

# Создать роль для динамических credentials (TTL = 1 минута для демонстрации)
vault write database/roles/postgresql-role \
    db_name=my-postgresql-database \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1m" \
    max_ttl="2m"
```

### 3. Настройка статических credentials (опционально)

Если хотите также протестировать статические credentials, создайте отдельную роль:

```bash
# Сначала создайте статического пользователя в PostgreSQL
docker exec -it postgres-vault psql -U postgres -c "CREATE USER static_user WITH PASSWORD 'static_pass';"
docker exec -it postgres-vault psql -U postgres -c "GRANT SELECT ON ALL TABLES IN SCHEMA public TO static_user;"

# Создать роль для статических credentials в Vault
vault write database/static-roles/postgresql-role \
    db_name=my-postgresql-database \
    username="static_user" \
    rotation_period="1m"
```

### 4. Запуск примера

Минимальный набор действий для запуска:

```bash
git clone https://github.com/exitfound/vault-database-creds-example.git
pip3 install -r requirements.txt
python3 example.py
```

Перед запуском вам также нужно будет изменить содержимое файла `.env`. Укажите через HTTP / HTTPS адрес своего сервера Vault (вместе с портом, если не используете TLS) и токен, у которого есть доступ к подсистеме секретов Database, и который может получить учетные данные по пути `<database>/<creds_or_static-creds>/<name_of_role>`. Ниже представлен соответствующий пример файла `.env`:

```
VAULT_TOKEN = "Your_vault_token_there"
VAULT_ADDR = "http://vault.your.domain:8200"
DB_PORT = "5432"
DB_HOST = "localhost"
DB_NAME = "postgres"
```

## Работа со скриптом:

Как уже было отмечено ранее запуск осуществляется следующим образом:

```
python3 example.py
```

После этого вам будет предложено ввести три значения:

- Путь к подсистеме секретов базы данных (Secret Engine от Vault). По умолчанию это database;

- Тип учетных данных (Dynamic или Static Creds), поскольку скрипт поддерживает оба варианта. По умолчанию это creds, то бишь динамический вариант;

- Непосредственно сама роль, которая была создана во время настройки Vault для интеграции с БД Postgresql. По умолчанию это postgresql-role;

По сути это аналог двух консольных команд в Vault:

```
vault read database/creds/postgresql-role - для получения динамических учетных данных;

vault read database/static-creds/postgresql-role - для получения статических учетных данных;
```

Примечание: Важно понимать, что database как и postgresql-role, это просто имена, и в вашем случае путь может отличаться.

После чего, в случае валидности всех введенных данных, а также того, что указано в файле `.env`, скрипт начнет свою работу в бесконечном цикле. В нём же будет предоставлена базовая информация на предмет того, какой сейчас пользователь и пароль от Vault используются. Если вы желаете прервать работу скрипта, нажмите следующее сочетание клавиш:

```
Ctrl + C
```

Если вы хотите в явном виде увидеть как приложение потеряет доступ к базе из-за того, что пароль протух, а потом вновь обратится к Vault за обновленным вариантом, и снова подключится к базе, вы можете выставить крайне низкий TTL при настройке Vault и просто подождать или использовать следующие команды в соседнем окне во время работы скрипта:

### Ручной сброс динамических credentials

```bash
# Отозвать все текущие динамические credentials для моментального тестирования ротации
vault lease revoke -prefix database/creds/postgresql-role
```

### Ручной сброс статических credentials

```bash
# Rotate статических учетных данных
vault write -f database/rotate-role/postgresql-role
```

Подробнее обо всех командах по работе с динамическими / статическими учетными данными в рамках работы с БД можно найти в статье по ссылкам выше.
