import json
import psycopg
import requests
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

DB_PORT = os.environ.get('DB_PORT', '5432')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'postgres')
VAULT_TOKEN = os.environ.get('VAULT_TOKEN')
VAULT_ADDR = os.environ.get('VAULT_ADDR')

VAULT_SECRET_ENGINE = str(input('Enter the Vault Secret Engine path: ') or 'database')
VAULT_CREDS_TYPE = str(input('Enter the type of credentials that Vault uses to work with the Role: ') or 'creds')
VAULT_CREDS_NAME = str(input('Enter the role name Vault to obtain credentials: ') or 'postgresql-role')

query = "SELECT usename, valuntil FROM pg_user;"

headers = {
    "accept": "application/json",
    "X-Vault-Token": VAULT_TOKEN
}

def vault_credentials():
    response = requests.request("GET", f"{VAULT_ADDR}/v1/{VAULT_SECRET_ENGINE}/{VAULT_CREDS_TYPE}/{VAULT_CREDS_NAME}", headers=headers)
    if response.status_code == 200:
        data = response.json()
        role_username = data['data']['username']
        role_password = data['data']['password']
        return (role_username, role_password)

    elif response.status_code == 400 or response.status_code == 404:
        raise Exception("Your path to Secret Engine or Creds name by role is invalid. Check it.")

    elif response.status_code == 403:
        raise Exception("Your token is invalid or you do not have the appropriate permissions.")

    else:
        raise Exception("Some unexpected problems arose.")

def db_connect(role_username, role_password):
    connection = psycopg.connect(dbname=DB_NAME, user=role_username, password=role_password, host=DB_HOST, port=DB_PORT)
    print('\nYou are successfully connected to the PostgreSQL Database.\n')
    print('Your current credentials from Vault for PostgresSQL Database right now is:\n', 
        'Username:', role_username, '\n',
        'Password:', role_password, '\n')
    cursor = connection.cursor()
    cursor.execute(query)
    record = cursor.fetchall()
    print("Display current list of users inside the PostgreSQL Database (Example Query):\n",'\n '.join([i[0] for i in record]))
    cursor.close()
    connection.close()

try:
    role_username, role_password = vault_credentials()

except Exception as error:
    print("Something went wrong:\n\n", error)
    sys.exit(1)

while True:
    time.sleep(2)
    try:
        db_connect(role_username, role_password)

    except (Exception, psycopg.Error) as error:
        error = str(error)
        if 'password authentication' in error:
            role_username, role_password = vault_credentials()
            print(error)
            print('\n\nYour password has been successfully updated according to Vault\'s policy!\n')

        else:
            print('\nError Message: {m}'.format(m = str(error)))
            break
