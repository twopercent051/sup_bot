import sys
import logging
import telebot
import time
from telebot import apihelper

import config
import core_mssql
import markup

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
)
logger.info("Starting bot")

if config.PROXY_URL:
    apihelper.proxy = {'https': config.PROXY_URL}

bot = telebot.TeleBot(config.TOKEN, skip_pending=True)


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    if core_mssql.check_agent_status(user_id):
        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html',
                         reply_markup=markup.markup_agent())
    else:
        bot.send_message(message.chat.id,
                         '👋🏻 Привет! Это бот для технической поддержки пользователей.\nЕсли у тебя есть какой-либо '
                         'вопрос или проблема - нажми на кнопку <b>Написать запрос</b> и наши сотрудники в скором '
                         'времени тебе ответят!',
                         parse_mode='html', reply_markup=markup.markup_main())


@bot.message_handler(commands=['agent'])
def agent(message):
    user_id = message.from_user.id

    if core_mssql.check_agent_status(user_id):
        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html',
                         reply_markup=markup.markup_agent())

    else:
        take_password_message = bot.send_message(message.chat.id,
                                                 '⚠️ Тебя нет в базе. Отправь одноразовый пароль доступа.',
                                                 reply_markup=markup.markup_cancel())

        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_password_message, get_password_message)


@bot.message_handler(commands=['admin'])
def admin(message):
    user_id = message.from_user.id

    if str(user_id) == config.ADMIN_ID:
        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Админ', reply_markup=markup.markup_admin())
    else:
        bot.send_message(message.chat.id, '🚫 Эта команда доступна только администратору.')


@bot.message_handler(regexp='✏️ Написать запрос')
def get_source(message):
    message.from_user.id
    text = 'Выберите площадку'
    bot.send_message(message.chat.id, text, reply_markup=markup.markup_sources())


@bot.message_handler(content_types=['text'])
def send_text(message):
    user_id = message.from_user.id

    if message.text == '✏️ Написать запрос':
        take_new_request = bot.send_message(message.chat.id,
                                            'Введите свой запрос и наши сотрудники скоро с вами свяжутся.',
                                            reply_markup=markup.markup_cancel())

        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_new_request, get_new_request)

    elif message.text == '✉️ Мои запросы':
        markup_and_value = markup.markup_reqs(user_id, 'my_reqs', '1')
        markup_req = markup_and_value[0]
        value = markup_and_value[1]

        if value == 0:
            bot.send_message(message.chat.id, 'У вас пока ещё нет запросов.', reply_markup=markup.markup_main())
        else:
            bot.send_message(message.chat.id, 'Ваши запросы:', reply_markup=markup_req)

    else:
        bot.send_message(message.chat.id, 'Вы возвращены в главное меню.', parse_mode='html',
                         reply_markup=markup.markup_main())


def get_password_message(message):
    password = message.text
    user_id = message.from_user.id

    if password is None:
        send_message = bot.send_message(message.chat.id, '⚠️ Вы отправляете не текст. Попробуйте еще раз.',
                                        reply_markup=markup.markup_cancel())

        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(send_message, get_password_message)

    elif password.lower() == 'отмена':
        bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
        return

    elif core_mssql.valid_password(password):
        core_mssql.delete_password(password)
        core_mssql.add_agent(user_id)

        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html',
                         reply_markup=markup.markup_main())
        bot.send_message(message.chat.id, 'Выберите раздел технической панели:', parse_mode='html',
                         reply_markup=markup.markup_agent())

    else:
        send_message = bot.send_message(message.chat.id, '⚠️ Неверный пароль. Попробуй ещё раз.',
                                        reply_markup=markup.markup_cancel())

        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(send_message, get_password_message)


def get_agent_id_message(message):
    agent_id = message.text

    if agent_id is None:
        take_agent_id_message = bot.send_message(message.chat.id, '⚠️ Вы отправляете не текст. Попробуйте еще раз.',
                                                 reply_markup=markup.markup_cancel())

        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_agent_id_message, get_agent_id_message)

    elif agent_id.lower() == 'отмена':
        bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
        return

    else:
        core_mssql.add_agent(agent_id)
        bot.send_message(message.chat.id, '✅ Агент успешно добавлен.', reply_markup=markup.markup_main())
        bot.send_message(message.chat.id, 'Выберите раздел админ панели:', reply_markup=markup.markup_admin())


def get_new_request(message, source):
    request = message.text
    user_id = message.from_user.id
    username = f'@{message.from_user.username}'
    check_file = core_mssql.get_file(message)

    # Если пользователь отправляет файл
    if check_file is not None:
        file_id = check_file['file_id']
        file_name = check_file['file_name']
        file_type = check_file['type']
        request = check_file['text']

        if str(request) == 'None':
            take_new_request = bot.send_message(message.chat.id,
                                                '⚠️ Вы не ввели ваш запрос. Попробуйте ещё раз, отправив текст вместе '
                                                'с файлом.',
                                                reply_markup=markup.markup_cancel())

            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.register_next_step_handler(take_new_request, get_new_request, source)

        else:
            req_id = core_mssql.new_req(user_id, request, source, username)
            core_mssql.add_file(req_id, file_id, file_name, file_type)

            bot.send_message(message.chat.id,
                             f'✅ Ваш запрос под ID {req_id} создан. Посмотреть текущие запросы можно нажав кнопку '
                             f'<b>Мои текущие запросы</b>',
                             parse_mode='html', reply_markup=markup.markup_main())

            # Если пользователь отправляет только текст
    else:
        if request is None:
            take_new_request = bot.send_message(message.chat.id,
                                                '⚠️ Отправляемый вами тип данных не поддерживается в боте. Попробуйте '
                                                'еще раз отправить ваш запрос, использовав один из доступных типов '
                                                'данных (текст, файлы, фото, видео, аудио, голосовые сообщения)',
                                                reply_markup=markup.markup_cancel())

            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.register_next_step_handler(take_new_request, get_new_request, source)

        elif request.lower() == 'отмена':
            bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
            return

        else:
            req_id = core_mssql.new_req(user_id, request, source, username)
            bot.send_message(message.chat.id,
                             f'✅ Ваш запрос под ID {req_id} создан. Посмотреть текущие запросы можно нажав кнопку '
                             f'<b>Мои текущие запросы</b>',
                             parse_mode='html', reply_markup=markup.markup_main())


def get_additional_message(message, req_id, status):
    additional_message = message.text
    check_file = core_mssql.get_file(message)

    # Если пользователь отправляет файл
    if check_file is not None:
        file_id = check_file['file_id']
        file_name = check_file['file_name']
        file_type = check_file['type']
        additional_message = check_file['text']

        core_mssql.add_file(req_id, file_id, file_name, file_type)

    if additional_message is None:
        take_additional_message = bot.send_message(chat_id=message.chat.id,
                                                   text='⚠️ Отправляемый вами тип данных не поддерживается в боте. '
                                                        'Попробуйте еще раз отправить ваше сообщение, использовав '
                                                        'один из доступных типов данных (текст, файлы, фото, видео, '
                                                        'аудио, голосовые сообщения).',
                                                   reply_markup=markup.markup_cancel())

        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_additional_message, get_additional_message, req_id, status)

    elif additional_message.lower() == 'отмена':
        bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
        return

    else:
        if additional_message != 'None':
            source = ''
            core_mssql.add_message(req_id, additional_message, status, source)

        if check_file is not None:
            if additional_message != 'None':
                text = '✅ Ваш файл и сообщение успешно отправлены!'
            else:
                text = '✅ Ваш файл успешно отправлен!'
        else:
            text = '✅ Ваше сообщение успешно отправлено!'

        bot.send_message(message.chat.id, text, reply_markup=markup.markup_main())

        if status == 'agent':
            user_id = core_mssql.get_user_id_of_req(req_id)
            try:
                if additional_message == 'None':
                    additional_message = ''

                bot.send_message(user_id,
                                 f'⚠️ Получен новый ответ на ваш запрос ID {req_id}!\n\n🧑‍💻 Ответ агента поддержки:\n{additional_message}',
                                 reply_markup=markup.markup_main())

                if type == 'photo':
                    bot.send_photo(user_id, photo=file_id, reply_markup=markup.markup_main())
                elif type == 'document':
                    bot.send_document(user_id, data=file_id, reply_markup=markup.markup_main())
                elif type == 'video':
                    bot.send_video(user_id, data=file_id, reply_markup=markup.markup_main())
                elif type == 'audio':
                    bot.send_audio(user_id, audio=file_id, reply_markup=markup.markup_main())
                elif type == 'voice':
                    bot.send_voice(user_id, voice=file_id, reply_markup=markup.markup_main())
                else:
                    bot.send_message(user_id, additional_message, reply_markup=markup.markup_main())
            except:
                pass

def push(req_id):
    text = f'⚠️ Агент поддержки закрыл Ваш запрос ID {req_id}'
    user_id = core_mssql.get_user_id_of_req(req_id)
    bot.send_message(user_id, text)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.message.chat.id

    sources = [
        'source_1',
        'source_2',
        'source_3',
        'source_4',
        'source_5',
        'source_6',
    ]

    if call.message:
        if call.data in sources:

            take_new_request = bot.send_message(call.message.chat.id,
                                                'Введите свой запрос и наши сотрудники скоро с вами свяжутся.',
                                                reply_markup=markup.markup_cancel())

            bot.clear_step_handler_by_chat_id(call.message.chat.id)
            bot.register_next_step_handler(take_new_request, get_new_request, call.data)

        if ('my_reqs:' in call.data) or ('waiting_reqs:' in call.data) or ('answered_reqs:' in call.data) or (
                'confirm_reqs:' in call.data):
            """
            Обработчик кнопок для:

            ✉️ Мои запросы
            ❗️ Ожидают ответа от поддержки,
            ⏳ Ожидают ответа от пользователя
            ✅ Завершенные запросы  
            """

            parts = call.data.split(':')
            callback = parts[0]
            number = parts[1]
            markup_and_value = markup.markup_reqs(user_id, callback, number)
            markup_req = markup_and_value[0]
            value = markup_and_value[1]

            if value == 0:
                bot.send_message(chat_id=call.message.chat.id, text='⚠️ Запросы не обнаружены.',
                                 reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Нажмите на запрос, чтобы посмотреть историю переписки, либо добавить '
                                           'сообщение:',
                                      reply_markup=markup_req)
            except:
                bot.send_message(chat_id=call.message.chat.id, text='Ваши запросы:', reply_markup=markup_req)

            bot.answer_callback_query(call.id)

        # Открыть запрос
        elif 'open_req:' in call.data:
            parts = call.data.split(':')
            req_id = parts[1]
            callback = parts[2]

            req_status = core_mssql.get_req_status(req_id)
            request_data = core_mssql.get_request_data(req_id, callback)
            len_req_data = len(request_data)

            i = 1
            for data in request_data:
                if i == len_req_data:
                    markup_req = markup.markup_request_action(req_id, req_status, callback)
                else:
                    markup_req = None

                bot.send_message(chat_id=call.message.chat.id, text=data, parse_mode='html', reply_markup=markup_req)

                i += 1

            bot.answer_callback_query(call.id)

        # Добавить сообщение в запрос
        elif 'add_message:' in call.data:
            parts = call.data.split(':')
            req_id = parts[1]
            status_user = parts[2]

            take_additional_message = bot.send_message(chat_id=call.message.chat.id,
                                                       text='Отправьте ваше сообщение, использовав один из доступных '
                                                            'типов данных (текст, файлы, фото, видео, аудио, '
                                                            'голосовые сообщения)',
                                                       reply_markup=markup.markup_cancel())

            bot.register_next_step_handler(take_additional_message, get_additional_message, req_id, status_user)

            bot.answer_callback_query(call.id)

        # Завершить запрос
        elif 'confirm_req:' in call.data:
            parts = call.data.split(':')
            confirm_status = parts[1]
            req_id = parts[2]

            if core_mssql.get_req_status(req_id) == 'confirm':
                bot.send_message(chat_id=call.message.chat.id, text="⚠️ Этот запрос уже завершен.",
                                 reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)

                return

            # Запросить подтверждение завершения
            if confirm_status == 'wait':
                user_id = call.message.chat.id
                is_agent = core_mssql.check_agent_status(user_id)
                bot.send_message(chat_id=call.message.chat.id,
                                 text="Для завершения запроса - нажмите кнопку <b>Подтвердить</b>", parse_mode='html',
                                 reply_markup=markup.markup_confirm_req(req_id, is_agent))

            # Подтвердить завершение
            elif confirm_status == 'true':
                core_mssql.confirm_req(req_id)
                is_agent = parts[3]
                try:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text="✅ Запрос успешно завершён.", reply_markup=markup.markup_main())
                except:
                    bot.send_message(chat_id=call.message.chat.id, text="✅ Запрос успешно завершён.",
                                     reply_markup=markup.markup_main())
                if is_agent == 'True':
                    push(req_id)
                bot.answer_callback_query(call.id)

        # Файлы запроса
        elif 'req_files:' in call.data:
            parts = call.data.split(':')
            req_id = parts[1]
            callback = parts[2]
            number = parts[3]

            markup_and_value = markup.markup_files(number, req_id, callback)
            markup_files = markup_and_value[0]
            value = markup_and_value[1]

            if value == 0:
                bot.send_message(chat_id=call.message.chat.id, text='⚠️ Файлы не обнаружены.',
                                 reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Нажмите на файл, чтобы получить его.', reply_markup=markup_files)
            except:
                bot.send_message(chat_id=call.message.chat.id, text='Нажмите на файл, чтобы получить его.',
                                 reply_markup=markup_files)

            bot.answer_callback_query(call.id)

        # Отправить файл
        elif 'send_file:' in call.data:
            parts = call.data.split(':')
            id = parts[1]
            file_type = parts[2]

            file_id = core_mssql.get_file_id(id)

            if file_type == 'photo':
                bot.send_photo(call.message.chat.id, photo=file_id, reply_markup=markup.markup_main())
            elif file_type == 'document':
                bot.send_document(call.message.chat.id, document=file_id, reply_markup=markup.markup_main())
            elif file_type == 'video':
                bot.send_video(call.message.chat.id, data=file_id, reply_markup=markup.markup_main())
            elif file_type == 'audio':
                bot.send_audio(call.message.chat.id, audio=file_id, reply_markup=markup.markup_main())
            elif file_type == 'voice':
                bot.send_voice(call.message.chat.id, voice=file_id, reply_markup=markup.markup_main())

            bot.answer_callback_query(call.id)

        # Вернуться назад в панель агента
        elif call.data == 'back_agent':
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='🔑 Вы авторизованы как Агент поддержки', parse_mode='html',
                                      reply_markup=markup.markup_agent())
            except:
                bot.send_message(call.message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html',
                                 reply_markup=markup.markup_agent())

            bot.answer_callback_query(call.id)

        # Вернуться назад в панель админа
        elif call.data == 'back_admin':
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='🔑 Вы авторизованы как Админ', parse_mode='html',
                                      reply_markup=markup.markup_admin())
            except:
                bot.send_message(call.message.chat.id, '🔑 Вы авторизованы как Админ', parse_mode='html',
                                 reply_markup=markup.markup_admin())

            bot.answer_callback_query(call.id)

        # Добавить агента
        elif call.data == 'add_agent':
            take_agent_id_message = bot.send_message(chat_id=call.message.chat.id,
                                                     text='Чтобы добавить агента поддержки - введите его ID Telegram.',
                                                     reply_markup=markup.markup_cancel())
            bot.register_next_step_handler(take_agent_id_message, get_agent_id_message)

        # Все агенты
        elif 'all_agents:' in call.data:
            number = call.data.split(':')[1]
            markup_and_value = markup.markup_agents(number)
            markup_agents = markup_and_value[0]
            len_agents = markup_and_value[1]

            if len_agents == 0:
                bot.send_message(chat_id=call.message.chat.id, text='⚠️ Агенты не обнаружены.',
                                 reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Нажмите на агента поддержки, чтобы удалить его', parse_mode='html',
                                      reply_markup=markup_agents)
            except:
                bot.send_message(call.message.chat.id, 'Нажмите на агента поддержки, чтобы удалить его',
                                 parse_mode='html', reply_markup=markup_agents)

            bot.answer_callback_query(call.id)

        # Удалить агента
        elif 'delete_agent:' in call.data:
            agent_id = call.data.split(':')[1]
            core_mssql.delete_agent(agent_id)

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Нажмите на агента поддержки, чтобы удалить его', parse_mode='html',
                                      reply_markup=markup.markup_agents('1')[0])
            except:
                bot.send_message(call.message.chat.id, 'Нажмите на агента поддержки, чтобы удалить его',
                                 parse_mode='html', reply_markup=markup.markup_agents('1')[0])

            bot.answer_callback_query(call.id)

        # Все пароли
        elif 'all_passwords:' in call.data:
            number = call.data.split(':')[1]
            markup_and_value = markup.markup_passwords(number)
            markup_passwords = markup_and_value[0]
            len_passwords = markup_and_value[1]

            if len_passwords == 0:
                bot.send_message(chat_id=call.message.chat.id, text='⚠️ Пароли не обнаружены.',
                                 reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Нажмите на пароль, чтобы удалить его', parse_mode='html',
                                      reply_markup=markup_passwords)
            except:
                bot.send_message(call.message.chat.id, 'Нажмите на пароль, чтобы удалить его', parse_mode='html',
                                 reply_markup=markup_passwords)

            bot.answer_callback_query(call.id)

        # Удалить пароль
        elif 'delete_password:' in call.data:
            password = call.data.split(':')[1]
            core_mssql.delete_password(password)

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Нажмите на пароль, чтобы удалить его', parse_mode='html',
                                      reply_markup=markup.markup_passwords('1')[0])
            except:
                bot.send_message(call.message.chat.id, 'Нажмите на пароль, чтобы удалить его', parse_mode='html',
                                 reply_markup=markup.markup_passwords('1')[0])

            bot.answer_callback_query(call.id)

        # Сгенерировать пароли
        elif call.data == 'generate_passwords':
            # 10 - количество паролей, 16 - длина пароля
            passwords = core_mssql.generate_passwords(10, 16)
            core_mssql.add_passwords(passwords)

            text_passwords = ''
            i = 1
            for password in passwords:
                text_passwords += f'{i}. {password}\n'
                i += 1

            bot.send_message(call.message.chat.id, f"✅ Сгенерировано {i - 1} паролей:\n\n{text_passwords}",
                             parse_mode='html', reply_markup=markup.markup_main())
            bot.send_message(call.message.chat.id, 'Нажмите на пароль, чтобы удалить его', parse_mode='html',
                             reply_markup=markup.markup_passwords('1')[0])

            bot.answer_callback_query(call.id)

        # Остановить бота
        elif 'stop_bot:' in call.data:
            status = call.data.split(':')[1]

            # Запросить подтверждение на отключение
            if status == 'wait':
                try:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=f"Вы точно хотите отключить бота?", parse_mode='html',
                                          reply_markup=markup.markup_confirm_stop())
                except:
                    bot.send_message(call.message.chat.id, f"Вы точно хотите отключить бота?", parse_mode='html',
                                     reply_markup=markup.markup_confirm_stop())

            # Подтверждение получено
            elif status == 'confirm':
                try:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text='✅ Бот оключен.')
                except:
                    bot.send_message(chat_id=call.message.chat.id, text='✅ Бот оключен.')

                bot.answer_callback_query(call.id)
                bot.stop_polling()
                sys.exit()


if __name__ == "__main__":

    bot.polling(none_stop=True)
    # while True:
    #     try:
    #         logging.info("Bot running..")
    #         bot.polling(none_stop=True, interval=2)
    #     except Exception as e:
    #         logging.error(e)
    #         time.sleep(15)
    #         logging.info("Running again!")
