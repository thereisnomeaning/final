import sqlite3


DB_DAME = 'database.db'
PROMPTS_TABLE = 'prompts'
LIMITS_TABLE = 'limits'


# Функция выполнения запроса к БД.
def execute_query(query, data=None):
    cursor, connection = get_cursor()

    if data:
        result = cursor.execute(query, data).fetchall()
    else:
        result = cursor.execute(query).fetchall()

    connection.commit()
    connection.close()

    return result


# Создаем курсор.
def get_cursor():
    connection = sqlite3.connect(DB_DAME)
    return connection.cursor(), connection


# Создание таблицы промптов.
def create_table_prompts():
    query = f'''
    CREATE TABLE IF NOT EXISTS {PROMPTS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    role TEXT,
    message TEXT);
    '''
    execute_query(query)


# Создание таблицы лимитов пользователей.
def create_table_limits():
    query = f'''
    CREATE TABLE IF NOT EXISTS {LIMITS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    total_gpt_tokens INTEGER DEFAULT 0,
    total_tts_tokens INTEGER DEFAULT 0,
    total_stt_blocks INTEGER DEFAULT 0);
    '''
    execute_query(query)


# Добавление строки в таблицу промптов.
def insert_row_into_prompts(values):
    query = f'''
    INSERT INTO {PROMPTS_TABLE}
    (user_id, role, message)
    VALUES(?, ?, ?);
    '''
    execute_query(query, values)


# Добавление строки в таблицу лимитов пользователей.
def insert_row_into_limits(user_id):
    query = f'''
    INSERT INTO {LIMITS_TABLE}
    (user_id)
    VALUES({user_id});
    '''
    execute_query(query)


# Обновление ттс токенов в таблице лимитов пользователей.
def update_tts_tokens_in_limits(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_tts_tokens = total_tts_tokens + {value}
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Обновление стт блоков в таблице лимитов пользователей.
def update_stt_blocks_in_limits(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_stt_blocks = total_stt_blocks + {value}
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Обновление гпт токенов в таблице лимитов пользователей.
def update_gpt_tokens_in_limits(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_gpt_tokens = total_gpt_tokens + {value}
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Получение ттс токенов из таблицы лимитов пользователей.
def get_tts_tokens(user_id):
    query = f'''
    SELECT total_tts_tokens FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)

    return result[0][0]


# Получение стт блоков из таблицы лимитов пользователей.
def get_stt_blocks(user_id):
    query = f'''
    SELECT total_stt_blocks FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)

    return result[0][0]


# Получение гпт токенов из таблицы лимитов пользователей.
def get_gpt_tokens(user_id):
    query = f'''
    SELECT total_gpt_tokens FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)

    return result[0][0]


# Получение всех промптов пользователя.
def get_user_prompts(user_id):
    query = f'''
    SELECT message FROM {PROMPTS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)
    return ' '.join(list(map(lambda x: x[0], result)))


# Получение всех различных id пользователей.
def all_users():
    query = f'''
    SELECT COUNT(DISTINCT user_id) AS unique_count_users FROM {LIMITS_TABLE};
    '''
    result = execute_query(query)

    return result[0][0]


# Проверяем есть ли пользователь в таблице
def user_in_table(user_id):
    query = f'''
    SELECT EXISTS(SELECT 1 FROM {LIMITS_TABLE} WHERE user_id = {user_id});
    '''
    result = execute_query(query)

    return result[0][0]


#con = sqlite3.connect(DB_DAME)
#cur = con.cursor()
#cur.execute('DROP TABLE IF EXISTS prompts;')
#cur.execute('DROP TABLE IF EXISTS limits;')
#con.commit()
#con.close()