import config
import datetime
import random
import pymssql


db_server = config.MSSQL[0]
db_user = config.MSSQL[1]
db_password = config.MSSQL[2]
db_title = config.MSSQL[3]


# Добавить агента
def add_agent(agent_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"INSERT INTO agents VALUES (%s)", (agent_id))
    con.commit()

    cur.close()
    con.close()



# Добавить файл
def add_file(req_id, file_id, file_name, type):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"INSERT INTO files VALUES (%s, %s, %s, %s)", (req_id, file_id, file_name, type))
    con.commit()

    cur.close()
    con.close()




# Создать запрос
def new_req(user_id, request, source, username):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    # Добавить запрос в БД
    cur.execute(f"INSERT INTO requests VALUES (%s, %s, %s)", (user_id, username, 'waiting'))

    # Получить айди добавленного запроса
    req_id = cur.lastrowid

    dt = datetime.datetime.now()
    date_now = dt.strftime('%d.%m.%Y %H:%M:%S')

    # Добавить сообщение для запроса
    cur.execute(f"INSERT INTO messages VALUES (%s, %s, %s, %s, %s)", (req_id, request, source, 'user', date_now))

    con.commit()

    cur.close()
    con.close()

    return req_id




# Добавить сообщение
def add_message(req_id, message, user_status, source):
    if user_status == 'user':
        req_status = 'waiting'
    elif user_status == 'agent':
        req_status = 'answered'

    dt = datetime.datetime.now()
    date_now = dt.strftime('%d.%m.%Y %H:%M:%S')

    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    # Добавить сообщение для запроса
    cur.execute(f"INSERT INTO messages VALUES (%s, %s, %s, %s, %s)", (req_id, message, source, user_status, date_now))

    # Изменить статус запроса
    cur.execute(f"UPDATE requests SET req_status = (%s) WHERE req_id = (%s)", (req_status, req_id))

    con.commit()

    cur.close()
    con.close()




# Добавить пароли
def add_passwords(passwords):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    for password in passwords:
        cur.execute(f"INSERT INTO passwords VALUES (%s)", (password))

    con.commit()

    cur.close()
    con.close()


# Проверить статус агента
def check_agent_status(user_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"SELECT * FROM agents WHERE agent_id=%s", (user_id))
    agent = cur.fetchone()

    cur.close()
    con.close()

    if agent == None:
        return False
    else:
        return True


# Проверить валидность пароля
def valid_password(password):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"SELECT * FROM passwords WHERE password=%s", (password))
    password = cur.fetchone()

    cur.close()
    con.close()

    if password == None:
        return False
    else:
        return True


# Проверить отправляет ли пользователь файл, если да - вернуть его
def get_file(message):
    """
    Атрибут file_name доступен только в типах файлов - document и video.
    Если пользователь отправляет не документ и не видео - в качестве имени файла передать дату и время отправки (date_now)
    """

    types = ['document', 'video', 'audio', 'voice']
    dt = datetime.datetime.now()
    date_now = dt.strftime('%d.%m.%Y %H:%M:%S')

    # Сначала проверить отправляет ли пользователь фото
    try:
        return {'file_id': message.json['photo'][-1]['file_id'], 'file_name': date_now, 'type': 'photo',
                'text': str(message.caption)}

    # Если нет - проверить отправляет ли документ, видео, аудио, голосовое сообщение
    except:
        for type in types:
            try:
                if type == 'document' or type == 'video':
                    file_name = message.json[type]['file_name']
                else:
                    file_name = date_now

                return {'file_id': message.json[type]['file_id'], 'file_name': file_name, 'type': type,
                        'text': str(message.caption)}
            except:
                pass

        return None


# Получить иконку статуса запроса
def get_icon_from_status(req_status, user_status):
    if req_status == 'confirm':
        return '✅'

    elif req_status == 'waiting':
        if user_status == 'user':
            return '⏳'
        elif user_status == 'agent':
            return '❗️'

    elif req_status == 'answered':
        if user_status == 'user':
            return '❗️'
        elif user_status == 'agent':
            return '⏳'


# Получить текст для кнопки с файлом
def get_file_text(file_name, type):
    if type == 'photo':
        return f'📷 | Фото {file_name}'
    elif type == 'document':
        return f'📄 | Документ {file_name}'
    elif type == 'video':
        return f'🎥 | Видео {file_name}'
    elif type == 'audio':
        return f'🎵 | Аудио {file_name}'
    elif type == 'voice':
        return f'🎧 | Голосовое сообщение {file_name}'


# Сгенерировать пароли
def generate_passwords(number, lenght):
    chars = 'abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

    passsords = []
    for _ in range(number):
        password = ''
        for _ in range(lenght):
            password += random.choice(chars)

        passsords.append(password)

    return passsords


# Получить юзер айди пользователя, создавшего запрос
def get_user_id_of_req(req_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"SELECT user_id FROM requests WHERE req_id=%s", (req_id))
    user_id = cur.fetchone()[0]

    cur.close()
    con.close()

    return user_id


# Получить file_id из id записи в БД
def get_file_id(id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"SELECT file_id FROM files WHERE id=%s", (id))
    file_id = cur.fetchone()[0]

    cur.close()
    con.close()

    return file_id


# Получить статус запроса
def get_req_status(req_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"SELECT req_status FROM requests WHERE req_id=%s", (req_id))
    req_status = cur.fetchone()[0]

    cur.close()
    con.close()

    return req_status


# Удалить пароль
def delete_password(password):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"DELETE FROM passwords WHERE password = %s", (password))
    con.commit()

    cur.close()
    con.close()


# Удалить агента
def delete_agent(agent_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"DELETE FROM agents WHERE agent_id = %s", (agent_id))
    con.commit()

    cur.close()
    con.close()


# Завершить запрос
def confirm_req(req_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"UPDATE requests SET req_status = (%s) WHERE req_id = (%s)", ('confirm', req_id))
    con.commit()

    cur.close()
    con.close()


# Получить пароли с лимитом
def get_passwords(number):
    limit = (int(number) * 10) - 10

    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"""
                    SELECT password
                    FROM passwords
                    ORDER BY id
                    OFFSET {limit} ROWS
                    FETCH NEXT 10 ROWS ONLY 
                    """, (limit))
    passwords = cur.fetchall()

    cur.close()
    con.close()

    return passwords


# Получить агентов с лимитом
def get_agents(number):
    limit = (int(number) * 10) - 10
    # limit = number
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"""
                    SELECT agent_id
                    FROM agents
                    ORDER BY id
                    OFFSET {limit} ROWS
                    FETCH NEXT 10 ROWS ONLY 
                    """, (limit))
    agents = cur.fetchall()

    cur.close()
    con.close()

    return agents

# print(get_agents(0))

# Получить мои запросы с лимитом
def my_reqs(number, user_id):
    limit = (int(number) * 10) - 10

    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute("""
                SELECT req_id, req_status, username
                FROM requests
                WHERE user_id = (%s)
                ORDER BY req_id DESC
                OFFSET %d ROWS
                FETCH NEXT 10 ROWS ONLY 
                """, (user_id, limit))
    reqs = cur.fetchall()

    cur.close()
    con.close()

    return reqs


# Получить запросы по статусу с лимитом
def get_reqs(number, callback):
    limit = (int(number) * 10) - 10
    req_status = callback.replace('_reqs', '')

    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute("""
            SELECT req_id, req_status, username
            FROM requests
            WHERE req_status = (%s)
            ORDER BY req_id DESC
            OFFSET %d ROWS
            FETCH NEXT 10 ROWS ONLY 
            """, (req_status, limit))
    reqs = cur.fetchall()

    cur.close()
    con.close()

    return reqs

def get_msg_info(req_id):
    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute("""
            SELECT message, source
            FROM messages
            WHERE req_id = (%s)
            """, (req_id))
    result = cur.fetchone()

    cur.close()
    con.close()

    return result

# Получить файлы по запросу с лимитом
def get_files(number, req_id):
    limit = (int(number) * 10) - 10

    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    # cur.execute(f"SELECT id, file_name, type FROM files WHERE req_id = (%s) ORDER BY id DESC BETWEEN %d AND 10", (req_id, limit))
    cur.execute("""
        SELECT id, file_name, type
        FROM files
        WHERE req_id = (%s)
        ORDER BY id DESC
        OFFSET %d ROWS
        FETCH NEXT 10 ROWS ONLY 
        """, (req_id, limit))
    files = cur.fetchall()

    cur.close()
    con.close()

    return files


# Получить историю запроса
def get_request_data(req_id, callback):
    if 'my_reqs' in callback:
        get_dialog_user_status = 'user'
    else:
        get_dialog_user_status = 'agent'

    con = pymssql.connect(db_server, db_user, db_password, db_title)
    cur = con.cursor()

    cur.execute(f"SELECT message, user_status, date, source FROM messages WHERE req_id=%s", (req_id))
    messages = cur.fetchall()

    cur.close()
    con.close()

    data = []
    text = ''
    i = 1

    sources = {
        'source_1': '1',
        'source_2': '2',
        'source_3': '3',
        'source_4': '4',
        'source_5': '5',
        'source_6': '6',
    }
    for message in messages:
        message_value = message[0]
        user_status = message[1]
        date = message[2]
        source = sources.get(message[3])

        if user_status == 'user':
            if get_dialog_user_status == 'user':
                text_status = '👤 Ваше сообщение'
            else:
                text_status = '👤 Сообщение пользователя'
        elif user_status == 'agent':
            text_status = '🧑‍💻 Агент поддержки'

        # Бэкап для текста
        backup_text = text
        text += f'{text_status}\n<b>Площадка</b> {source}\n{date}\n{message_value}\n\n'

        # Если размер текста превышает допустимый в Telegram, то добавить первую часть текста и начать вторую
        if len(text) >= 4096:
            data.append(backup_text)
            text = f'{text_status}\n{date}\n{message_value}\n\n'

        # Если сейчас последняя итерация, то проверить не является ли часть текста превыщающий допустимый размер (4096 символов). Если превышает - добавить часть и начать следующую. Если нет - просто добавить последнюю часть списка.
        if len(messages) == i:
            if len(text) >= 4096:
                data.append(backup_text)
                text = f'{text_status}\n{date}\n{message_value}\n\n'

            data.append(text)

        i += 1

    return data