# veniki_bot.py
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ===== настройки логирования =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== Личные данные (заменять только при необходимости) ========
TOKEN = "7996197814:AAHkD3uQsNc0IJjoxatEuoAJkEK05QR_L6w"
ADMIN_ID = 507208748  # числовой Telegram ID администратора
# ===================================

# ======== Инициализация бота, диспетчера и хранилища состояний ========
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ======== Структура товаров ========
VENIKS = {
    "lip": {"label": "🌿 Липовые", "price": 5},
    "dub": {"label": "🌳 Дубовые", "price": 6},
    "bir": {"label": "🍃 Березовые", "price": 5},
}

# ======== Состояния FSM ========
class OrderStates(StatesGroup):
    choosing_venik = State()
    choosing_quantity = State()
    choosing_delivery = State()
    confirming = State()

# ======== Главное меню (reply keyboard) ========
menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
menu_kb.add(KeyboardButton("📞 Контакты 🌿"))
menu_kb.add(KeyboardButton("🚚 Доставка и оплата 🍃"))
menu_kb.add(KeyboardButton("🛒 Сделать заказ 🌳"))

# ======== Вспомогательные генераторы inline-кнопок ========
def venik_inline_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    for key, v in VENIKS.items():
        kb.insert(InlineKeyboardButton(text=f"{v['label']} — {v['price']}р", callback_data=f"venik:{key}"))
    kb.add(InlineKeyboardButton(text="⬅ В главное меню", callback_data="cancel"))
    return kb

def quantity_inline_kb():
    # Быстрые варианты + кнопка "Другое" (позволяет ввести вручную, но мы будем минимизировать падения)
    kb = InlineKeyboardMarkup(row_width=4)
    for q in (1, 2, 5, 10):
        kb.insert(InlineKeyboardButton(text=str(q), callback_data=f"qty:{q}"))
    kb.add(InlineKeyboardButton(text="Другое количество", callback_data="qty:other"))
    kb.add(InlineKeyboardButton(text="⬅ Выбрать веник", callback_data="back_to_venik"))
    return kb

def delivery_inline_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(text="Самовывоз 🌿", callback_data="delivery:self"))
    kb.add(InlineKeyboardButton(text="Почта 📦", callback_data="delivery:mail"))
    kb.add(InlineKeyboardButton(text="⬅ Изменить количество", callback_data="back_to_qty"))
    return kb

def confirm_inline_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm:yes"))
    kb.add(InlineKeyboardButton(text="✏ Изменить заказ", callback_data="confirm:edit"))
    kb.add(InlineKeyboardButton(text="⬅ В главное меню", callback_data="cancel"))
    return kb

# ======== Хэндлеры: старт и меню ========
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    try:
        await message.answer("Привет! 🌿 Добро пожаловать. Выберите действие:", reply_markup=menu_kb)
    except Exception as e:
        logger.exception("Ошибка при /start: %s", e)

@dp.message_handler(lambda m: m.text == "📞 Контакты 🌿")
async def show_contacts(message: types.Message):
    try:
        await message.answer(
            "📞 Контакты:\n"
            "+375257388194\n"
            "+375333241573\n\n"
            "⏰ Часы работы: 8:00 — 20:00"
        )
    except Exception as e:
        logger.exception("Ошибка в show_contacts: %s", e)

@dp.message_handler(lambda m: m.text == "🚚 Доставка и оплата 🍃")
async def show_delivery_info(message: types.Message):
    try:
        await message.answer(
            "🚚 Доставка и оплата:\n"
            "• Самовывоз — г. Поставы (8:00–20:00)\n"
            "• Доставка почтой — уточняется при заказе\n\n"
            "Оплата — по факту"
        )
    except Exception as e:
        logger.exception("Ошибка в show_delivery_info: %s", e)

# ======== Начало процесса заказа ========
@dp.message_handler(lambda m: m.text == "🛒 Сделать заказ 🌳")
async def start_order(message: types.Message):
    try:
        # показываем меню веников
        await message.answer("🌿 Шаг 1/3 — Выберите тип веника:", reply_markup=venik_inline_kb())
        await OrderStates.choosing_venik.set()
    except Exception as e:
        logger.exception("Ошибка в start_order: %s", e)

# ======== Выбор веника (inline) ========
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("venik:"), state=OrderStates.choosing_venik)
async def on_venik_selected(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, key = callback.data.split(":")
        if key not in VENIKS:
            await callback.answer("Неверный выбор.", show_alert=True)
            return
        # сохраняем выбор
        await state.update_data(venik_key=key)
        venik_label = VENIKS[key]["label"]
        price = VENIKS[key]["price"]
        await bot.send_message(callback.from_user.id, f"🌿 Вы выбрали: {venik_label} — {price}р\n\nШаг 2/3 — выберите количество:", reply_markup=quantity_inline_kb())
        await OrderStates.choosing_quantity.set()
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка on_venik_selected: %s", e)
        await callback.answer("Ошибка, повторите, пожалуйста.", show_alert=True)

# кнопка назад / отмена
@dp.callback_query_handler(lambda c: c.data == "cancel", state="*")
async def on_cancel(callback: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        await bot.send_message(callback.from_user.id, "Отменено. Возврат в главное меню.", reply_markup=menu_kb)
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка on_cancel: %s", e)

# ======== Выбор количества (inline) ========
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("qty:"), state=OrderStates.choosing_quantity)
async def on_qty_selected(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, qty = callback.data.split(":")
        if qty == "other":
            # Разрешаем ввести вручную — переводим в состояние, принимающее число через текст,
            # но обрабатываем вежливо и безопасно (минимизируем падения).
            await bot.send_message(callback.from_user.id,
                                   "Введите нужное количество числом (например: 12). Если хотите отменить — нажмите '⬅ В главное меню' в интерфейсе.",
                                   reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅ В главное меню", callback_data="cancel")))
            # сохраняем, что ожидаем произвольное число
            await state.update_data(expect_custom_qty=True)
            await callback.answer()
            return

        # быстрая опция
        try:
            qty_int = int(qty)
            if qty_int <= 0:
                raise ValueError
        except ValueError:
            await callback.answer("Неверное количество.", show_alert=True)
            return

        await state.update_data(quantity=qty_int)
        data = await state.get_data()
        venik_key = data.get("venik_key")
        if not venik_key:
            await callback.answer("Сначала выберите веник.", show_alert=True)
            await state.finish()
            return

        venik_label = VENIKS[venik_key]["label"]
        price = VENIKS[venik_key]["price"]
        total = price * qty_int

        await bot.send_message(callback.from_user.id,
                               f"🌿 Вы: {venik_label}\nКоличество: {qty_int}\nЦена за шт.: {price}р\nИтого: {total}р\n\nШаг 3/3 — выберите способ доставки:",
                               reply_markup=delivery_inline_kb())
        await OrderStates.choosing_delivery.set()
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка on_qty_selected: %s", e)
        await callback.answer("Ошибка сервера, повторите позже.", show_alert=True)

# ======== Обработка ввода произвольного количества (текст) ========
@dp.message_handler(lambda m: m.text.isdigit(), state="*")
async def handle_custom_quantity_text(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        if not data.get("expect_custom_qty"):
            # это не ожидаемое число — просто игнорируем (попросим использовать кнопки)
            return
        qty_int = int(message.text)
        if qty_int <= 0:
            await message.answer("Количество должно быть положительным числом.")
            return
        await state.update_data(quantity=qty_int)
        await state.update_data(expect_custom_qty=False)

        venik_key = data.get("venik_key")
        if not venik_key:
            await message.answer("Сначала выберите веник через 'Сделать заказ'.")
            await state.finish()
            return

        venik_label = VENIKS[venik_key]["label"]
        price = VENIKS[venik_key]["price"]
        total = price * qty_int

        await message.answer(
            f"🌿 Вы: {venik_label}\nКоличество: {qty_int}\nЦена за шт.: {price}р\nИтого: {total}р\n\nШаг 3/3 — выберите способ доставки:",
            reply_markup=delivery_inline_kb()
        )
        await OrderStates.choosing_delivery.set()
    except Exception as e:
        logger.exception("Ошибка handle_custom_quantity_text: %s", e)
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")

# Кнопка "назад к выбору веников"
@dp.callback_query_handler(lambda c: c.data == "back_to_venik", state=OrderStates.choosing_quantity)
async def back_to_venik(callback: types.CallbackQuery, state: FSMContext):
    try:
        await state.update_data(expect_custom_qty=False)
        await bot.send_message(callback.from_user.id, "Вернитесь к выбору веников:", reply_markup=venik_inline_kb())
        await OrderStates.choosing_venik.set()
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка back_to_venik: %s", e)

# ======== Выбор доставки ========
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("delivery:"), state=OrderStates.choosing_delivery)
async def on_delivery_selected(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, method = callback.data.split(":")
        if method not in ("self", "mail"):
            await callback.answer("Неверный выбор.", show_alert=True)
            return

        await state.update_data(delivery=method)
        data = await state.get_data()
        venik_key = data.get("venik_key")
        qty = data.get("quantity")
        price = VENIKS[venik_key]["price"] if venik_key else 0
        venik_label = VENIKS[venik_key]["label"] if venik_key else "—"
        total = price * (qty or 0)
        delivery_text = "Самовывоз 🌿" if method == "self" else "Почта 📦"

        await bot.send_message(
            callback.from_user.id,
            f"Подтвердите заказ:\n\n{venik_label}\nКоличество: {qty}\nДоставка: {delivery_text}\nИтого: {total}р",
            reply_markup=confirm_inline_kb()
        )
        await OrderStates.confirming.set()
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка on_delivery_selected: %s", e)
        await callback.answer("Ошибка сервера, повторите позже.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "back_to_qty", state=OrderStates.choosing_delivery)
async def back_to_qty(callback: types.CallbackQuery, state: FSMContext):
    try:
        await bot.send_message(callback.from_user.id, "Выберите количество:", reply_markup=quantity_inline_kb())
        await OrderStates.choosing_quantity.set()
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка back_to_qty: %s", e)

# ======== Подтверждение заказа ========
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("confirm:"), state=OrderStates.confirming)
async def on_confirm(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, action = callback.data.split(":")
        if action == "edit":
            # возвращаемся к выбору веников
            await bot.send_message(callback.from_user.id, "Редактирование заказа — выберите веник:", reply_markup=venik_inline_kb())
            await OrderStates.choosing_venik.set()
            await callback.answer()
            return
        if action != "yes":
            await callback.answer()
            return

        # собираем данные заказа
        data = await state.get_data()
        venik_key = data.get("venik_key")
        qty = data.get("quantity")
        delivery = data.get("delivery")
        venik_label = VENIKS[venik_key]["label"] if venik_key else "—"
        price = VENIKS[venik_key]["price"] if venik_key else 0
        total = price * (qty or 0)
        delivery_text = "Самовывоз 🌿" if delivery == "self" else "Почта 📦"

        # подтверждение пользователю
        try:
            await bot.send_message(callback.from_user.id,
                                   f"✅ Заказ принят!\n\n{venik_label}\nКоличество: {qty}\nДоставка: {delivery_text}\nИтого: {total}р\n\nМы свяжемся с вами для подтверждения.")
        except Exception as e:
            logger.exception("Не удалось отправить подтверждение пользователю: %s", e)

        # уведомление админу (защищено)
        order_text = (
            f"🌿 Новый заказ\n"
            f"Пользователь: @{callback.from_user.username or '—'} ({callback.from_user.id})\n"
            f"{venik_label} — {qty} шт.\n"
            f"Доставка: {delivery_text}\n"
            f"Итого: {total}р"
        )
        try:
            await bot.send_message(ADMIN_ID, order_text)
        except Exception as e:
            logger.exception("Не удалось уведомить администратора: %s", e)

        await state.finish()
        await callback.answer()
    except Exception as e:
        logger.exception("Ошибка on_confirm: %s", e)
        await callback.answer("Ошибка сервера, попробуйте позже.", show_alert=True)

# ======== Защита: любые неожиданные callback_data ========
@dp.callback_query_handler(lambda c: True)
async def unknown_callback(callback: types.CallbackQuery):
    try:
        await callback.answer("Эта кнопка больше не активна. Вернитесь в меню.", show_alert=False)
    except Exception:
        pass

# ======== Не-онлайн текстовые сообщения (просим использовать кнопки) ========
@dp.message_handler()
async def fallback_text(message: types.Message):
    try:
        await message.answer("Пожалуйста, используйте кнопки меню и inline-кнопки для оформления заказа 🌿", reply_markup=menu_kb)
    except Exception as e:
        logger.exception("Ошибка fallback_text: %s", e)

# ======== Запуск polling ========
if __name__ == "__main__":
    print("Бот запускается... 🌿")
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logger.exception("Ошибка при старте polling: %s", e)
