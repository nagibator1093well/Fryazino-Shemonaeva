#@Krpppp_bot
import logging
from telegram.ext import Application, MessageHandler, filters
from telegram.ext import CommandHandler
import sqlite3 as sl
import requests
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import os
from telegram import InputFile
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler
import random
from datetime import date
from telegram.ext import JobQueue
from datetime import time
import pytz

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


# Подключение к базе данных
con1 = sl.connect('d1.db')
cur1 = con1.cursor()
cur1.execute('''CREATE TABLE IF NOT EXISTS tl1 
              (id INTEGER PRIMARY KEY, 
               id_pol INT, 
               USD INT, 
               BTC INT, 
               ETH INT, 
               USDT INT, 
               daily INT)''')
reg_polz = []  # Список ID зарегистрированных пользователей

# Функции для работы с криптовалютами
def get_crypto_data(coin_id='bitcoin', vs_currency='usd', days=10):
    """Получает исторические данные о курсе криптовалюты"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': vs_currency, 'days': days}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
        prices.set_index('date', inplace=True)
        prices.drop('timestamp', axis=1, inplace=True)
        
        return prices
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении данных: {e}")
        return None

def plot_and_save_crypto_chart(data, coin_name='Bitcoin', currency='USD'):
    """Строит и сохраняет график криптовалюты, возвращает путь к файлу"""
    if data is None or data.empty:
        logger.error("Нет данных для построения графика")
        return None
    
    plt.figure(figsize=(12, 6))
    plt.plot(data.index, data['price'], color='#2ca02c', linewidth=2, marker='o', markersize=4)
    
    plt.title(f'Курс {coin_name} за последние {len(data)} дней', fontsize=16, pad=20)
    plt.xlabel('Дата', fontsize=12)
    plt.ylabel(f'Цена ({currency})', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    if not os.path.exists('crypto_charts'):
        os.makedirs('crypto_charts')
    
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"crypto_charts/{coin_name.lower()}_{currency.lower()}_{timestamp}.png"
    
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filename

def get_top_cryptos(limit=5):
    """Получает список топовых криптовалют"""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении списка криптовалют: {e}")
        return None

def valuta():
    """Обновляет данные и графики для всех криптовалют"""
    top_cryptos = get_top_cryptos(3)
    if not top_cryptos:
        return None
    
    for crypto in top_cryptos:
        coin_id = crypto['id']
        coin_name = crypto['name']
        data = get_crypto_data(coin_id=coin_id, days=10)
        if data is not None:
            plot_and_save_crypto_chart(data, coin_name=coin_name)
            
        if top_cryptos:
            #Получаем данные для топовых криптовалют
            for crypto in top_cryptos:
                coin_id = crypto['id']
                coin_name = crypto['name']
                symbol = crypto['symbol'].upper()
                print(f"\nОбрабатываем {coin_name} ({symbol})...")
                # Получаем данные за последние 10 дней
                data = get_crypto_data(coin_id=coin_id, days=10)
                    
                # Строим и сохраняем график
                if data is not None:
                    plot_and_save_crypto_chart(data, coin_name=coin_name)
                         

# Обработчики команд Telegram
async def start(update, context):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Проверяем существование пользователя в базе
    cur1.execute("SELECT id_pol FROM tl1 WHERE id_pol = ?", (user_id,))
    existing_user = cur1.fetchone()
    
    if not existing_user:
        # Генерируем новый ID (максимальный существующий + 1)
        cur1.execute("SELECT MAX(id) FROM tl1")
        max_id = cur1.fetchone()[0] or 0  # Если таблица пустая, начинаем с 1
        new_id = max_id + 1
        
        # Добавляем пользователя в базу
        cur1.execute(
            "INSERT INTO tl1 (id, id_pol, USD, BTC, ETH, USDT, daily) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id, user_id, 100000, 0, 0, 0, 0)
        )
        con1.commit()
        logger.info(f"Добавлен новый пользователь: ID {user_id}")
    
    await update.message.reply_html(
        f"Привет {user.mention_html()}! Я крипто-бот.\n"
        "Со мной ты можешь следить за актуальными ценами криптовалют, а так же покупать и продавать их (конечно же, понарошку)\n"
        "Вот часть доступных команд:\n"
        "/rate_crypto - курс криптовалют\n"
        "/profile - ваш профиль\n"
        "/daily - ежедневная награда (раз в день)\n"
        "/grafBTC - график и покупка/продажа Bitcoin\n"
        "/grafETH - график и покупка/продажа Ethereum\n"
        "/grafUSDT - график и покупка/продажа Tether\n"
        "Остальные компнды можно узнать, нажав /help\n"
        "Удачи!"
    )

async def help_command(update, context):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "/rate_crypto - информация об актуальном курсе криптовалют\n"
        "/profile - актуальная информация о пользователе\n"
        "/daily - ежедневная награда (раз в день, от 10000 USD до 100000 USD)\n"
        "/top - топ-5 пользователей бота с наибольшим капиталом\n"
        "/tap - мгновенная награда (от 1 до 10 USD, можно использовать многократно)\n"
        "/grafBTC - график Bitcoin\n"
        "/grafETH - график Ethereum\n"
        "/grafUSDT - график Tether\n"
        "после просмотра графика можно купить и продать выбранную валюту"
    )

async def profile(update, context):
    """Обработчик команды /profile"""
    user = update.effective_user
    user_id = user.id
    
    cur1.execute("SELECT USD, BTC, ETH, USDT FROM tl1 WHERE id_pol = ?", (user_id,))
    result = cur1.fetchone()
    
    if result:
        usd, btc, eth, usdt = result
        prof_text = f"""Ваш профиль:
👤 Ник: {user.mention_html()}
💵 Доллары: {usd} USD
₿ Bitcoin: {btc}
Ξ Ethereum: {eth}
₮ Tether: {usdt}"""
    else:
        prof_text = "Профиль не найден. Пожалуйста, начните с команды /start"
    
    await update.message.reply_html(prof_text)

async def rate_crypto(update, context):
    """Обработчик команды /rate_crypto"""
    spis_val = []
    spis_izm = []    
    top_cryptos = get_top_cryptos(3)
    
    if top_cryptos:
        for crypto in top_cryptos:
            coin_id = crypto['id']
            data = get_crypto_data(coin_id=coin_id, days=1)
            
            if data is not None and not data.empty:
                last_price = data['price'].iloc[-1]
                first_price = data['price'].iloc[0]
                change_percent = ((last_price - first_price) / first_price) * 100
                spis_val.append(f"{last_price:.2f}")
                spis_izm.append(f"{change_percent:+.2f}%")
    
    if len(spis_val) >= 3 and len(spis_izm) >= 3:
        ratecrp_text = (
            f"📊 Текущие курсы криптовалют:\n\n"
            f"₿ Bitcoin: {spis_val[0]} USD ({spis_izm[0]})\n"
            f"Ξ Ethereum: {spis_val[1]} USD ({spis_izm[1]})\n"
            f"₮ Tether: {spis_val[2]} USD ({spis_izm[2]})\n\n"
            f"Для просмотра графиков:\n"
            f"Bitcoin: /grafBTC\n"
            f"Ethereum: /grafETH\n"
            f"Tether: /grafUSDT"
        )
    else:
        ratecrp_text = "Не удалось получить данные о курсах криптовалют. Попробуйте позже."
    
    await update.message.reply_text(ratecrp_text)

async def grafBTC(update, context):
    """Обработчик команды /grafBTC"""
    valuta()  # Обновляем данные
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"crypto_charts/bitcoin_usd_{timestamp}.png"
    
    if os.path.exists(filename):
        with open(filename, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption="📈 График курса Bitcoin (BTC) за последние 240 дней, чтобы продать: /sellBTC , чтобы купить: /buyBTC"
            )
    else:
        await update.message.reply_text("График BTC не найден. Попробуйте позже.")

async def grafETH(update, context):
    """Обработчик команды /grafETH"""
    valuta()  # Обновляем данные
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"crypto_charts/ethereum_usd_{timestamp}.png"
    
    if os.path.exists(filename):
        with open(filename, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption="📈 График курса Ethereum (ETH) за последние 240 дней, чтобы продать: /sellETH , чтобы купить: /buyETH"
            )
    else:
        await update.message.reply_text("График ETH не найден. Попробуйте позже.")

async def grafUSDT(update, context):
    """Обработчик команды /grafUSDT"""
    valuta()  # Обновляем данные
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"crypto_charts/tether_usd_{timestamp}.png"
    
    if os.path.exists(filename):
        with open(filename, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption="📈 График курса Tether (USDT) за последние 241 дней, чтобы продать: /sellUSDT, чтобы купить: /buyUSDT"
            )
    else:
        await update.message.reply_text("График USDT не найден. Попробуйте позже.")

async def get_crypto_price(coin_id):
    """Получает текущую цену криптовалюты"""
    data = get_crypto_data(coin_id=coin_id, days=1)
    if data is None or data.empty:   #в случае ошибки подключения не выводит ошибку, а берутся усредненные цены валют за последнее время
        if coin_id == 'BTC' or coin_id == 'btc' or coin_id == 'Bitcoin' or coin_id == 'bitcoin':
            return 103960
        elif coin_id == 'ETH' or coin_id == 'eth' or coin_id == 'Ethereum' or coin_id == 'ethereum':
            return 2508
        elif coin_id == 'USDT' or coin_id == 'usdt' or coin_id == 'Tether' or coin_id == 'tether':
            return 1        
    return data['price'].iloc[-1]

async def show_trade_options(update, context, coin_type, action):
    """Показывает варианты торговли с точными ценами"""
    user_id = update.effective_user.id
    coin_name = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'USDT': 'Tether'}[coin_type]
    
    # Проверяем регистрацию пользователя
    cur1.execute(f"SELECT {coin_type}, USD FROM tl1 WHERE id_pol = ?", (user_id,))
    result = cur1.fetchone()
    
    if not result:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /start")
        return
    
    coin_balance, usd_balance = result
    
    # Получаем текущий курс
    current_price = await get_crypto_price(coin_type.lower())
    if current_price is None:
        await update.message.reply_text(f"Не удалось получить текущий курс {coin_name}. Попробуйте позже.")
        return
    
    # Рассчитываем цены для каждого количества
    amounts = [1, 10, 100]
    prices = {amount: amount * current_price for amount in amounts}
    
    # Создаем клавиатуру с вариантами и ценами
    keyboard = [
        [
            InlineKeyboardButton(f"1 {coin_type} - {prices[1]:.2f} USD", 
                                callback_data=f"{action}_{coin_type}_1"),
            InlineKeyboardButton(f"10 {coin_type} - {prices[10]:.2f} USD", 
                                callback_data=f"{action}_{coin_type}_10")
        ],
        [
            InlineKeyboardButton(f"100 {coin_type} - {prices[100]:.2f} USD", 
                                callback_data=f"{action}_{coin_type}_100")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if action == 'buy':
        message = (
            f"💰 <b>Покупка {coin_name}</b>\n\n"
            f"📊 Текущий курс: 1 {coin_type} = {current_price:.2f} USD\n"
            f"💼 Ваш баланс: {usd_balance:.2f} USD\n\n"
            "Выберите количество для покупки:"
        )
    else:  # sell
        if coin_balance <= 0:
            await update.message.reply_text(f"❌ У вас нет {coin_name} для продажи")
            return
        
        message = (
            f"💰 <b>Продажа {coin_name}</b>\n\n"
            f"📊 Текущий курс: 1 {coin_type} = {current_price:.2f} USD\n"
            f"💼 Ваш баланс: {coin_balance:.8f} {coin_type}\n\n"
            "Выберите количество для продажи:"
        )
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def process_trade_callback(update, context):
    """Обрабатывает нажатие кнопок торговли"""
    query = update.callback_query
    await query.answer()
    
    action, coin_type, amount_str = query.data.split('_')
    amount = float(amount_str)
    user_id = query.from_user.id
    coin_name = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'USDT': 'Tether'}[coin_type]
    
    # Получаем текущий курс
    current_price = await get_crypto_price(coin_type.lower())
    if current_price is None:
        await query.edit_message_text("❌ Не удалось получить текущий курс. Попробуйте позже.")
        return
    
    total = amount * current_price
    
    if action == 'buy':
        # Проверяем баланс USD
        cur1.execute("SELECT USD FROM tl1 WHERE id_pol = ?", (user_id,))
        usd_balance = cur1.fetchone()[0]
        
        if usd_balance < total:
            await query.edit_message_text(
                f"❌ Недостаточно средств!\n\n"
                f"Нужно: {total:.2f} USD\n"
                f"У вас: {usd_balance:.2f} USD",
                parse_mode='HTML'
            )
            return
        
        # Обновляем баланс
        cur1.execute(
            f"UPDATE tl1 SET USD = USD - ?, {coin_type} = {coin_type} + ? WHERE id_pol = ?",
            (total, amount, user_id)
        )
        con1.commit()
        
        # Получаем обновленные балансы
        cur1.execute(f"SELECT USD, {coin_type} FROM tl1 WHERE id_pol = ?", (user_id,))
        new_usd, new_coin = cur1.fetchone()
        
        await query.edit_message_text(
            f"✅ <b>Успешная покупка!</b>\n\n"
            f"Вы купили {amount:.8f} {coin_type} за {total:.2f} USD\n"
            f"По курсу: 1 {coin_type} = {current_price:.2f} USD\n\n"
            f"💼 <b>Новый баланс:</b>\n"
            f"USD: {new_usd:.2f}\n"
            f"{coin_type}: {new_coin:.8f}",
            parse_mode='HTML'
        )
    else:  # sell
        # Проверяем баланс криптовалюты
        cur1.execute(f"SELECT {coin_type} FROM tl1 WHERE id_pol = ?", (user_id,))
        coin_balance = cur1.fetchone()[0]
        
        if coin_balance < amount:
            await query.edit_message_text(
                f"❌ Недостаточно {coin_type}!\n\n"
                f"Пытаетесь продать: {amount:.8f}\n"
                f"У вас: {coin_balance:.8f}",
                parse_mode='HTML'
            )
            return
        
        # Обновляем баланс
        cur1.execute(
            f"UPDATE tl1 SET USD = USD + ?, {coin_type} = {coin_type} - ? WHERE id_pol = ?",
            (total, amount, user_id)
        )
        con1.commit()
        
        # Получаем обновленные балансы
        cur1.execute(f"SELECT USD, {coin_type} FROM tl1 WHERE id_pol = ?", (user_id,))
        new_usd, new_coin = cur1.fetchone()
        
        await query.edit_message_text(
            f"✅ <b>Успешная продажа!</b>\n\n"
            f"Вы продали {amount:.8f} {coin_type} за {total:.2f} USD\n"
            f"По курсу: 1 {coin_type} = {current_price:.2f} USD\n\n"
            f"💼 <b>Новый баланс:</b>\n"
            f"USD: {new_usd:.2f}\n"
            f"{coin_type}: {new_coin:.8f}",
            parse_mode='HTML')
        
# Функции для BTC
async def buyBTC(update, context):
    await show_trade_options(update, context, 'BTC', 'buy')

async def sellBTC(update, context):
    await show_trade_options(update, context, 'BTC', 'sell')

# Функции для ETH
async def buyETH(update, context):
    await show_trade_options(update, context, 'ETH', 'buy')

async def sellETH(update, context):
    await show_trade_options(update, context, 'ETH', 'sell')

# Функции для USDT
async def buyUSDT(update, context):
    await show_trade_options(update, context, 'USDT', 'buy')

async def sellUSDT(update, context):
    await show_trade_options(update, context, 'USDT', 'sell')

async def daily(update, context):
    #Выдает ежедневную награду пользователю. 1 раз в календарный день, выдается рандомное число USD в размере от 10000 до 100000 единиц
    user = update.effective_user
    user_id = user.id
    
    # Проверяем регистрацию пользователя
    cur1.execute("SELECT id_pol, daily FROM tl1 WHERE id_pol = ?", (user_id,))
    result = cur1.fetchone()
    
    if not result:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /start")
        return
    
    last_daily_date = result[1] if result[1] else None
    today = date.today().isoformat()
    
    if last_daily_date == today:
        await update.message.reply_text("Вы уже получали ежедневную награду сегодня. Приходите завтра!")
        return
    
    # Генерируем случайную сумму от 10000 до 100000
    reward = random.randint(10000, 100000)
    
    # Обновляем баланс и дату последней награды
    cur1.execute(
        "UPDATE tl1 SET USD = USD + ?, daily = ? WHERE id_pol = ?",
        (reward, today, user_id)
    )
    con1.commit()
    
    await update.message.reply_text(
        f"🎉 Поздравляем! Вы получили ежедневную награду: {reward} USD!\n"
        f"Ваш новый баланс можно проверить командой /profile"
    )
    
async def top(update, context):
    """Обработчик команды /top - выводит топ-5 пользователей по капиталу"""
    # Получаем данные всех пользователей
    cur1.execute("SELECT id_pol, USD, BTC, ETH, USDT FROM tl1")
    users = cur1.fetchall()
    
    if not users:
        await update.message.reply_text("Нет данных о пользователях")
        return
    
    # Рассчитываем капитал для каждого пользователя
    user_capitals = []
    for user_id, usd, btc, eth, usdt in users:
        # Получаем текущие курсы криптовалют
        btc_price = await get_crypto_price('bitcoin')
        eth_price = await get_crypto_price('ethereum')
        usdt_price = await get_crypto_price('tether')
        
        # Рассчитываем общий капитал
        total = usd + (btc * btc_price) + (eth * eth_price) + (usdt * usdt_price)
        
        # Получаем имя пользователя
        try:
            user = await context.bot.get_chat(user_id)
            username = user.username or user.first_name or f"Пользователь {user_id}"
        except:
            username = f"Пользователь {user_id}"
        
        user_capitals.append((username, total))
    
    # Сортируем по капиталу (по убыванию)
    user_capitals.sort(key=lambda x: x[1], reverse=True)
    
    # Формируем сообщение с топ-5
    top_message = "🏆 Топ-5 пользователей по капиталу:\n\n"
    for i, (username, capital) in enumerate(user_capitals[:5], 1):
        top_message += f"{i}. {username}: {capital:.2f} USD\n"
    
    await update.message.reply_text(top_message)

async def tap(update, context):
    """Обработчик команды /tap - дает случайную сумму от 1 до 10 USD"""
    user = update.effective_user
    user_id = user.id
    
    # Проверяем регистрацию пользователя
    cur1.execute("SELECT id_pol FROM tl1 WHERE id_pol = ?", (user_id,))
    result = cur1.fetchone()
    
    if not result:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /start")
        return
    
    # Генерируем случайную сумму от 1 до 10 USD
    reward = random.randint(1, 10)
    
    # Обновляем баланс
    cur1.execute(
        "UPDATE tl1 SET USD = USD + ? WHERE id_pol = ?",
        (reward, user_id)
    )
    con1.commit()
    
    # Получаем новый баланс
    cur1.execute("SELECT USD FROM tl1 WHERE id_pol = ?", (user_id,))
    new_balance = cur1.fetchone()[0]
    
    await update.message.reply_text(
        f"💸 Вы получили {reward} USD!\n"
        f"💼 Ваш новый баланс: {new_balance} USD\n\n"
        f"Можете использовать /tap снова для получения новой награды!"
    )

async def send_daily_notification(context):
    """Функция для рассылки уведомлений о ежедневной награде"""
    try:
        # Получаем список всех пользователей
        cur1.execute("SELECT id_pol FROM tl1")
        users = cur1.fetchall()
        
        if not users:
            logger.info("Нет пользователей для рассылки")
            return
        
        # Отправляем сообщение каждому пользователю
        for user in users:
            user_id = user[0]
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🌞 Доброе утро! Не забудьте получить свою ежедневную награду командой /daily"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        
        logger.info(f"Успешно отправлены уведомления {len(users)} пользователям")
    except Exception as e:
        logger.error(f"Ошибка в send_daily_notification: {e}")

def main():
    try:
        """Основная функция запуска бота"""
        application = Application.builder().token("8089456213:AAE_3m8vGHEgaULjvaWQRbBgCJMDUsK7LmE").build()
    
        # Настраиваем ежедневную рассылку в 8:00
        job_queue = application.job_queue
        
        # Устанавливаем время рассылки (8:00 по Москве)
        moscow_time = time(8, 0, tzinfo=pytz.timezone('Europe/Moscow'))
        job_queue.run_daily(send_daily_notification, time=moscow_time)
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("profile", profile))
        application.add_handler(CommandHandler("rate_crypto", rate_crypto))
        application.add_handler(CommandHandler("grafBTC", grafBTC))
        application.add_handler(CommandHandler("grafETH", grafETH))
        application.add_handler(CommandHandler("grafUSDT", grafUSDT))
        application.add_handler(CommandHandler("daily", daily))
        application.add_handler(CommandHandler("top", top))
        application.add_handler(CommandHandler("tap", tap))
    
        # Обработчики для торговли
        application.add_handler(CommandHandler("buyBTC", buyBTC))
        application.add_handler(CommandHandler("sellBTC", sellBTC))
        application.add_handler(CommandHandler("buyETH", buyETH))
        application.add_handler(CommandHandler("sellETH", sellETH))
        application.add_handler(CommandHandler("buyUSDT", buyUSDT))
        application.add_handler(CommandHandler("sellUSDT", sellUSDT))
        
        # Обработчик callback-кнопок
        application.add_handler(CallbackQueryHandler(process_trade_callback))
    
        # Запускаем бота
        application.run_polling()
        
    finally:
        con1.close()
        
if __name__ == '__main__':
    main()