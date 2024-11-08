import asyncio
import logging
import os
import nest_asyncio
import json
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cozepy import Coze, TokenAuth, Stream, WorkflowEvent, WorkflowEventType

TOKEN = 'pat_tEwF9lJLUedw7qGz7vn2ixEcCC8rMpDdC5joWLOu75q9VMV7TJ89jhLjfPhM40kF'
WORKFLOW_ID = '7433086745733120005'

coze = Coze(auth=TokenAuth(TOKEN))
'''
result = coze.workflows.runs.create(
    # id of workflow
    workflow_id='7433086745733120005',
    # params
    parameters={
        'input_key': 'Я люблю',
    }
)
'''
# Применение nest_asyncio
nest_asyncio.apply()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Настройка SQLAlchemy
engine = create_engine('sqlite:///example.db', echo=True)
Base = declarative_base()
application = ApplicationBuilder().token("6003616188:AAHNSNaSKt_vMm92BQeM38tQEobkeMtZWEk").build()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, nullable=False)
    name = Column(String)
    reminder_date = Column(Date)
    description = Column(String)
    isAdding = Column(Integer, nullable=False)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Функция для добавления пользователя
async def add_user(telegram_id, isAdding, name, reminder_date=None, description=""):
    session = Session()
    try:
        new_user = User(telegram_id = telegram_id, isAdding = isAdding, name=name, reminder_date=reminder_date, description=description)
        session.add(new_user)
        session.commit()
        logger.info(f"Пользователь {name} добавлен.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
    finally:
        session.close()


async def updateDate_user(telegram_id, date):
    session = Session()
    try:
        use = session.query(User).filter(User.telegram_id == telegram_id).filter(User.isAdding == 1).first()
        if use != None:
            use.reminder_date = date
        session.commit()
        logger.info(f"Пользователь обновлён.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {e}")
    finally:
        session.close()


async def updateDescription_user(telegram_id, desc):
    session = Session()
    try:
        use = session.query(User).filter(User.telegram_id == telegram_id).filter(User.isAdding == 1).first()
        if use != None:
            use.description = desc
            use.isAdding = 0
        session.commit()
        logger.info(f"Пользователь обновлён.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {e}")
    finally:
        session.close()


async def show_all(telegram_id):
    session = Session()
    ret = []
    for us in session.query(User).filter(User.telegram_id == telegram_id):
        ret.append([us.id, us.name, datetime.strftime(us.reminder_date, '%d.%m.%Y')])
    session.commit()
    session.close()
    return ret


async def delUser(telegram_id, num):
    session = Session()

    gid = await show_all(telegram_id)
    del_us = session.query(User).filter(User.id == gid[num - 1][0]).first()
    session.delete(del_us)

    session.commit()
    session.close()


async def printUser(telegram_id, num):
    session = Session()

    gid = await show_all(telegram_id)
    print_us = session.query(User).filter(User.id == gid[num - 1][0]).first()
    await createMessage(print_us)

    session.commit()
    session.close()


async def createMessage(user):
    today = datetime.now().date().year
    result = coze.workflows.runs.create(
        # id of workflow
        workflow_id='7433363425587281926',
        # params
        parameters={
            'name': user.name,
            'age': (today - user.reminder_date.year),
            'descr': user.description,
        }
    )
    text = json.loads(json.loads(result.json())["data"])["output"]
    await application.bot.send_message(user.telegram_id, text)


# Функция для проверки напоминаний
async def check_reminders():
    session = Session()
    today = datetime.now().date()
    month_day_today = (today.month, today.day)
    try:
        users_with_reminders = session.query(User).filter(User.reminder_date != None).all()
        for user in users_with_reminders:
            reminder_date = user.reminder_date
            if (reminder_date.month, reminder_date.day) == month_day_today:
                await createMessage(user)
    except Exception as e:
        logger.error(f"Ошибка при проверке напоминаний: {e}")
    finally:
        session.close()

def send_reminder(user):
    # Логика отправки напоминания пользователю
    logger.info(f"Отправлено напоминание пользователю {user.name} (ID: {user.telegram_id})")


#Проверка
async def checkDate(time):
    result = coze.workflows.runs.create(
        # id of workflow
        workflow_id='7433086745733120005',
        # params
        parameters={
            'time': time,
        }
    )
    return json.loads(json.loads(result.json())["data"])["output"]


# Обработчик команды /start
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Добавить", callback_data='add_user'), InlineKeyboardButton("Удалить", callback_data='del_user')],
        [InlineKeyboardButton("Сгенерировать для человека", callback_data='print_congr')],
        [InlineKeyboardButton("Вывести список отслеживаемых", callback_data='show_users')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Что вы хотите сделать?', reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'add_user':
        await query.edit_message_text(text="Пожалуйста, введите имя")
        context.user_data['action'] = 'name'
    elif query.data == "del_user":
        await query.edit_message_text(text="Пожалуйста, введите номер человека")
        context.user_data['action'] = 'del_name'
    elif query.data == "print_congr":
        await query.edit_message_text(text="Пожалуйста, введите номер человека")
        context.user_data['action'] = 'print_congr'
    elif query.data == "show_users":
        try:
            allUs = await show_all(query.from_user.id)
            idx, mess = 0, []
            for id, na, date in allUs:
                idx += 1
                mess.append(f'{idx}. {na} — {date}')
            ret = '\n'.join(map(str, mess))
            await query.edit_message_text(text=ret)
            context.user_data['action'] = 'def'
        except:
            await query.edit_message_text(text="В вашем списке нет пользователей")
    

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    action = context.user_data.get('action')

    if action == 'name':
        try:
            name = update.message.text
            telegram_id = update.message.from_user.id
            await add_user(telegram_id, 1, name)
            await update.message.reply_text(f'Введите дату, когда родился человек')
            context.user_data['action'] = 'data'
        except:
            await update.message.reply_text(f'Ведите корректные данные')
            context.user_data['action'] = 'name'
    elif action == 'data':
        try:
            retData = await checkDate(update.message.text)
            data = datetime.strptime(retData, '%d.%m.%Y').date()
            telegram_id = update.message.from_user.id
            await updateDate_user(telegram_id, data)
            await update.message.reply_text(f'Опишите будущего именинника')
            context.user_data['action'] = 'description'
        except:
            await update.message.reply_text(f'Ведите корректные данные')
            context.user_data['action'] = 'data'
    elif action == 'description':
        try:
            desc = update.message.text
            telegram_id = update.message.from_user.id
            await updateDescription_user(telegram_id, desc)
            await update.message.reply_text(f'Человек добавлен')
        except:
            await update.message.reply_text(f'Ведите корректные данные')
            context.user_data['action'] = 'description'
    elif action == 'del_name':
        try:
            num = int(update.message.text)
            telegram_id = update.message.from_user.id
            await delUser(telegram_id, num)
            await update.message.reply_text(f'Человек удалён')
        except ValueError:
            await update.message.reply_text(f'Пожалуйста, введите корректный ID')
    elif action == "print_congr":
        try:
            num = int(update.message.text)
            telegram_id = update.message.from_user.id
            await printUser(telegram_id, num)
        except ValueError:
            await update.message.reply_text(f'Пожалуйста, введите корректный ID')

# Основная функция для запуска бота
async def main():
    # Замените 'YOUR_TOKEN' на токен вашего бота
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Настройка APScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, 'cron', hour=21, minute=39)  # Запускаем check_reminders каждый день в 9:00
    scheduler.start()

    try:
        await application.run_polling()
    finally:
        scheduler.shutdown()  # Завершение работы планировщика
        logger.info("Бот остановлен.")

# Запуск основного цикла
if __name__ == '__main__':
    # Запуск в фоновом режиме
    asyncio.run(main())
