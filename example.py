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

if not VAULT_TOKEN or not VAULT_ADDR:
    print("VAULT_TOKEN and VAULT_ADDR must be set in .env file")
    sys.exit(1)

VAULT_SECRET_ENGINE = str(input('Enter the Vault Secret Engine path: ') or 'database')
VAULT_CREDS_TYPE = str(input('Enter the type of credentials that Vault uses to work with the Role: ') or 'creds')
VAULT_CREDS_NAME = str(input('Enter the role name Vault to obtain credentials: ') or 'postgresql-role')

query = "SELECT usename, valuntil FROM pg_user;"

headers = {
    "accept": "application/json",
    "X-Vault-Token": VAULT_TOKEN
}

def vault_credentials():
    try:
        response = requests.request("GET", f"{VAULT_ADDR}/v1/{VAULT_SECRET_ENGINE}/{VAULT_CREDS_TYPE}/{VAULT_CREDS_NAME}", headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            role_username = data['data']['username']
            role_password = data['data']['password']
            return (role_username, role_password)

        elif response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get('errors', ['Unknown error'])[0]
                if 'connection' in error_msg.lower() or 'connect' in error_msg.lower():
                    raise Exception("Database connection error: Vault cannot connect to PostgreSQL. Please check if PostgreSQL is running and accessible.")
                else:
                    raise Exception(f"Vault configuration error: {error_msg}")
            except (ValueError, KeyError):
                raise Exception("Your path to Secret Engine or Creds name by role is invalid. Check it.")

        elif response.status_code == 404:
            raise Exception("Your path to Secret Engine or Creds name by role is invalid. Check it.")

        elif response.status_code == 403:
            raise Exception("Your token is invalid or you do not have the appropriate permissions.")

        else:
            raise Exception(f"Vault API error (HTTP {response.status_code}): {response.text}")

    except requests.RequestException as e:
        raise Exception(f"Failed to connect to Vault: {e}")

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

    except psycopg.OperationalError as error:
        error_msg = str(error)
        if 'password authentication failed' in error_msg or ('role' in error_msg and 'does not exist' in error_msg):
            role_username, role_password = vault_credentials()
            print(error_msg)
            print('\n\nYour password has been successfully updated according to Vault\'s policy!\n')
        elif 'could not connect' in error_msg or 'Connection refused' in error_msg:
            print(f'\nDatabase connection error: {error_msg}')
            print('Please check if PostgreSQL is running and accessible.')
            break
        else:
            print(f'\nOperational error: {error_msg}')
            break

    except psycopg.Error as error:
        print(f'\nDatabase error: {error}')
        break

    except Exception as error:
        print(f'\nUnexpected error: {error}')
        break
