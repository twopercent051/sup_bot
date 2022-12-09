import pymssql

import config

server = config.MSSQL[0]
user = config.MSSQL[1]
password = config.MSSQL[2]
db = config.MSSQL[3]


def create_table_agents():
    conn = pymssql.connect(server, user, password, db)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE agents (
        id INT IDENTITY(1, 1) PRIMARY KEY,
        agent_id VARCHAR(20) NOT NULL
    )
    """)
        conn.commit()
        print('Создали agents')
    except:
        print('Таблица agents уже создана. Если хотите ее удалить воспользуйтесь функцией delete_table')
    cursor.close()
    conn.close()


def create_table_passwords():
    conn = pymssql.connect(server, user, password, db)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE passwords (
        id INT IDENTITY(1, 1) PRIMARY KEY,
        password VARCHAR(20) NOT NULL
    )
    """)
        conn.commit()
        print('Создали passwords')
    except:
        print('Таблица passwords уже создана. Если хотите ее удалить воспользуйтесь функцией delete_table')
    cursor.close()
    conn.close()


def create_table_files():
    conn = pymssql.connect(server, user, password, db)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE files (
        id INT IDENTITY(1, 1) PRIMARY KEY,
        req_id VARCHAR(20),
        file_id VARCHAR(250),
        file_name VARCHAR(2048),
        type VARCHAR(20)
    )
    """)
        conn.commit()
        print('Создали files')
    except:
        print('Таблица files уже создана. Если хотите ее удалить воспользуйтесь функцией delete_table')
    cursor.close()
    conn.close()


def create_table_requests():
    conn = pymssql.connect(server, user, password, db)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE requests (
        req_id INT IDENTITY(1, 1) PRIMARY KEY,
        user_id VARCHAR(20),
        username VARCHAR(50),
        req_status VARCHAR(20)
    )
    """)
        conn.commit()
        print('Создали requests')
    except:
        print('Таблица requests уже создана. Если хотите ее удалить воспользуйтесь функцией delete_table')
    cursor.close()
    conn.close()


def create_table_messages():
    conn = pymssql.connect(server, user, password, db)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE messages (
        id INT IDENTITY(1, 1) PRIMARY KEY,
        req_id NVARCHAR(20),
        message NTEXT,
        source NVARCHAR(30),
        user_status NVARCHAR(20),
        date NVARCHAR(50),
    )
    """)
        conn.commit()
        print('Создали messages')
    except:
        print('Таблица messages уже создана. Если хотите ее удалить воспользуйтесь функцией delete_table')
    cursor.close()
    conn.close()


def delete_table(table):
    conn = pymssql.connect(server, user, password, db)
    cursor = conn.cursor()
    try:
        cursor.execute(f'DROP TABLE {table}')
        conn.commit()
        print(f'Успешно удалили {table}')
    except:
        print('Что-то пошло не по плану. праверьте таблицу')
    cursor.close()
    conn.close()


def creating():
    create_table_agents()
    create_table_passwords()
    create_table_files()
    create_table_requests()
    create_table_messages()


def deleting():
    tables = [
        'agents',
        'passwords',
        'files',
        'requests',
        'messages'
    ]
    for table in tables:
        delete_table(table)


if __name__ == '__main__':
    creating()
    # deleting()
