import html
import os
from datetime import datetime, timedelta

import telebot
from telebot import types
from dotenv import load_dotenv

from connect import Connect_base

load_dotenv()

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

user_data = {}


# USER STATE
def get_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {}
    return user_data[chat_id]


def set_flags(user, phone=False, tutor_msg=False, pass_date=False):
    user["await_phone"] = phone
    user["await_tutor_message"] = tutor_msg
    user["await_pass_date"] = pass_date


# DB
def db_connect():
    return Connect_base().connect_base()


# SAFE HELPERS
def safe_delete(chat_id, mid):
    try:
        bot.delete_message(chat_id, mid)
    except:
        pass


def safe_tutor_send(user, text):
    if user.get("tutor"):
        try:
            bot.send_message(user["tutor"], text)
        except:
            pass


def ok_keyboard(callback):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🆗", callback_data=callback))
    return kb


def back_kb(callback):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Назад", callback_data=callback))
    return kb


def schedule_kb(back_cb, other_label, other_cb):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("Назад", callback_data=back_cb),
        types.InlineKeyboardButton(other_label, callback_data=other_cb),
    )
    return kb


# FORMATTERS
def format_schedule(rows):
    return "\n".join([f"{str(s)[:5]} - {str(e)[:5]} {c}" for s, e, c in rows])


def format_group(rows):
    res = []
    for surname, name, patronymic, gender in rows:
        emoji = "👧🏼" if gender == "женский" else "🧒🏼"
        res.append(f"{surname} {name} {patronymic} {emoji}")
    return "\n".join(res)


# WEEKDAY
ENG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
RUS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
WEEKDAY = dict(zip(ENG, RUS))


def weekday_ru(dt):
    return WEEKDAY.get(dt.strftime("%A"))


# KIDS MENU
def send_kids(chat_id, parent_id):
    conn = db_connect()
    if not conn:
        bot.send_message(chat_id, "Ошибка подключения к базе.")
        return

    cur = conn.cursor()
    cur.execute("""
        select name, gender, id, surname
        from kid
        inner join kid_has_parent on kid.id = kid_has_parent.kid_id
        where parent_id = %s
    """, (parent_id,))

    kids = cur.fetchall()

    kb = types.InlineKeyboardMarkup()
    for name, gender, kid_id, _ in kids:
        emoji = "👧🏼" if gender == "женский" else "🧒🏼"
        kb.add(types.InlineKeyboardButton(name + emoji, callback_data=f"kid:{kid_id}"))

    bot.send_message(chat_id, "Выберите ребенка, для которого будут выполнены команды:", reply_markup=kb)



# START
@bot.message_handler(commands=["start"])
def start(message):
    u = get_user(message.chat.id)
    set_flags(u)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Авторизация", callback_data="to_authoriz"))

    bot.send_message(
        message.chat.id,
        "Добрый день, Родитель!🔅\n\n"
        "Я - <b>Daycarebot</b>. Я умею сообщать о новостях сада. "
        "Делаю быстрым и удобным ваше общение с воспитателем и отвечаю на различные запросы.\n\n"
        " Для общения со мной вам нужно <b>авторизоваться</b> 📝",
        parse_mode="html",
        reply_markup=kb,
    )


# CALLBACKS
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    user = get_user(call.message.chat.id)
    data = call.data
    mid = call.message.message_id
    chat_id = call.message.chat.id

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    # ---------------- AUTH ----------------
    if data == "to_authoriz":
        set_flags(user, phone=True)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("Отправить номер телефона 📞", request_contact=True))

        bot.send_message(
            chat_id,
            "Для авторизации нужен ваш <b>номер телефона</b>, нажмите кнопку ниже, чтобы отправить его",
            parse_mode="html",
            reply_markup=kb,
        )
        return

    # ---------------- KID ----------------
    if data.startswith("kid:"):
        kid_id = data.split(":")[1]
        user["kid_id"] = kid_id
        user["save"] = data

        conn = db_connect()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            select kid.name, surname, patronymic, gender,
                   date_of_birth, age, `group`.name, `group`.id, `group`.tutor_id
            from kid
            inner join `group` on kid.group_idgroup = `group`.id
            where kid.id = %s
        """, (kid_id,))

        row = cur.fetchone()
        if not row:
            return

        user["kid_name"] = row[0]
        user["kid_surname"] = row[1]
        user["kid_group"] = row[6]
        user["kid_group_id"] = row[7]
        user["kid_gender"] = row[3]
        user["tutor_db_id"] = row[8]

        cur.execute("select chat_id from tutor where id = %s", (row[8],))
        t = cur.fetchone()
        user["tutor"] = t[0] if t else None

        emoji = "👧🏼" if user["kid_gender"] == "женский" else "🧒🏼"

        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("Стоим у двери 🔔", callback_data="door"),
            types.InlineKeyboardButton("Одеть ребенка 👕", callback_data="dress"),
        )
        kb.add(types.InlineKeyboardButton("Сообщение воспитателю ✉️", callback_data="message"))
        kb.add(types.InlineKeyboardButton("Сообщить о пропуске ❗️", callback_data="pass"))
        kb.row(
            types.InlineKeyboardButton("Группа ребенка 👨‍👩‍👦‍👦", callback_data="group"),
            types.InlineKeyboardButton("Расписание ребенка ⏰", callback_data="schedule_today"),
        )
        kb.add(types.InlineKeyboardButton("Контакты 📱", callback_data="contacts"))
        kb.add(types.InlineKeyboardButton("Назад", callback_data="choose_kid"))

        safe_delete(chat_id, mid)

        bot.send_message(
            chat_id,
            f"{user['kid_name']} {user['kid_surname']} {emoji}\n\n"
            "Воспользуйтесь кнопками внизу, чтобы сообщить или запросить информацию ⬇️",
            reply_markup=kb,
        )
        return

    # ---------------- DOOR ----------------
    if data == "door":
        safe_delete(chat_id, mid)
        bot.send_message(chat_id, "Уже открываем!", reply_markup=ok_keyboard(user.get("save", "choose_kid")))
        safe_tutor_send(user,
            f"Сообщение от {user.get('name','')} {user.get('patronymic','')}: "
            f"{user.get('kid_name','')} {user.get('kid_surname','')} уже у дверей, встречайте!🙌🏼\n\n"
            f"Телефон родителя: {user.get('phone','')}"
        )
        return

    # ---------------- DRESS ----------------
    if data == "dress":
        safe_delete(chat_id, mid)
        bot.send_message(chat_id, "Начинаем одевать ребенка!", reply_markup=ok_keyboard(user.get("save", "choose_kid")))
        safe_tutor_send(user,
            f"Сообщение от {user.get('name','')} {user.get('patronymic','')}: "
            f"просьба одеть {user.get('kid_name','')} {user.get('kid_surname','')} 👕\n\n"
            f"Телефон родителя: {user.get('phone','')}"
        )
        return

    # ---------------- MESSAGE ----------------
    if data == "message":
        set_flags(user, tutor_msg=True)
        safe_delete(chat_id, mid)
        bot.send_message(chat_id, "Напишите сообщение, которое хотите передать воспитателю ⬇️",
                         reply_markup=back_kb(user.get("save", "choose_kid")))
        return

    # ---------------- PASS ----------------
    if data == "pass":
        safe_delete(chat_id, mid)
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("Сегодня не придем", callback_data="pass_today"),
            types.InlineKeyboardButton("Завтра не придем", callback_data="pass_tomorrow"),
        )
        kb.add(types.InlineKeyboardButton("Указать другую дату пропуска 📅", callback_data="pass_date"))
        kb.add(types.InlineKeyboardButton("Назад", callback_data=user.get("save", "choose_kid")))
        bot.send_message(chat_id, "Выберите дату пропуска или укажите свою ⬇️", reply_markup=kb)
        return

    # ---------------- PASS TODAY ----------------
    if data == "pass_today":
        safe_delete(chat_id, mid)
        safe_tutor_send(user,
            f"Сообщение от {user.get('name','')} {user.get('patronymic','')}: "
            f"сегодня {user.get('kid_name','')} {user.get('kid_surname','')} остается дома 🏠\n\n"
            f"Телефон родителя: {user.get('phone','')}"
        )
        bot.send_message(chat_id, "Сообщили воспитателю, ждем вас завтра!✨",
                         reply_markup=ok_keyboard(user.get("save", "choose_kid")))
        return

    # ---------------- PASS TOMORROW ----------------
    if data == "pass_tomorrow":
        safe_delete(chat_id, mid)
        safe_tutor_send(user,
            f"Сообщение от {user.get('name','')} {user.get('patronymic','')}: "
            f"завтра {user.get('kid_name','')} {user.get('kid_surname','')} останется дома 🏠\n\n"
            f"Телефон родителя: {user.get('phone','')}"
        )
        bot.send_message(chat_id, "Сообщили воспитателю, будем ждать вас!✨",
                         reply_markup=ok_keyboard(user.get("save", "choose_kid")))
        return

    # ---------------- PASS DATE ----------------
    if data == "pass_date":
        set_flags(user, pass_date=True)
        safe_delete(chat_id, mid)
        bot.send_message(chat_id, "Укажите дату пропуска:\n\n📌 Дату укажите в виде числа и месяца",
                         reply_markup=back_kb(user.get("save", "choose_kid")))
        return

    # ---------------- GROUP ----------------
    if data == "group":
        conn = db_connect()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            select surname, name, patronymic, gender
            from kid
            where group_idgroup = %s
        """, (user["kid_group_id"],))

        text = format_group(cur.fetchall())

        safe_delete(chat_id, mid)

        bot.send_message(
            chat_id,
            f"Группа {user['kid_group']}:\n\n{text}",
            reply_markup=ok_keyboard(user.get("save", "choose_kid"))
        )
        return

    # ---------------- SCHEDULE ----------------
    if data in ("schedule_today", "schedule_tomorrow"):
        cur_date = datetime.today() if data == "schedule_today" else datetime.today() + timedelta(days=1)
        w = weekday_ru(cur_date)

        if w in ("Сб", "Вс"):
            bot.send_message(chat_id, f"Расписание нa {cur_date.date()} {w}\n\nВыходной🎊",
                             reply_markup=schedule_kb(user.get("save", "choose_kid"),
                             "Расписание на завтра" if data == "schedule_today" else "Расписание на сегодня",
                             "schedule_tomorrow" if data == "schedule_today" else "schedule_today"))
            return

        conn = db_connect()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            select start_time, end_time, class.name
            from kidgarten.schedule
            join kidgarten.class on schedule.class_id = class.id
            where group_id = %s
        """, (user["kid_group_id"],))

        bot.send_message(chat_id, f"Расписание на {cur_date.date()} {w}\n\n{format_schedule(cur.fetchall())}",
                         reply_markup=schedule_kb(user.get("save", "choose_kid"),
                         "Расписание на завтра" if data == "schedule_today" else "Расписание на сегодня",
                         "schedule_tomorrow" if data == "schedule_today" else "schedule_today"))
        return

    # ---------------- CONTACTS ----------------
    if data == "contacts":
        conn = db_connect()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            select name, surname, patronymic, phone_number
            from tutor
            where id = %s
        """, (user.get("tutor_db_id"),))

        t = cur.fetchone()

        safe_delete(chat_id, mid)

        bot.send_message(
            chat_id,
            "Дементьева Полина Николаевна - директор👸🏼: +79055457103\n"
            f"{t[1]} {t[0]} {t[2]} - воспитатель 👩🏼‍🏫: {t[3]}",
            reply_markup=ok_keyboard(user.get("save", "choose_kid"))
        )
        return

    # ---------------- CHOOSE KID ----------------
    if data == "choose_kid":
        set_flags(user)
        uid = user.get("user_id")
        if uid:
            send_kids(chat_id, uid)


# TEXT HANDLERS
@bot.message_handler(content_types=["contact", "text"])
def text_router(message):
    u = get_user(message.chat.id)

    if u.get("await_phone"):
        u["await_phone"] = False
        check_phone_num(message)

    elif u.get("await_tutor_message"):
        u["await_tutor_message"] = False
        send_mes(message)

    elif u.get("await_pass_date"):
        u["await_pass_date"] = False
        send_date(message)


# BUSINESS LOGIC
def send_date(message):
    user = get_user(message.chat.id)
    safe_tutor_send(user,
        f"Сообщение от {user.get('name','')} {user.get('patronymic','')}: {message.text} "
        f"{user.get('kid_name','')} {user.get('kid_surname','')} останется дома 🏠\n\n"
        f"Телефон родителя: {user.get('phone','')}"
    )
    bot.send_message(message.chat.id, "Сообщили воспитателю, будем ждать вас!✨",
                     reply_markup=ok_keyboard(user.get("save", "choose_kid")))


def send_mes(message):
    user = get_user(message.chat.id)
    safe_tutor_send(user,
        f"Сообщение от {user.get('name','')} {user.get('patronymic','')}: {message.text}\n\n"
        f"Телефон родителя: {user.get('phone','')}"
    )
    bot.send_message(message.chat.id, "Сообщение отправлено",
                     reply_markup=ok_keyboard(user.get("save", "choose_kid")))


# PHONE CHECK
def check_phone_num(message):
    user = get_user(message.chat.id)

    phone = None
    if message.content_type == "contact":
        phone = message.contact.phone_number
    else:
        phone = message.text

    if not phone:
        return

    user["phone"] = phone

    conn = db_connect()
    if not conn:
        return

    cur = conn.cursor()
    cur.execute("""
        select name, patronymic, id
        from parent
        where phone_number = %s
    """, (phone,))

    row = cur.fetchone()
    if not row:
        bot.send_message(message.chat.id, "Пользователя с таким номером нет")
        return

    user["name"] = row[0]
    user["patronymic"] = row[1]
    user["user_id"] = row[2]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🆗", callback_data="choose_kid"))

    bot.send_message(
        message.chat.id,
        f"Добрый день, <b>{html.escape(row[0])} {html.escape(row[1])}</b> 😸!\n\n"
        "Нажав кнопку ниже, вы можете ознакомиться с доступными командами ⬇️",
        parse_mode="html",
        reply_markup=kb,
    )


# START BOT
bot.infinity_polling(skip_pending=True)