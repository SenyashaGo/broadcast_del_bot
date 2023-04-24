import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

# Укажите токен вашего бота, который вы получили от BotFather
API_TOKEN = 'TOKEN'

# id пользователя, которому доступна функция рассылки
allowed_user_id = your_id

# Создайте объекты бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определение состояний FSM
class SendToGroup(StatesGroup):
    waiting_for_group = State()
    waiting_for_message = State()

@dp.callback_query_handler(lambda c: c.data == 'cancel', state='*')
async def process_callback_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await state.finish()
    await bot.send_message(callback_query.from_user.id, "Рассылка отменена.")



# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот для рассылки сообщений в группы. Напиши /send, чтобы начать рассылку.")

# Обработчик команды /send
@dp.message_handler(commands=['send'])
async def send_message_to_group(message: types.Message):
    markup = InlineKeyboardMarkup()
    cancel_button = InlineKeyboardButton("Отмена", callback_data="cancel")
    markup.row(cancel_button)

    if message.from_user.id != allowed_user_id:
        await message.reply("У вас нет прав на выполнение этой команды.")
        return
    await message.answer("Отправь мне название группы, в которую нужно отправить сообщение.", reply_markup=markup)

    # Установка состояния FSM
    await SendToGroup.waiting_for_group.set()

# Обработчик названия группы
@dp.message_handler(state=SendToGroup.waiting_for_group)
async def process_group_name(message: types.Message, state: FSMContext):
    group_name = message.text
    markup = InlineKeyboardMarkup()
    cancel_button = InlineKeyboardButton("Отмена", callback_data="cancel")
    markup.row(cancel_button)
    # Сохранение названия группы в контексте FSM
    async with state.proxy() as data:
        data['group_name'] = group_name

    await message.answer("Отправь мне сообщение, которое нужно отправить в группу.", reply_markup=markup)

    # Установка состояния FSM
    await SendToGroup.waiting_for_message.set()

# Обработчик сообщения для отправки в группу
@dp.message_handler(state=SendToGroup.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    message_text = message.text

    # Получение названия группы из контекста FSM
    async with state.proxy() as data:
        group_name = data['group_name']

    # Отправка сообщения в группу
    try:
        await bot.send_message(chat_id=group_name, text=message_text, parse_mode=ParseMode.HTML)
        await message.answer(f"Сообщение успешно отправлено в группу {group_name}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

    # Сброс состояния FSM
    await state.finish()

def has_matt(message_text):
    regex_matt = re.compile(
        r'\b(х[уеиыя]\w*|п[иез][дтец]\w*|пизд[аец]|пиздец|бл[яе][дт]\w*|муд[аие]\w*|г[ао]вн\w*|др[ао]ч\w*|ебл[ао]н\w*|з[ао]луп\w*|сос\w*|перд\w*|уеб[ао]н\w*|др[ао]т\w*)\b',
        re.IGNORECASE)
    regex_link = re.compile(r"(http[s]?://[^\s]+)")
    return bool(re.search(regex_matt, message_text)) or bool(re.search(regex_link, message_text))

@dp.message_handler(content_types=types.ContentType.ANY)
async def delete_message(message: types.Message, state: FSMContext):
    if has_matt(message.text):
        try:
            await message.delete()
        except Exception as e:
            logging.exception(e)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
