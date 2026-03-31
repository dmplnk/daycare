import html
import logging
import os
from datetime import datetime, timedelta

import telebot
from telebot import types
from dotenv import load_dotenv

from connect import Connect_base

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotExceptionHandler(telebot.ExceptionHandler):
    """Иначе любое необработанное исключение в потоке polling останавливает бота."""

    def handle(self, exception):
        logger.exception("Необработанная ошибка в обработчике: %s", exception)
        return True


bot = telebot.TeleBot(os.getenv("BOT_TOKEN"), exception_handler=BotExceptionHandler())

# Состояние по chat_id вместо глобальных переменных
user_data = {}


def get_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {}
    return user_data[chat_id]


ENG_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
RUS_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
WEEKDAY_RU = dict(zip(ENG_WEEKDAYS, RUS_WEEKDAYS))


def weekday_ru(dt):
    return WEEKDAY_RU.get(dt.strftime("%A"))


def db_connect():
    return Connect_base().connect_base()


def delete_msg_safe(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def format_schedule_rows(rows):
    lines = []
    for start, end, class_name in rows:
        lines.append(f"{str(start)[:5]} - {str(end)[:5]} {class_name}")
    return "\n".join(lines)


def format_group_kids(rows):
    lines = []
    for surname, name, patronymic, gender in rows:
        emoji = "👧🏼" if gender == "женский" else "🧒🏼"
        lines.append(f"{surname} {name} {patronymic} {emoji}")
    return "\n".join(lines)


def fetch_schedule(cursor, group_id, week_day_ru):
    cursor.execute(
        """(select start_time, end_time, class.name
           from kidgarten.schedule
           join kidgarten.tutor on kidgarten.schedule.tutor_id = kidgarten.tutor.id
           join kidgarten.class on kidgarten.schedule.class_id = kidgarten.class.id
           where group_id = %s
             and (week_day = 'каждый день' or week_day = %s)
           order by start_time)""",
        (int(group_id), week_day_ru),
    )
    return cursor.fetchall()


def send_kids_menu(chat_id, parent_id):
    conn = db_connect()
    if not conn:
        bot.send_message(chat_id, "Ошибка подключения к базе.")
        return
    cursor = conn.cursor()
    cursor.execute(
        """select name, gender, id, surname from kid
           inner join kid_has_parent on kid.id = kid_has_parent.kid_id
           where parent_id = %s""",
        (parent_id,),
    )
    kids = cursor.fetchall()
    kb = types.InlineKeyboardMarkup()
    for name, gender, kid_id, _surname in kids:
        emoji = "👧🏼" if gender == "женский" else "🧒🏼"
        kb.add(types.InlineKeyboardButton(name + emoji, callback_data=f"kid:{kid_id}"))
    bot.send_message(
        chat_id,
        "Выберите ребенка, для которого будут выполнены команды:",
        reply_markup=kb,
    )


def schedule_keyboard(back_cb, other_label, other_cb):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("Назад", callback_data=back_cb),
        types.InlineKeyboardButton(other_label, callback_data=other_cb),
    )
    return kb


@bot.message_handler(commands=["start"])
def greetings(message):
    u = get_user(message.chat.id)
    u["await_phone"] = False
    u["await_tutor_message"] = False
    u["await_pass_date"] = False
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Авторизация", callback_data="to_avtorisation"))
    bot.send_message(
        message.chat.id,
        "Добрый день, Родитель!🔅\n\n"
        "Я - <b>Daycarebot</b>. Я умею сообщать о новостях сада. "
        "Делаю быстрым и удобным ваше общение с воспитателем и отвечаю на различные запросы.\n\n"
        " Для общения со мной вам нужно <b>авторизоваться</b> 📝",
        parse_mode="html",
        reply_markup=kb,
    )


@bot.message_handler(commands=["id"])
def get_id(message):
    bot.send_message(message.chat.id, message.chat.id)


def is_waiting_for_input(message):
    """Фильтр для сообщений после кнопки «ждём ввод» — надёжнее, чем register_next_step_handler."""
    u = get_user(message.chat.id)
    if u.get("await_phone"):
        return message.content_type in ("contact", "text")
    if u.get("await_tutor_message"):
        return message.content_type == "text"
    if u.get("await_pass_date"):
        return message.content_type == "text"
    return False


@bot.message_handler(content_types=["contact", "text"], func=is_waiting_for_input)
def route_waiting_inputs(message):
    u = get_user(message.chat.id)
    if u.get("await_phone"):
        u["await_phone"] = False
        check_phone_num(message)
        return
    if u.get("await_tutor_message") and message.content_type == "text":
        u["await_tutor_message"] = False
        send_mes(message)
        return
    if u.get("await_pass_date") and message.content_type == "text":
        u["await_pass_date"] = False
        send_date(message)
        return


@bot.callback_query_handler(func=lambda c: True)
def on_callback(callback):
    data = callback.data
    chat_id = callback.message.chat.id
    user = get_user(chat_id)
    mid = callback.message.message_id
    try:
        bot.answer_callback_query(callback.id)
    except Exception:
        pass

    if data == "to_avtorisation":
        user["await_phone"] = True
        user["await_tutor_message"] = False
        user["await_pass_date"] = False
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(
            types.KeyboardButton(
                text="Отправить номер телефона 📞",
                request_contact=True,
            )
        )
        delete_msg_safe(chat_id, mid)
        bot.send_message(
            chat_id,
            "Для авторизации нужен ваш <b>номер телефона</b>, нажмите кнопку ниже, чтобы отправить его",
            parse_mode="html",
            reply_markup=kb,
        )
        return

    if data.startswith("kid:"):
        user["await_phone"] = False
        user["await_tutor_message"] = False
        user["await_pass_date"] = False
        kid_id = data.split(":", 1)[1]
        user["kid_id"] = kid_id
        user["save"] = data

        conn = db_connect()
        if not conn:
            bot.send_message(chat_id, "Ошибка подключения к базе. Попробуйте позже.")
            return
        cursor = conn.cursor()
        cursor.execute(
            """select kid.name, surname, patronymic, gender,
                      date_of_birth, age, `group`.name, `group`.id, `group`.tutor_id
               from kid
               inner join `group` on kid.group_idgroup = `group`.id
               where kid.id = %s""",
            (kid_id,),
        )
        kid_info = cursor.fetchone()
        if not kid_info:
            return

        user["kid_name"] = kid_info[0]
        user["kid_surname"] = kid_info[1]
        user["kid_group"] = kid_info[6]
        user["kid_group_id"] = kid_info[7]
        tutor_db_id = kid_info[8]
        user["tutor_db_id"] = tutor_db_id

        emoji = "👧🏼" if kid_info[3] == "женский" else "🧒🏼"

        cursor.execute("select chat_id from tutor where id = %s", (tutor_db_id,))
        tutor_chat = cursor.fetchone()
        user["tutor"] = tutor_chat[0] if tutor_chat else None

        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("Стоим у двери 🔔", callback_data="door"),
            types.InlineKeyboardButton("Одеть ребенка 👕", callback_data="dress"),
        )
        kb.row(types.InlineKeyboardButton("Отправить сообщение воспитателю ✉️", callback_data="message"))
        kb.row(types.InlineKeyboardButton("Сообщить о пропуске ❗️", callback_data="pass"))
        kb.row(
            types.InlineKeyboardButton("Группа ребенка 👨‍👩‍👦‍👦", callback_data="group"),
            types.InlineKeyboardButton("Расписание ребенка ⏰", callback_data="schedule_today"),
        )
        kb.row(types.InlineKeyboardButton("Контакты 📱", callback_data="contacts"))
        kb.row(types.InlineKeyboardButton("Назад", callback_data="choose_kid"))

        delete_msg_safe(chat_id, mid)
        bot.send_message(
            chat_id,
            f"{emoji} {user['kid_name']} {user['kid_surname']}\n\n"
            "Воспользуйтесь кнопками внизу, чтобы сообщить или запросить информацию ⬇️",
            reply_markup=kb,
        )
        return

    if data == "door":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
        delete_msg_safe(chat_id, mid)
        bot.send_message(chat_id, "Уже открываем!", reply_markup=kb)
        if user.get("tutor"):
            bot.send_message(
                user["tutor"],
                f"Сообщение от {user['name']} {user['patronymic']}: "
                f"{user['kid_name']} {user['kid_surname']} уже у дверей, встречайте!🙌🏼\n\n"
                f"Телефон родителя: {user['phone']}",
            )
        return

    if data == "dress":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
        delete_msg_safe(chat_id, mid)
        bot.send_message(chat_id, "Начинаем одевать ребенка!", reply_markup=kb)
        if user.get("tutor"):
            bot.send_message(
                user["tutor"],
                f"Сообщение от {user['name']} {user['patronymic']}: "
                f"просьба одеть {user['kid_name']} {user['kid_surname']} 👕\n\n"
                f"Телефон родителя: {user['phone']}",
            )
        return

    if data == "message":
        user["await_tutor_message"] = True
        user["await_phone"] = False
        user["await_pass_date"] = False
        delete_msg_safe(chat_id, mid)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data=user.get("save", "choose_kid")))
        bot.send_message(
            chat_id,
            "Напишите сообщение, которое хотите передать воспитателю ⬇️",
            reply_markup=kb,
        )
        return

    if data == "pass":
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("Сегодня не придем", callback_data="pass_today"),
            types.InlineKeyboardButton("Завтра не придем", callback_data="pass_tomorrow"),
        )
        kb.row(types.InlineKeyboardButton("Указать другую дату пропуска 📅", callback_data="pass_date"))
        kb.row(types.InlineKeyboardButton("Назад", callback_data=user.get("save", "choose_kid")))
        delete_msg_safe(chat_id, mid)
        bot.send_message(chat_id, "Выберите дату пропуска или укажите свою ⬇️", reply_markup=kb)
        return

    if data == "pass_today":
        delete_msg_safe(chat_id, mid)
        if user.get("tutor"):
            bot.send_message(
                user["tutor"],
                f"Сообщение от {user['name']} {user['patronymic']}: "
                f"сегодня {user['kid_name']} {user['kid_surname']} остается дома 🏠\n\n"
                f"Телефон родителя: {user['phone']}",
            )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
        bot.send_message(chat_id, "Сообщили воспитателю, ждем вас завтра!✨", reply_markup=kb)
        return

    if data == "pass_tomorrow":
        delete_msg_safe(chat_id, mid)
        if user.get("tutor"):
            bot.send_message(
                user["tutor"],
                f"Сообщение от {user['name']} {user['patronymic']}: "
                f"завтра {user['kid_name']} {user['kid_surname']} останется дома 🏠\n\n"
                f"Телефон родителя: {user['phone']}",
            )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
        bot.send_message(chat_id, "Сообщили воспитателю, будем ждать вас!✨", reply_markup=kb)
        return

    if data == "pass_date":
        user["await_pass_date"] = True
        user["await_phone"] = False
        user["await_tutor_message"] = False
        delete_msg_safe(chat_id, mid)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data=user.get("save", "choose_kid")))
        bot.send_message(
            chat_id,
            "Укажите дату пропуска:\n\n📌 Дату укажите в виде числа и месяца",
            reply_markup=kb,
        )
        return

    if data == "group":
        conn = db_connect()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute(
            "select surname, name, patronymic, gender from kid where group_idgroup = %s",
            (user["kid_group_id"],),
        )
        group_kids = cursor.fetchall()
        text = format_group_kids(group_kids)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
        delete_msg_safe(chat_id, mid)
        bot.send_message(
            chat_id,
            f"Группа {user['kid_group']}:\n\n{text}",
            reply_markup=kb,
        )
        return

    if data == "schedule_today":
        cur = datetime.today()
        w = weekday_ru(cur)
        if w in ("Сб", "Вс"):
            kb = schedule_keyboard(user.get("save", "choose_kid"), "Расписание на завтра", "schedule_tomorrow")
            delete_msg_safe(chat_id, mid)
            bot.send_message(
                chat_id,
                f"Расписание нa {cur.date()} {w}\n\nВыходной🎊",
                reply_markup=kb,
            )
            return
        conn = db_connect()
        if not conn:
            return
        cursor = conn.cursor()
        schedule = fetch_schedule(cursor, user["kid_group_id"], w)
        schedule_text = format_schedule_rows(schedule) if schedule else " "
        kb = schedule_keyboard(user.get("save", "choose_kid"), "Расписание на завтра", "schedule_tomorrow")
        delete_msg_safe(chat_id, mid)
        bot.send_message(
            chat_id,
            f"Расписание на {cur.date()} {w}\n\n{schedule_text}",
            reply_markup=kb,
        )
        return

    if data == "schedule_tomorrow":
        cur = datetime.today() + timedelta(days=1)
        w = weekday_ru(cur)
        if w in ("Сб", "Вс"):
            kb = schedule_keyboard(user.get("save", "choose_kid"), "Расписание на сегодня", "schedule_today")
            delete_msg_safe(chat_id, mid)
            bot.send_message(
                chat_id,
                f"Расписание нa {cur.date()} {w}\n\nВыходной🎊",
                reply_markup=kb,
            )
            return
        conn = db_connect()
        if not conn:
            return
        cursor = conn.cursor()
        schedule = fetch_schedule(cursor, user["kid_group_id"], w)
        schedule_text = format_schedule_rows(schedule) if schedule else " "
        kb = schedule_keyboard(user.get("save", "choose_kid"), "Расписание на сегодня", "schedule_today")
        delete_msg_safe(chat_id, mid)
        bot.send_message(
            chat_id,
            f"Расписание на {cur.date()} {w}\n\n{schedule_text}",
            reply_markup=kb,
        )
        return

    if data == "contacts":
        if not user.get("tutor_db_id"):
            return
        conn = db_connect()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute(
            "select name, surname, patronymic, phone_number from tutor where id = %s",
            (user["tutor_db_id"],),
        )
        group_tutor = cursor.fetchone()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data=user.get("save", "choose_kid")))
        delete_msg_safe(chat_id, mid)
        if group_tutor:
            bot.send_message(
                chat_id,
                "Дементьева Полина Николаевна - директор👸🏼: +79055457103\n"
                f"{group_tutor[1]} {group_tutor[0]} {group_tutor[2]} - воспитатель 👩🏼‍🏫: {group_tutor[3]}",
                reply_markup=kb,
            )
        return

    if data == "choose_kid":
        user["await_phone"] = False
        user["await_tutor_message"] = False
        user["await_pass_date"] = False
        uid = user.get("user_id")
        if uid is None:
            return
        delete_msg_safe(chat_id, mid)
        send_kids_menu(chat_id, uid)
        return


def send_date(message):
    user = get_user(message.chat.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
    if user.get("tutor"):
        bot.send_message(
            user["tutor"],
            f"Сообщение от {user['name']} {user['patronymic']}: {message.text} "
            f"{user['kid_name']} {user['kid_surname']} останется дома 🏠\n\n"
            f"Телефон родителя: {user['phone']}",
        )
    bot.send_message(message.chat.id, "Сообщили воспитателю, будем ждать вас!✨", reply_markup=kb)


def send_mes(message):
    user = get_user(message.chat.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🆗", callback_data=user.get("save", "choose_kid")))
    if user.get("tutor"):
        bot.send_message(
            user["tutor"],
            f"Сообщение от {user['name']} {user['patronymic']}: {message.text}\n\n"
            f"Телефон родителя: {user['phone']}",
        )
    bot.send_message(message.chat.id, "Сообщение отправлено", reply_markup=kb)


def _normalize_phone(value):
    if value is None:
        return ""
    return str(value).strip().replace(" ", "").replace("-", "")


def _digits_only(value):
    return "".join(c for c in str(value) if c.isdigit())


def check_phone_num(message):
    """Не пробрасывать исключения наружу — иначе pyTelegramBotAPI останавливает polling."""
    try:
        user = get_user(message.chat.id)

        if getattr(message, "contact", None) and message.contact.phone_number:
            phone = _normalize_phone(message.contact.phone_number)
        elif getattr(message, "text", None):
            phone = _normalize_phone(message.text)
        else:
            bot.send_message(
                message.chat.id,
                "Отправьте номер кнопкой «Отправить номер телефона» или введите его текстом.",
            )
            return

        if not phone:
            bot.send_message(message.chat.id, "Номер не получен. Попробуйте ещё раз.")
            return

        user["phone"] = phone
        plus = phone if phone.startswith("+") else "+" + phone

        conn = db_connect()
        if not conn:
            bot.send_message(message.chat.id, "Ошибка подключения к базе.")
            return

        cursor = conn.cursor()
        cursor.execute(
            "select name, patronymic, id, phone_number from parent where phone_number = %s or phone_number = %s",
            (phone, plus),
        )
        row = cursor.fetchone()

        if not row:
            want = _digits_only(phone)
            if len(want) < 10:
                bot.send_message(message.chat.id, "Пользователя с таким номером нет")
                return
            cursor.execute("select name, patronymic, id, phone_number from parent")
            for r in cursor.fetchall():
                if r[3] is not None and _digits_only(r[3]) == want:
                    row = (r[0], r[1], r[2], r[3])
                    break

        if not row:
            bot.send_message(message.chat.id, "Пользователя с таким номером нет")
            return

        user["name"] = row[0]
        user["patronymic"] = row[1]
        user["user_id"] = row[2]

        safe_name = html.escape(str(user["name"] or ""))
        safe_pat = html.escape(str(user["patronymic"] or ""))

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🆗", callback_data="choose_kid"))
        bot.send_message(
            message.chat.id,
            f"Добрый день, <b>{safe_name} {safe_pat}</b> 😸!\n\n"
            "Нажав кнопку ниже, вы можете ознакомиться с доступными командами ⬇️",
            parse_mode="html",
            reply_markup=kb,
        )
    except Exception as e:
        logger.exception("check_phone_num: %s", e)
        try:
            bot.send_message(
                message.chat.id,
                "Не удалось обработать номер. Попробуйте ещё раз или обратитесь к администратору.",
            )
        except Exception:
            pass


bot.infinity_polling(skip_pending=True)
