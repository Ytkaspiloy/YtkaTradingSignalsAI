что делает этот код? import os
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import telebot
from telebot import types
from datetime import datetime, timedelta
import talib
import time
import threading
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mdates
import logging
from dotenv import load_dotenv
import pytz
import queue
import signal
import sys
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import concurrent.futures

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Настройка сессии с повторными попытками
def create_telegram_session():
    session = requests.Session()

    # Настройка повторных попыток
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        backoff_factor=1
    )

    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# Настройки бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# Исправление SSL ошибок
bot = telebot.TeleBot(TOKEN, threaded=False)
bot.session = create_telegram_session()

# ID вашего Telegram-канала
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
# ID администратора для команды скип
ADMIN_ID = os.getenv('ADMIN_TELEGRAM_ID')
if not ADMIN_ID:
    logger.error("ADMIN_TELEGRAM_ID not found in .env file!")
    ADMIN_ID = "0"

# Настройки MT5
MT5_LOGIN = int(os.getenv('MT5_LOGIN'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD')
MT5_SERVER = "PoTrade-MT5"
MAX_RETRIES = 3
RECONNECT_DELAY = 5

# ОБНОВЛЕННЫЙ СПИСОК ИНСТРУМЕНТОВ С ВАШИХ СКРИНШОТОВ
OTC_INSTRUMENTS = [
    # === ВАЛЮТНЫЕ ПАРЫ ===
    "AUDCAD_OTC", "AUDCHF_OTC", "AUDJPY_OTC", "AUDNZD_OTC", "AUDUSD_OTC",
    "CADCHF_OTC", "CADJPY_OTC", "CHFJPY_OTC", "CHFNOK_OTC",
    "EURCHF_OTC", "EURGBP_OTC", "EURHUF_OTC", "EURJPY_OTC",
    "EURNZD_OTC", "EURTRY_OTC", "EURUSD_OTC",
    "GBPAUD_OTC", "GBPJPY_OTC", "GBPUSD_OTC",
    "NZDJPY_OTC", "NZDUSD_OTC",
    "USDCAD_OTC", "USDCHF_OTC", "USDJPY_OTC",

    # === ЭКЗОТИЧЕСКИЕ ВАЛЮТЫ ===
    "USDARS_OTC", "USDBDT_OTC", "USDBRL_OTC", "USDCLP_OTC",
    "USDCNH_OTC", "USDCOP_OTC", "USDDZD_OTC", "USDEGP_OTC",
    "USDIDR_OTC", "USDINR_OTC", "USDMXN_OTC", "USDMYR_OTC",
    "USDPHP_OTC", "USDPKR_OTC", "USDSGD_OTC",
    "USDTHB_OTC", "USDVND_OTC", "YERUSD_OTC", "ZARUSD_OTC",
    "UAHUSD_OTC", "LBPUSD_OTC", "NGNUSD_OTC",
    "TNDUSD_OTC", "KESUSD_OTC", "MADUSD_OTC",

    # === ВАЛЮТЫ С CNY ===
    "AEDCNY_OTC", "BHDCNY_OTC", "JODCNY_OTC", "OMRCNY_OTC",
    "QARCNY_OTC", "SARCNY_OTC",

    # === КРИПТОВАЛЮТЫ ===
    "Bitcoin_OTC", "Ethereum_OTC", "Litecoin_OTC", "Cardano_OTC",
    "Polkadot_OTC", "Chainlink_OTC", "Dogecoin_OTC", "BNB_OTC",
    "Solana_OTC", "Polygon_OTC", "Avalanche_OTC", "Toncoin_OTC",
    "TRON_OTC", "Bitcoin_ETF_OTC",

    # === АКЦИИ ===
    "Johnson&Johnson_OTC", "Apple_OTC", "American_Express_OTC",
    "Boeing_Company_OTC", "Cisco_OTC", "FACEBOOK_INC_OTC",
    "Intel_OTC", "McDonalds_OTC", "Microsoft_OTC", "Pfizer_Inc_OTC",
    "Tesla_OTC", "ExxonMobil_OTC", "Advanced_Micro_Devices_OTC",
    "Amazon_OTC", "Alibaba_OTC", "Citigroup_Inc_OTC",
    "Coinbase_Global_OTC", "Palantir_Technologies_OTC",
    "FedEx_OTC", "GameStop_Corp_OTC",
    "Marathon_Digital_Holdings_OTC", "Netflix_OTC", "VISA_OTC",

    # === ИНДЕКСЫ ===
    "100GBP_OTC", "AUS_200_OTC", "D30EUR_OTC", "DJI30_OTC",
    "E35EUR_OTC", "E50EUR_OTC", "F40EUR_OTC", "JPN225_OTC",
    "US100_OTC", "SP500_OTC",

    # === СЫРЬЕ И МЕТАЛЛЫ ===
    "Gold_OTC", "Silver_OTC", "Natural_Gas_OTC",
    "Palladium_spot_OTC", "Platinum_spot_OTC", "Brent_Oil_OTC",
    "WTI_Crude_Oil_OTC",

    # === ВОЛАТИЛЬНОСТЬ ===
    "VIX_OTC"
]

# КАТЕГОРИИ ИНСТРУМЕНТОВ ДЛЯ ФИЛЬТРАЦИИ
INSTRUMENT_CATEGORIES = {
    "OTC": [inst for inst in OTC_INSTRUMENTS if
            any(x in inst for x in ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]) and "CNY" not in inst],
    "Экзотические": [inst for inst in OTC_INSTRUMENTS if any(x in inst for x in
                                                             ["ARS", "BDT", "BRL", "CLP", "COP", "DZD", "EGP", "IDR",
                                                              "INR", "MXN", "MYR", "PHP", "PKR", "RUB", "SGD", "THB",
                                                              "VND", "YER", "ZAR", "UAH", "IRR", "LBP", "NGN", "SYP",
                                                              "TND", "KES", "MAD"])],
    "CNY пары": [inst for inst in OTC_INSTRUMENTS if "CNY" in inst],
    "Криптовалюты": [inst for inst in OTC_INSTRUMENTS if any(x in inst.lower() for x in
                                                             ["bitcoin", "ethereum", "litecoin", "cardano", "polkadot",
                                                              "chainlink", "dogecoin", "bnb", "solana", "polygon",
                                                              "avalanche", "toncoin", "tron"])],
    "Акции": [inst for inst in OTC_INSTRUMENTS if any(x in inst.lower() for x in
                                                      ["apple", "microsoft", "amazon", "tesla", "facebook", "netflix",
                                                       "johnson", "boeing", "cisco", "intel", "mcdonalds", "pfizer",
                                                       "exxon", "amd", "alibaba", "citigroup", "coinbase", "palantir",
                                                       "fedex", "gamestop", "marathon", "visa"])],
    "Индексы": [inst for inst in OTC_INSTRUMENTS if any(x in inst for x in ["100", "200", "30", "35", "40", "50", "225",
                                                                            "500"]) or "US100" in inst or "SP500" in inst or "JPN225" in inst],
    "Сырье": [inst for inst in OTC_INSTRUMENTS if any(
        x in inst.lower() for x in ["gold", "silver", "gas", "oil", "palladium", "platinum", "brent", "wti"])],
    "Волатильность": [inst for inst in OTC_INSTRUMENTS if "VIX" in inst]
}

# ОБНОВЛЕННЫЕ ТАЙМФРЕЙМЫ С БОЛЬШИМ КОЛИЧЕСТВОМ СВЕЧЕЙ
TIMEFRAMES = {
    "1M": {"tf": mt5.TIMEFRAME_M1, "wait_seconds": 60, "candle_count": 200, "width": 0.0004},
    "2M": {"tf": mt5.TIMEFRAME_M2, "wait_seconds": 120, "candle_count": 150, "width": 0.0008},
    "3M": {"tf": mt5.TIMEFRAME_M3, "wait_seconds": 180, "candle_count": 120, "width": 0.0012}
}

# Глобальные переменные для новой логики
current_signal = None
signal_start_time = None
signal_attempt = 0
signal_history = []
shutdown_event = threading.Event()
chart_queue = queue.Queue()
signal_active_event = threading.Event()
analysis_in_progress = threading.Event()
skip_signal_event = threading.Event()  # Событие для пропуска сигнала

# Настройки графиков
rcParams['font.family'] = 'Arial'
plt.style.use('seaborn-v0_8')


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Received shutdown signal")
    shutdown_event.set()
    sys.exit(0)


# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def format_mono(text):
    return f"<code>{text}</code>"


def send_admin_alert(message):
    if ADMIN_ID and ADMIN_ID != "0":
        try:
            bot.send_message(ADMIN_ID, f"⚠ Ошибка бота: {message}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления администратору: {e}")


def is_admin_user(user):
    """Проверяет пользователя на права администратора"""
    if not user or not user.id:
        return False
    return str(user.id) == ADMIN_ID


def initialize_mt5():
    for attempt in range(MAX_RETRIES):
        try:
            if not mt5.initialize():
                logger.error(f"MT5 init error (attempt {attempt + 1}): {mt5.last_error()}")
                time.sleep(RECONNECT_DELAY)
                continue

            authorized = mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
            if not authorized:
                logger.error(f"Auth error (attempt {attempt + 1}): {mt5.last_error()}")
                mt5.shutdown()
                time.sleep(RECONNECT_DELAY)
                continue

            # Добавляем все инструменты в терминал
            success_count = 0
            for pair in OTC_INSTRUMENTS:
                if mt5.symbol_select(pair, True):
                    success_count += 1
                else:
                    logger.warning(f"Не удалось добавить инструмент {pair}")

            logger.info(
                f"Connected to PoTrade-MT5 successfully. Added {success_count}/{len(OTC_INSTRUMENTS)} instruments")
            return True
        except Exception as e:
            logger.error(f"Connection error (attempt {attempt + 1}): {str(e)}")
            time.sleep(RECONNECT_DELAY)
    return False


def check_mt5_connection():
    if not mt5.initialize():
        logger.warning("Инициализация MT5 не удалась, пробуем переподключиться")
        return initialize_mt5()

    if not mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER):
        logger.warning("Ошибка авторизации, пробуем переподключиться")
        mt5.shutdown()
        return initialize_mt5()

    return True


def get_exact_rates_from_mt5(pair, timeframe, count=200):
    """Получение ТОЧНЫХ данных как в терминале MT5 с учетом последней свечи"""
    for attempt in range(MAX_RETRIES):
        try:
            if not check_mt5_connection():
                logger.error(f"Нет подключения к MT5 (попытка {attempt + 1})")
                time.sleep(RECONNECT_DELAY)
                continue

            symbol_info = mt5.symbol_info(pair)
            if symbol_info is None:
                logger.error(f"Инструмент {pair} не найден в терминале")
                return None

            if not symbol_info.visible:
                logger.warning(f"Инструмент {pair} не видим, пробуем добавить")
                if not mt5.symbol_select(pair, True):
                    logger.error(f"Не удалось добавить инструмент {pair}")
                    return None

            # Получаем точные данные как в терминале с учетом последней свечи
            rates = mt5.copy_rates_from_pos(pair, timeframe, 0, count)
            if rates is None:
                error = mt5.last_error()
                logger.error(f"Ошибка данных для {pair} (попытка {attempt + 1}): {error}")
                mt5.shutdown()
                time.sleep(RECONNECT_DELAY)
                if not initialize_mt5():
                    continue
                time.sleep(1)
                continue

            # Преобразуем в DataFrame без изменений
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            logger.info(f"Получено {len(df)} свечей для {pair}, последняя свеча: {df.index[-1]}")
            return df

        except Exception as e:
            logger.error(f"Ошибка получения данных (попытка {attempt + 1}): {str(e)}")
            time.sleep(RECONNECT_DELAY)

    logger.error(f"Не удалось получить данных для {pair} после {MAX_RETRIES} попыток")
    return None


def detect_order_blocks(df):
    """Обнаружение ордер-блоков с учетом последней свечи"""
    blocks = []

    # Анализируем все свечи включая последнюю
    for i in range(2, len(df)):
        # Бычий ордер-блок (две зеленые свечи + красная)
        if i >= 2 and i < len(df):
            if df['close'].iloc[i - 2] > df['open'].iloc[i - 2] and \
                    df['close'].iloc[i - 1] > df['open'].iloc[i - 1] and \
                    df['close'].iloc[i] < df['open'].iloc[i]:
                # Используем ВСЕ хвосты свечи (high и low) для создания блока
                high_price = df['high'].iloc[i]  # Верхняя тень
                low_price = df['low'].iloc[i]  # Нижняя тень

                blocks.append({
                    'type': 'bullish',
                    'time': df.index[i],
                    'index': i,
                    'high': high_price,
                    'low': low_price,
                    'original_high': high_price,
                    'original_low': low_price
                })

        # Медвежий ордер-блок (две красные свечи + зеленая)
        if i >= 2 and i < len(df):
            if df['close'].iloc[i - 2] < df['open'].iloc[i - 2] and \
                    df['close'].iloc[i - 1] < df['open'].iloc[i - 1] and \
                    df['close'].iloc[i] > df['open'].iloc[i]:
                high_price = df['high'].iloc[i]  # Верхняя тень
                low_price = df['low'].iloc[i]  # Нижняя тень

                blocks.append({
                    'type': 'bearish',
                    'time': df.index[i],
                    'index': i,
                    'high': high_price,
                    'low': low_price,
                    'original_high': high_price,
                    'original_low': low_price
                })

    return blocks[-6:]  # Возвращаем последние 6 блоков


def analyze_block_strength(df, block, block_index):
    """Анализ силы ордер-блока с учетом всех свечей"""
    lookback = min(30, block_index)
    lookforward = min(30, len(df) - block_index - 1)

    # Анализируем поведение цены вокруг блока
    touches = 0
    breakouts = 0

    # Проверяем касания до блока
    for i in range(block_index - lookback, block_index):
        if (df['low'].iloc[i] <= block['high'] and df['high'].iloc[i] >= block['low']):
            touches += 1

    # Проверяем пробития после блока (включая последнюю свечу)
    for i in range(block_index + 1, min(block_index + lookforward + 1, len(df))):
        if block['type'] == 'bullish':
            if df['low'].iloc[i] < block['low']:  # Пробитие вниз
                breakouts += 1
        else:  # bearish
            if df['high'].iloc[i] > block['high']:  # Пробитие вверх
                breakouts += 1

    # Определяем силу блока
    if touches == 0 and breakouts == 0:
        return "tested_once"  # Белый/серый
    elif breakouts >= 2:
        return "volatile"  # Фиолетовый
    elif block['type'] == 'bullish' and breakouts == 0:
        return "strong_support"  # Красный
    elif block['type'] == 'bearish' and breakouts == 0:
        return "strong_resistance"  # Зеленый
    else:
        return "tested_once"


def detect_support_resistance(df):
    """Обнаружение уровней поддержки и сопротивления"""
    levels = []
    max_window = 25  # Увеличили окно для более значимых уровней

    # Поиск сопротивления (максимумы)
    for i in range(max_window, len(df) - max_window):
        window = df['high'].iloc[i - max_window:i + max_window]
        if df['high'].iloc[i] == window.max():
            levels.append({
                'type': 'resistance',
                'time': df.index[i],
                'value': df['high'].iloc[i],
                'strength': len(window)  # Сила уровня
            })

    # Поиск поддержки (минимумы)
    for i in range(max_window, len(df) - max_window):
        window = df['low'].iloc[i - max_window:i + max_window]
        if df['low'].iloc[i] == window.min():
            levels.append({
                'type': 'support',
                'time': df.index[i],
                'value': df['low'].iloc[i],
                'strength': len(window)  # Сила уровня
            })

    # Фильтрация близких уровней
    filtered_levels = []
    tolerance = 0.0015  # Уменьшили tolerance для более точных уровней

    for level in levels:
        if not filtered_levels:
            filtered_levels.append(level)
        else:
            similar = False
            for existing in filtered_levels:
                if abs(level['value'] - existing['value']) / existing['value'] < tolerance:
                    similar = True
                    # Обновляем на более сильный уровень
                    if level['strength'] > existing['strength']:
                        existing['value'] = level['value']
                        existing['time'] = level['time']
                        existing['strength'] = level['strength']
                    break
            if not similar:
                filtered_levels.append(level)

    # Сортируем по силе и берем самые сильные
    filtered_levels.sort(key=lambda x: x['strength'], reverse=True)
    return filtered_levels[:10]  # Возвращаем до 10 самых сильных уровней


def calculate_fibonacci_levels(df):
    """Расчет уровней Фибоначчи для последнего значимого движения"""
    if len(df) < 50:
        return []

    # Берем более широкий диапазон для значимого движения
    lookback = min(100, len(df))
    high_price = df['high'].tail(lookback).max()
    low_price = df['low'].tail(lookback).min()

    # Проверяем, что движение достаточно значительное
    if (high_price - low_price) / low_price < 0.001:  # Минимальное движение 0.1%
        return []

    fib_levels = []
    fib_ratios = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618]

    for ratio in fib_ratios:
        level = low_price + (high_price - low_price) * ratio
        fib_levels.append({
            'ratio': ratio,
            'value': level
        })

    return fib_levels


def detect_diagonal_levels(df):
    """Обнаружение диагональных уровней (трендовые линии)"""
    diagonal_levels = []

    if len(df) < 40:
        return diagonal_levels

    # Поиск значимых максимумов для нисходящего тренда
    highs = df['high'].values
    times = np.arange(len(highs))

    # Находим локальные максимумы
    for i in range(15, len(highs) - 15):
        if highs[i] == max(highs[i - 15:i + 15]):
            diagonal_levels.append({
                'type': 'resistance_diagonal',
                'index': i,
                'value': highs[i],
                'time': df.index[i]
            })

    # Находим локальные минимумы для восходящего тренда
    lows = df['low'].values
    for i in range(15, len(lows) - 15):
        if lows[i] == min(lows[i - 15:i + 15]):
            diagonal_levels.append({
                'type': 'support_diagonal',
                'index': i,
                'value': lows[i],
                'time': df.index[i]
            })

    return diagonal_levels[-8:]  # Последние 8 точек


def generate_signal(df):
    try:
        df['SMA_10'] = talib.SMA(df['close'], 10)
        df['SMA_20'] = talib.SMA(df['close'], 20)
        df['SMA_50'] = talib.SMA(df['close'], 50)
        df['RSI'] = talib.RSI(df['close'], 14)
        df['MACD'], df['Signal'], _ = talib.MACD(df['close'], 12, 26, 9)
        df['Stoch_K'], df['Stoch_D'] = talib.STOCH(df['high'], df['low'], df['close'], 14, 3, 0, 3, 0)
        df['EMA_21'] = talib.EMA(df['close'], 21)
        df['EMA_50'] = talib.EMA(df['close'], 50)
        df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(df['close'], 20, 2)

        last = df.iloc[-1]

        buy_conditions = [
            last['SMA_10'] > last['SMA_20'],
            last['EMA_21'] > last['SMA_20'],
            last['MACD'] > last['Signal'],
            last['RSI'] > 45 and last['RSI'] < 75,
            last['Stoch_K'] > last['Stoch_D'],
            last['close'] > last['SMA_10'],
            last['close'] > last['EMA_21']
        ]

        sell_conditions = [
            last['SMA_10'] < last['SMA_20'],
            last['EMA_21'] < last['SMA_20'],
            last['MACD'] < last['Signal'],
            last['RSI'] < 55 and last['RSI'] > 25,
            last['Stoch_K'] < last['Stoch_D'],
            last['close'] < last['SMA_10'],
            last['close'] < last['EMA_21']
        ]

        buy_score = sum(buy_conditions)
        sell_score = sum(sell_conditions)

        if buy_score >= 5:
            return "ПОКУПАТЬ 🟢", "green", 1
        elif sell_score >= 5:
            return "ПРОДАВАТЬ 🔴", "red", -1
        elif buy_score >= 4:
            return "ПОКУПАТЬ 🟡", "yellow", 0.5
        elif sell_score >= 4:
            return "ПРОДАВАТЬ 🟠", "orange", -0.5
        else:
            return "НЕТ ЧЕТКОГО СИГНАЛА ⚪", "gray", 0
    except Exception as e:
        logger.error(f"Error generating signal: {str(e)}")
        return "ОШИБКА АНАЛИЗА", "gray", 0


def calculate_success_probability(df, signal_type):
    """Расчет вероятности успеха сделки в процентах"""
    try:
        if len(df) < 50:
            return 65

        probability = 70
        last = df.iloc[-1]

        if 'SMA_10' in df and 'SMA_20' in df:
            sma_diff = abs((last['SMA_10'] - last['SMA_20']) / last['SMA_20'] * 100)
            if sma_diff > 0.1:
                probability += 10
            elif sma_diff < 0.02:
                probability -= 5

        if 'RSI' in df:
            if 30 < last['RSI'] < 70:
                probability += 5
            elif last['RSI'] > 80 or last['RSI'] < 20:
                probability -= 10

        if 'MACD' in df and 'Signal' in df:
            macd_strength = abs(last['MACD'] - last['Signal'])
            if macd_strength > 0.001:
                probability += 8

        high_low_range = (df['high'].tail(20) - df['low'].tail(20)).mean()
        avg_range = high_low_range / df['close'].iloc[-1] * 100
        if avg_range < 0.1:
            probability += 5
        elif avg_range > 0.5:
            probability -= 5

        indicator_agreement = 0
        if signal_type > 0:
            buy_conditions = [
                last['SMA_10'] > last['SMA_20'] if 'SMA_10' in df else False,
                last['MACD'] > last['Signal'] if 'MACD' in df else False,
                last['RSI'] > 50 if 'RSI' in df else False,
                last['close'] > last['SMA_20'] if 'SMA_20' in df else False
            ]
            indicator_agreement = sum(buy_conditions) * 3
        else:
            sell_conditions = [
                last['SMA_10'] < last['SMA_20'] if 'SMA_10' in df else False,
                last['MACD'] < last['Signal'] if 'MACD' in df else False,
                last['RSI'] < 50 if 'RSI' in df else False,
                last['close'] < last['SMA_20'] if 'SMA_20' in df else False
            ]
            indicator_agreement = sum(sell_conditions) * 3

        probability += indicator_agreement

        data_quality = min(100, len(df) / 200 * 10)
        probability += data_quality * 0.1

        probability = max(55, min(95, probability))

        return int(probability)

    except Exception as e:
        logger.error(f"Error calculating success probability: {e}")
        return 70


def get_probability_emoji(probability):
    if probability >= 85:
        return "🎯"
    elif probability >= 75:
        return "🔥"
    elif probability >= 65:
        return "⚡"
    else:
        return "📊"


def create_exact_candlestick_chart(pair, timeframe_name, df, entry_price=None, signal_type=None, signal_direction=None):
    """Создание ТОЧНОГО графика как в терминале MT5 с улучшенным анализом и ордер-блоками вправо"""
    chart_path = None
    try:
        plt.close('all')

        # Используем точные данные без изменений
        blocks = detect_order_blocks(df)
        levels = detect_support_resistance(df)
        fib_levels = calculate_fibonacci_levels(df)
        diagonal_levels = detect_diagonal_levels(df)

        # Подготовка данных для candlestick_ohlc
        df_ohlc = df[['open', 'high', 'low', 'close']].copy()
        df_ohlc.reset_index(inplace=True)
        df_ohlc['time'] = df_ohlc['time'].map(mdates.date2num)

        fig, ax = plt.subplots(figsize=(18, 12))  # Увеличили размер для лучшего отображения

        # ИСПРАВЛЕНИЕ: используем правильное имя переменной - candle_width вместо callet_width
        candle_width = TIMEFRAMES[timeframe_name]["width"]

        # Создаем точные свечи как в MT5
        candlestick_ohlc(ax, df_ohlc.values, width=candle_width, colorup='#2E8B57', colordown='#DC143C', alpha=1.0)

        # ДОБАВЛЯЕМ ЦЕНЫ НА МАКСИМУМАХ И МИНИМУМАХ
        # Отмечаем важные максимумы и минимумы
        for i in range(len(df)):
            if i % 8 == 0 or i == len(df) - 1:  # Каждую 8-ю свечу и последнюю
                # Максимум
                ax.annotate(f"{df['high'].iloc[i]:.5f}",
                            xy=(mdates.date2num(df.index[i]), df['high'].iloc[i]),
                            xytext=(0, 5), textcoords='offset points',
                            fontsize=6, color='red', ha='center',
                            bbox=dict(boxstyle="round,pad=0.2", facecolor='yellow', alpha=0.7))
                # Минимум
                ax.annotate(f"{df['low'].iloc[i]:.5f}",
                            xy=(mdates.date2num(df.index[i]), df['low'].iloc[i]),
                            xytext=(0, -15), textcoords='offset points',
                            fontsize=6, color='blue', ha='center',
                            bbox=dict(boxstyle="round,pad=0.2", facecolor='lightblue', alpha=0.7))

        # ОРДЕР-БЛОКИ: ИСХОДЯТ ОТ СВЕЧИ И ИДУТ ВПРАВО ДО КОНЦА ГРАФИКА
        for i, block in enumerate(blocks):
            block_time = block['time']
            block_index = df.index.get_loc(block_time)
            block_strength = analyze_block_strength(df, block, block_index)

            # ЯРКИЕ ЦВЕТА ДЛЯ ОРДЕР-БЛОКОВ
            if block_strength == "strong_support":
                color = '#FF4444'  # Ярко-красный
                alpha = 0.25
            elif block_strength == "strong_resistance":
                color = '#44FF44'  # Ярко-зеленый
                alpha = 0.25
            elif block_strength == "volatile":
                color = '#AA44FF'  # Ярко-фиолетовый
                alpha = 0.2
            else:  # tested_once
                color = '#AAAAAA'  # Светло-серый
                alpha = 0.15

            # РИСУЕМ ОРДЕР-БЛОКИ ОТ СВЕЧИ ВПРАВО ДО КОНЦА ГРАФИКА
            block_start_x = mdates.date2num(block_time)
            block_end_x = mdates.date2num(df.index[-1])  # До последней свечи

            # Высота блока от low до high свечи
            block_height = block['high'] - block['low']

            # Создаем прямоугольник от свечи блока до конца графика
            rect = plt.Rectangle((block_start_x, block['low']),
                                 block_end_x - block_start_x,
                                 block_height,
                                 facecolor=color, alpha=alpha,
                                 edgecolor=color, linewidth=1.5,
                                 linestyle='--')
            ax.add_patch(rect)

            # Подписываем ордер-блоки
            text_x = block_start_x + (block_end_x - block_start_x) / 2
            text_y = (block['high'] + block['low']) / 2

            block_type_text = "BUY BLOCK" if block['type'] == 'bullish' else "SELL BLOCK"
            ax.text(text_x, text_y, f"{block_type_text}\n{block_strength}",
                    fontsize=7, ha='center', va='center', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))

        # ЯРКИЕ УРОВНИ ПОДДЕРЖКИ И СОПРОТИВЛЕНИЯ (СПЛОШНЫЕ ЛИНИИ)
        for level in levels:
            if level['type'] == 'support':
                color = '#0000FF'  # Ярко-синий
                linestyle = '-'
                linewidth = 2.5
                label = f'Support {level["value"]:.5f}'
            else:  # resistance
                color = '#FF0000'  # Ярко-красный
                linestyle = '-'
                linewidth = 2.5
                label = f'Resistance {level["value"]:.5f}'

            ax.axhline(y=level['value'], color=color, linestyle=linestyle,
                       linewidth=linewidth, alpha=0.9, label=label)

            # Подписываем уровни
            ax.text(mdates.date2num(df.index[-1]), level['value'],
                    f'{level["value"]:.5f}',
                    fontsize=8, color=color, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))

        # ЯРКИЕ ЖЕЛТЫЕ УРОВНИ ФИБОНАЧЧИ (СПЛОШНЫЕ ЛИНИИ)
        if fib_levels:
            for fib in fib_levels:
                if fib['ratio'] in [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]:
                    color = '#FFFF00'  # Ярко-желтый
                    linestyle = '-'
                    linewidth = 2.0
                    alpha = 0.8

                    ax.axhline(y=fib['value'], color=color, linestyle=linestyle,
                               linewidth=linewidth, alpha=alpha)

                    # Подписываем уровни Фибо
                    ax.text(mdates.date2num(df.index[0]), fib['value'],
                            f'Fib {fib["ratio"] * 100:.1f}%: {fib["value"]:.5f}',
                            fontsize=7, color=color, fontweight='bold',
                            bbox=dict(boxstyle="round,pad=0.2", facecolor='black', alpha=0.7))

        # ДИАГОНАЛЬНЫЕ УРОВНИ (ТРЕНДОВЫЕ ЛИНИИ)
        if len(diagonal_levels) >= 2:
            # Группируем точки по типам
            resistance_points = [p for p in diagonal_levels if p['type'] == 'resistance_diagonal']
            support_points = [p for p in diagonal_levels if p['type'] == 'support_diagonal']

            # Рисуем линии сопротивления (нисходящий тренд)
            if len(resistance_points) >= 2:
                points = sorted(resistance_points, key=lambda x: x['index'])
                x_coords = [mdates.date2num(p['time']) for p in points]
                y_coords = [p['value'] for p in points]

                # Проверяем, что линия имеет отрицательный наклон (нисходящий тренд)
                if len(x_coords) >= 2 and (y_coords[-1] - y_coords[0]) / (x_coords[-1] - x_coords[0]) < 0:
                    ax.plot(x_coords, y_coords, color='#FF00FF', linestyle='--',
                            linewidth=2, alpha=0.8, label='Resistance Trend')

            # Рисуем линии поддержки (восходящий тренд)
            if len(support_points) >= 2:
                points = sorted(support_points, key=lambda x: x['index'])
                x_coords = [mdates.date2num(p['time']) for p in points]
                y_coords = [p['value'] for p in points]

                # Проверяем, что линия имеет положительный наклон (восходящий тренд)
                if len(x_coords) >= 2 and (y_coords[-1] - y_coords[0]) / (x_coords[-1] - x_coords[0]) > 0:
                    ax.plot(x_coords, y_coords, color='#00FFFF', linestyle='--',
                            linewidth=2, alpha=0.8, label='Support Trend')

        # Добавляем индикаторы (тонкие линии чтобы не перекрывать свечи)
        if 'SMA_10' in df:
            ax.plot(df.index, df['SMA_10'], label='SMA 10', color='orange', linestyle='-', linewidth=1.5, alpha=0.8)
        if 'SMA_20' in df:
            ax.plot(df.index, df['SMA_20'], label='SMA 20', color='blue', linestyle='-', linewidth=1.5, alpha=0.8)
        if 'EMA_21' in df:
            ax.plot(df.index, df['EMA_21'], label='EMA 21', color='purple', linestyle='-', linewidth=1.5, alpha=0.8)

        # Точка входа (если указана)
        if entry_price is not None and signal_type is not None:
            entry_color = '#00FF00' if signal_type > 0 else '#FF0000'
            entry_marker = '^' if signal_type > 0 else 'v'
            marker_size = 200

            ax.scatter(df.index[-1], entry_price, color=entry_color, marker=entry_marker,
                       s=marker_size, zorder=10, label='Точка входа',
                       edgecolors='black', linewidth=3)

            ax.axhline(y=entry_price, color=entry_color, linestyle='--', alpha=0.8, linewidth=2)

        # Настройка внешнего вида как в терминале
        ax.xaxis_date()
        time_format = '%H:%M'
        ax.xaxis.set_major_formatter(mdates.DateFormatter(time_format))
        plt.xticks(rotation=45)

        # Определяем категорию
        category = "OTC"
        for cat, instruments in INSTRUMENT_CATEGORIES.items():
            if pair in instruments:
                category = cat
                break

        title = f'{pair} ({category}) {timeframe_name} - ПРОДВИНУТЫЙ АНАЛИЗ\nВсе свечи: {len(df)} (от {df.index[0].strftime("%H:%M")} до {df.index[-1].strftime("%H:%M")})'
        plt.title(title, fontsize=14, pad=20, fontweight='bold')
        plt.legend(loc='upper left', fontsize=8)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()

        chart_path = f"charts/{pair}_{timeframe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        os.makedirs('charts', exist_ok=True)
        plt.savefig(chart_path, bbox_inches='tight', dpi=150, facecolor='white')
        plt.close(fig)

        return chart_path

    except Exception as e:
        logger.error(f"Error creating exact candlestick chart: {e}")
        plt.close('all')
        return None


def chart_worker():
    """Воркер для создания графиков"""
    while not shutdown_event.is_set():
        try:
            task = chart_queue.get(timeout=1)
            if task is None:
                break

            pair, timeframe_name, df, entry_price, signal_type, signal_direction, result_queue = task
            chart_path = create_exact_candlestick_chart(pair, timeframe_name, df, entry_price, signal_type,
                                                        signal_direction)
            result_queue.put(chart_path)

        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Error in chart worker: {e}")


def get_random_instrument_timeframe():
    """Случайный выбор инструмента и таймфрейма"""
    pair = random.choice(OTC_INSTRUMENTS)
    timeframe_name = random.choice(list(TIMEFRAMES.keys()))
    return pair, timeframe_name


def calculate_signal_result(initial_price, current_price, signal_type):
    """ИСПРАВЛЕННЫЙ РАСЧЕТ РЕЗУЛЬТАТА СИГНАЛА"""
    price_change = current_price - initial_price
    price_change_pips = abs(price_change) * 10000

    if signal_type > 0:  # BUY сигнал
        if price_change > 0.0001:
            return "ПЛЮС", price_change_pips
        else:
            return "ДОГОН", price_change_pips
    else:  # SELL сигнал
        if price_change < -0.0001:
            return "ПЛЮС", price_change_pips
        else:
            return "ДОГОН", price_change_pips


def send_analysis_start():
    """Отправка сообщения о начале анализа всех активов"""
    try:
        if not CHANNEL_ID:
            return

        message_text = (
            f"🔍 <b>НАЧАЛО МАСШТАБНОГО АНАЛИЗА</b>\n\n"
            f"📊 Анализируем все {len(OTC_INSTRUMENTS)} активов\n"
            f"⏰ На всех таймфреймах\n"
            f"🕯️ Количество свечей: 120-200\n\n"
            f"<i>Ищем лучший сигнал с максимальной вероятностью...</i>"
        )

        bot.send_message(
            CHANNEL_ID,
            message_text,
            parse_mode='HTML',
            timeout=20
        )
        logger.info(f"Начало анализа всех активов")

    except Exception as e:
        logger.error(f"Error sending analysis start: {e}")


def get_signal_text_for_direction(signal_type):
    """Получение текста сигнала в зависимости от направления"""
    if signal_type > 0:
        return "ПОКУПАТЬ 🟢"
    elif signal_type < 0:
        return "ПРОДАВАТЬ 🔴"
    else:
        return "НЕТ ЧЕТКОГО СИГНАЛА ⚪"


def analyze_single_instrument(pair, timeframe_name):
    """Анализ одного инструмента на одном таймфрейме с учетом последней свечи"""
    try:
        # Получаем ТОЧНЫЕ данные как в терминале с большим количеством свечей
        candle_count = TIMEFRAMES[timeframe_name]["candle_count"]
        df = get_exact_rates_from_mt5(pair, TIMEFRAMES[timeframe_name]["tf"], count=candle_count)

        if df is None or len(df) < 30:
            return None

        # Генерируем сигнал с учетом последней свечи
        signal_text, color, signal_type = generate_signal(df)

        if signal_type == 0:
            return None

        # Рассчитываем вероятность
        probability = calculate_success_probability(df, signal_type)

        # Используем цену закрытия последней свечи как в терминале
        current_price = df['close'].iloc[-1]

        return {
            'pair': pair,
            'timeframe_name': timeframe_name,
            'signal_type': signal_type,
            'signal_text': signal_text,
            'probability': probability,
            'current_price': current_price,
            'df': df,
            'score': probability * abs(signal_type)
        }

    except Exception as e:
        logger.error(f"Error analyzing {pair} {timeframe_name}: {e}")
        return None


def find_best_signal():
    """Поиск лучшего сигнала среди всех активов и таймфреймов"""
    logger.info("Начинаем поиск лучшего сигнала среди всех активов...")

    all_signals = []
    analysis_start_time = time.time()

    # Анализируем все комбинации инструментов и таймфреймов
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        for pair in OTC_INSTRUMENTS:
            for timeframe_name in TIMEFRAMES.keys():
                future = executor.submit(analyze_single_instrument, pair, timeframe_name)
                futures.append(future)

        # Собираем результаты
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result(timeout=15)
                if result and result['probability'] >= 65:
                    all_signals.append(result)
            except concurrent.futures.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in future: {e}")

    # Сортируем сигналы по оценке
    all_signals.sort(key=lambda x: x['score'], reverse=True)

    analysis_duration = time.time() - analysis_start_time
    logger.info(f"Анализ завершен за {analysis_duration:.2f} сек. Найдено {len(all_signals)} сигналов")

    if all_signals:
        best_signal = all_signals[0]
        logger.info(f"Лучший сигнал: {best_signal['pair']} {best_signal['timeframe_name']} "
                    f"вероятность: {best_signal['probability']}% свечей: {len(best_signal['df'])}")
        return best_signal
    else:
        logger.info("Не найдено подходящих сигналов")
        return None


def send_signal_with_chart(pair, timeframe_name, signal_type, initial_price, probability, attempt=1, is_dogon=False):
    """ОТПРАВКА СИГНАЛА С ТОЧНЫМ ГРАФИКОМ (БЕЗ КНОПКИ)"""
    try:
        if not CHANNEL_ID:
            return

        # Получаем ТОЧНЫЕ данные для графика как в терминале с большим количеством свечей
        candle_count = TIMEFRAMES[timeframe_name]["candle_count"]
        df = get_exact_rates_from_mt5(pair, TIMEFRAMES[timeframe_name]["tf"], count=candle_count)
        if df is None:
            logger.error(f"Не удалось получить данные для графика {pair}")
            return None

        # Используем точную цену закрытия последней свечи
        initial_price = df['close'].iloc[-1]

        # Генерируем текст сигнала
        signal_text = get_signal_text_for_direction(signal_type)

        # Создаем график через очередь
        result_queue = queue.Queue()
        signal_direction = f"ДОГОН #{attempt}" if is_dogon else "СИГНАЛ"
        chart_task = (pair, timeframe_name, df, initial_price, signal_type, signal_direction, result_queue)
        chart_queue.put(chart_task)

        try:
            chart_path = result_queue.get(timeout=30)
        except queue.Empty:
            logger.error("Timeout waiting for chart creation")
            chart_path = None

        probability_emoji = get_probability_emoji(probability)

        signal_direction_text = "ПОКУПКА" if signal_type > 0 else "ПРОДАЖА"

        if is_dogon:
            message_text = (
                f"🔄 <b>ДОГОН #{attempt} - {signal_direction_text}</b>\n\n"
                f"📊 <b>Инструмент:</b> {format_mono(pair)}\n"
                f"⏰ <b>Таймфрейм:</b> {format_mono(timeframe_name)}\n"
                f"🕯️ <b>Свечей в анализе:</b> {format_mono(str(len(df)))}\n"
                f"💰 <b>Новая цена входа:</b> {format_mono(f'{initial_price:.5f}')}\n"
                f"🎯 <b>Сигнал:</b> {signal_text}\n"
                f"{probability_emoji} <b>Вероятность:</b> {format_mono(f'{probability}%')}\n\n"
                f"⏳ <i>Ждем {TIMEFRAMES[timeframe_name]['wait_seconds']} секунд для результата...</i>"
            )
        else:
            message_text = (
                f"🎯 <b>ЛУЧШИЙ СИГНАЛ - {signal_direction_text}</b> 🎯\n\n"
                f"📊 <b>Инструмент:</b> {format_mono(pair)}\n"
                f"⏰ <b>Таймфрейм:</b> {format_mono(timeframe_name)}\n"
                f"🕯️ <b>Свечей в анализе:</b> {format_mono(str(len(df)))}\n"
                f"💰 <b>Цена входа:</b> {format_mono(f'{initial_price:.5f}')}\n"
                f"🎯 <b>Сигнал:</b> {signal_text}\n"
                f"{probability_emoji} <b>Вероятность:</b> {format_mono(f'{probability}%')}\n\n"
                f"⏳ <i>Ждем {TIMEFRAMES[timeframe_name]['wait_seconds']} секунд для результата...</i>"
            )

        # УБРАЛИ КНОПКУ ПРОПУСКА - отправляем просто сообщение
        if chart_path and os.path.exists(chart_path):
            try:
                with open(chart_path, 'rb') as chart:
                    message = bot.send_photo(
                        CHANNEL_ID,
                        chart,
                        caption=message_text,
                        parse_mode='HTML',
                        timeout=30
                    )
                logger.info(
                    f"Отправлен сигнал с ПРОДВИНУТЫМ графиком: {pair} {timeframe_name} (попытка {attempt}) свечей: {len(df)}")

                signal_active_event.set()
                logger.info(f"Сигнал активирован после отправки графика: {pair} {timeframe_name}")

                # Удаляем файл после отправки
                time.sleep(1)
                if os.path.exists(chart_path):
                    os.remove(chart_path)

                return message

            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                message = bot.send_message(
                    CHANNEL_ID,
                    message_text + "\n\n⚠ Не удалось создать график",
                    parse_mode='HTML',
                    timeout=20
                )
                signal_active_event.set()
                return message
        else:
            message = bot.send_message(
                CHANNEL_ID,
                message_text,
                parse_mode='HTML',
                timeout=20
            )
            signal_active_event.set()
            return message

    except Exception as e:
        logger.error(f"Error sending signal with chart: {e}")
        return None


def send_signal_result(pair, timeframe_name, result, price_change_pips, attempt, initial_price, current_price,
                       signal_type):
    """Отправка результата сигнала БЕЗ графика"""
    try:
        if not CHANNEL_ID:
            return

        if result == "ПЛЮС":
            emoji = "✅"
            color = "🟢"
            result_text = "УСПЕХ"
        elif result == "ДОГОН":
            emoji = "🔄"
            color = "🟡"
            result_text = "ДОГОН"
        else:
            emoji = "❌"
            color = "🔴"
            result_text = "ПРОИГРЫШ"

        price_change = current_price - initial_price
        direction_emoji = "📈" if price_change > 0 else "📉"
        direction_text = "выросла" if price_change > 0 else "упала"

        signal_direction = "ПОКУПКА" if signal_type > 0 else "ПРОДАЖА"
        expected_direction = "рост" if signal_type > 0 else "падение"
        actual_direction = "рост" if price_change > 0 else "падение"

        direction_match = "✅" if (signal_type > 0 and price_change > 0) or (
                signal_type < 0 and price_change < 0) else "❌"

        message_text = (
            f"{emoji} <b>РЕЗУЛЬТАТ СИГНАЛА #{attempt} - {signal_direction}</b> {color}\n\n"
            f"📊 <b>Инструмент:</b> {format_mono(pair)}\n"
            f"⏰ <b>Таймфрейм:</b> {format_mono(timeframe_name)}\n"
            f"🎯 <b>Тип сигнала:</b> {format_mono(signal_direction)}\n"
            f"💰 <b>Цена входа:</b> {format_mono(f'{initial_price:.5f}')}\n"
            f"💵 <b>Текущая цена:</b> {format_mono(f'{current_price:.5f}')}\n"
            f"📈 <b>Изменение:</b> {format_mono(f'{price_change_pips:.1f} пипс')} {direction_emoji}\n"
            f"🔄 <b>Ожидали:</b> {expected_direction} {direction_match}\n"
            f"📊 <b>Фактически:</b> {actual_direction}\n"
            f"🎯 <b>Результат:</b> <b>{result_text}</b>\n\n"
        )

        if result == "ДОГОН" and attempt < 3:
            message_text += f"🔄 <i>Пробуем еще раз! Попытка #{attempt + 1}</i>"
        elif result == "МИНУС":
            message_text += f"💔 <i>Сигнал закрыт с убытком. Ищем новый актив...</i>"

        bot.send_message(
            CHANNEL_ID,
            message_text,
            parse_mode='HTML',
            timeout=20
        )
        logger.info(f"Результат сигнала: {pair} {timeframe_name} - {result} (попытка {attempt})")

    except Exception as e:
        logger.error(f"Error sending signal result: {e}")


def skip_current_signal():
    """Пропуск текущего сигнала по команде администратора"""
    global current_signal

    if current_signal:
        pair = current_signal['pair']
        timeframe_name = current_signal['timeframe_name']
        attempt = current_signal['attempt']

        logger.info(f"Пропуск сигнала по команде администратора: {pair} {timeframe_name} (попытка {attempt})")

        # Отправляем сообщение о пропуске
        try:
            if CHANNEL_ID:
                bot.send_message(
                    CHANNEL_ID,
                    f"⏭️ <b>СИГНАЛ ПРОПУЩЕН АДМИНИСТРАТОРОМ</b>\n\n"
                    f"📊 {format_mono(pair)}\n"
                    f"⏰ {format_mono(timeframe_name)}\n"
                    f"🔄 Попытка #{attempt}\n\n"
                    f"<i>Ищем новый лучший сигнал...</i>",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о пропуске: {e}")

        # Сбрасываем текущий сигнал
        current_signal = None
        signal_active_event.clear()
        skip_signal_event.set()

        return True
    return False


# ОБРАБОТЧИК КОМАНДЫ /skip В ЛИЧНЫХ СООБЩЕНИЯХ (ОСТАВЛЯЕМ)
@bot.message_handler(commands=['skip'])
def handle_skip_command(message):
    """Обработка команды /skip в личных сообщениях"""
    try:
        # Проверяем, что команда от администратора
        if str(message.from_user.id) == ADMIN_ID:
            logger.info(f"Команда /skip получена от администратора {message.from_user.id}")
            if skip_current_signal():
                bot.reply_to(message, "✅ Сигнал пропущен. Ищем новый лучший сигнал...")
            else:
                bot.reply_to(message, "ℹ️ Нет активного сигнала для пропуска")
        else:
            bot.reply_to(message, "⛔ У вас нет прав для использования этой команды")

    except Exception as e:
        logger.error(f"Ошибка обработки команды /skip: {e}")
        bot.reply_to(message, "❌ Ошибка при обработке команды")


def process_signal_cycle():
    """Основной цикл обработки сигналов с возможностью пропуска"""
    global current_signal, signal_attempt

    while not shutdown_event.is_set():
        try:
            # Проверяем команду пропуска
            if skip_signal_event.is_set():
                skip_signal_event.clear()
                logger.info("Пропуск сигнала активирован")
                time.sleep(2)
                continue

            if current_signal is None:
                # Начинаем поиск лучшего сигнала
                analysis_in_progress.set()
                send_analysis_start()

                # РЕАЛЬНЫЙ АНАЛИЗ всех активов
                best_signal = find_best_signal()
                analysis_in_progress.clear()

                if best_signal and not shutdown_event.is_set() and not skip_signal_event.is_set():
                    # Сохраняем текущий сигнал
                    current_signal = {
                        'pair': best_signal['pair'],
                        'timeframe_name': best_signal['timeframe_name'],
                        'signal_type': best_signal['signal_type'],
                        'initial_price': best_signal['current_price'],
                        'start_time': datetime.now(),
                        'attempt': 1,
                        'original_signal_type': best_signal['signal_type'],
                        'chart_sent': False,
                        'probability': best_signal['probability']
                    }

                    # Сбрасываем флаг активности сигнала
                    signal_active_event.clear()

                    # Отправляем сигнал с ПРОДВИНУТЫМ графиком (БЕЗ КНОПКИ)
                    send_signal_with_chart(
                        current_signal['pair'],
                        current_signal['timeframe_name'],
                        current_signal['signal_type'],
                        current_signal['initial_price'],
                        current_signal['probability']
                    )

                    # Ждем отправки графика с проверкой пропуска
                    wait_for_chart_timeout = 30
                    start_wait_time = time.time()

                    while not signal_active_event.is_set() and not shutdown_event.is_set() and not skip_signal_event.is_set():
                        if time.time() - start_wait_time > wait_for_chart_timeout:
                            logger.error(f"Таймаут ожидания отправки графика для {current_signal['pair']}")
                            current_signal = None
                            break
                        time.sleep(0.5)

                    if skip_signal_event.is_set():
                        current_signal = None
                        signal_active_event.clear()
                        continue

                    if current_signal and signal_active_event.is_set():
                        current_signal['chart_sent'] = True
                        logger.info(
                            f"Продвинутый график отправлен, сигнал активен: {current_signal['pair']} {current_signal['timeframe_name']}")

                        # Ждем время таймфрейма с проверкой пропуска
                        wait_time = TIMEFRAMES[current_signal['timeframe_name']]["wait_seconds"]
                        logger.info(f"Ждем {wait_time} секунд для результата...")

                        # Разбиваем ожидание на части для проверки пропуска
                        for _ in range(wait_time):
                            if shutdown_event.is_set() or skip_signal_event.is_set():
                                break
                            time.sleep(1)

                        if skip_signal_event.is_set():
                            current_signal = None
                            signal_active_event.clear()
                            continue
                else:
                    if not skip_signal_event.is_set():
                        logger.info("Не найдено подходящих сигналов, ждем 10 секунд...")
                        time.sleep(10)

            else:
                # Проверяем результат текущего сигнала
                if current_signal.get('chart_sent', False) and not skip_signal_event.is_set():
                    pair = current_signal['pair']
                    timeframe_name = current_signal['timeframe_name']
                    signal_type = current_signal['signal_type']
                    initial_price = current_signal['initial_price']
                    attempt = current_signal['attempt']

                    # Получаем ТОЧНУЮ текущую цену из терминала
                    df = get_exact_rates_from_mt5(pair, TIMEFRAMES[timeframe_name]["tf"], count=5)
                    if df is not None and len(df) > 0:
                        current_price = df['close'].iloc[-1]
                    else:
                        current_price = initial_price

                    # Рассчитываем результат
                    result, price_change_pips = calculate_signal_result(initial_price, current_price, signal_type)

                    # Отправляем результат
                    send_signal_result(pair, timeframe_name, result, price_change_pips, attempt, initial_price,
                                       current_price, signal_type)

                    if result == "ПЛЮС":
                        current_signal = None
                        signal_attempt = 0
                        signal_active_event.clear()
                        logger.info("Сигнал успешен, ищем новый лучший сигнал")
                        time.sleep(5)

                    elif result == "ДОГОН":
                        if attempt < 3 and not skip_signal_event.is_set():
                            dogon_delay = random.randint(2, 5)
                            logger.info(f"Задержка перед догоном: {dogon_delay} сек")
                            time.sleep(dogon_delay)

                            if skip_signal_event.is_set():
                                current_signal = None
                                signal_active_event.clear()
                                continue

                            current_signal['attempt'] += 1
                            current_signal['initial_price'] = current_price
                            current_signal['chart_sent'] = False
                            current_signal['signal_type'] = current_signal.get('original_signal_type', signal_type)

                            signal_active_event.clear()

                            # Пересчитываем вероятность для догона
                            candle_count = TIMEFRAMES[timeframe_name]["candle_count"]
                            df_new = get_exact_rates_from_mt5(pair, TIMEFRAMES[timeframe_name]["tf"],
                                                              count=candle_count)
                            if df_new is not None:
                                probability = calculate_success_probability(df_new, signal_type)
                                current_signal['probability'] = probability

                                send_signal_with_chart(pair, timeframe_name, signal_type, current_price,
                                                       probability, attempt + 1, True)

                                wait_for_chart_timeout = 30
                                start_wait_time = time.time()

                                while not signal_active_event.is_set() and not shutdown_event.is_set() and not skip_signal_event.is_set():
                                    if time.time() - start_wait_time > wait_for_chart_timeout:
                                        logger.error(f"Таймаут ожидания отправки графика для догона {pair}")
                                        current_signal = None
                                        break
                                    time.sleep(0.5)

                                if skip_signal_event.is_set():
                                    current_signal = None
                                    signal_active_event.clear()
                                    continue

                                if current_signal and signal_active_event.is_set():
                                    current_signal['chart_sent'] = True

                            wait_time = TIMEFRAMES[timeframe_name]["wait_seconds"]
                            for _ in range(wait_time):
                                if shutdown_event.is_set() or skip_signal_event.is_set():
                                    break
                                time.sleep(1)

                            if skip_signal_event.is_set():
                                current_signal = None
                                signal_active_event.clear()
                                continue
                        else:
                            send_signal_result(pair, timeframe_name, "МИНУС", price_change_pips, attempt, initial_price,
                                               current_price, signal_type)
                            current_signal = None
                            signal_attempt = 0
                            signal_active_event.clear()
                            logger.info("3 догона - сигнал в минус, ищем новый лучший сигнал")
                            time.sleep(5)
                else:
                    if not skip_signal_event.is_set():
                        logger.warning("Сигнал без графика, сбрасываем...")
                        current_signal = None
                        signal_active_event.clear()
                        time.sleep(5)

        except Exception as e:
            logger.error(f"Error in signal cycle: {e}")
            current_signal = None
            signal_attempt = 0
            signal_active_event.clear()
            analysis_in_progress.clear()
            time.sleep(10)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        f"🎯 <b>СКАЛЬПИНГ БОТ С СИСТЕМОЙ ПЛЮС/ДОГОН</b>\n\n"
        f"📊 <b>Режим работы:</b>\n"
        f"• Анализ ВСЕХ активов и выбор ЛУЧШЕГО сигнала\n"
        f"• ПРОДВИНУТЫЕ графики с расширенным анализом\n"
        f"• Ордер-блоки, уровни Фибоначчи, поддержка/сопротивление\n"
        f"• Команда /skip для пропуска сигнала\n"
        f"• Реальный анализ с поиском максимальной вероятности\n\n"
        f"⏰ <b>Таймфреймы:</b> 1M, 2M, 3M\n"
        f"📈 <b>Инструменты:</b> {len(OTC_INSTRUMENTS)} активов\n"
        f"🕯️ <b>Свечей в анализе:</b> 120-200\n"
        f"🔄 <b>Цикл:</b> Анализ всех → Выбор лучшего → Сигнал → Результат",
        parse_mode='HTML'
    )


@bot.message_handler(commands=['status'])
def show_status(message):
    """Показать текущий статус"""
    if analysis_in_progress.is_set():
        status_text = "🔍 <b>ИДЕТ АНАЛИЗ ВСЕХ АКТИВОВ...</b>\n\nИщем лучший сигнал среди всех инструментов"
    elif current_signal:
        signal_type_text = "ПОКУПКА" if current_signal['signal_type'] > 0 else "ПРОДАЖА"
        chart_status = "✅ Отправлен" if current_signal.get('chart_sent', False) else "⏳ Ожидает отправки"
        status_text = (
            f"📊 <b>ТЕКУЩИЙ ЛУЧШИЙ СИГНАЛ - {signal_type_text}</b>\n\n"
            f"• Инструмент: {current_signal['pair']}\n"
            f"• Таймфрейм: {current_signal['timeframe_name']}\n"
            f"• Попытка: #{current_signal['attempt']}\n"
            f"• Вероятность: {current_signal.get('probability', 0)}%\n"
            f"• Цена входа: {current_signal['initial_price']:.5f}\n"
            f"• График: {chart_status}\n"
            f"• Время начала: {current_signal['start_time'].strftime('%H:%M:%S')}\n\n"
            f"<i>Для пропуска напишите /skip боту в личные сообщения</i>"
        )
    else:
        status_text = "🔍 <b>ПОИСК ЛУЧШЕГО СИГНАЛА...</b>"

    bot.send_message(message.chat.id, status_text, parse_mode='HTML')


def cleanup():
    """Очистка ресурсов при завершении"""
    logger.info("Cleaning up resources...")
    shutdown_event.set()
    signal_active_event.set()
    analysis_in_progress.set()
    skip_signal_event.set()
    plt.close('all')

    if os.path.exists('charts'):
        for filename in os.listdir('charts'):
            try:
                filepath = os.path.join('charts', filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            except Exception as e:
                logger.error(f"Error removing {filename}: {e}")

    mt5.shutdown()
    logger.info("Cleanup completed")


if __name__ == '__main__':
    try:
        logger.info("Starting Advanced Scalping Bot with ENHANCED CHARTS...")

        # Проверка обязательных переменных
        required_env_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHANNEL_ID', 'ADMIN_TELEGRAM_ID']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

        os.makedirs('charts', exist_ok=True)

        if initialize_mt5():
            # Запускаем воркер для графиков
            chart_thread = threading.Thread(target=chart_worker, daemon=True)
            chart_thread.start()

            # Запускаем основной цикл обработки сигналов
            signal_thread = threading.Thread(target=process_signal_cycle, daemon=True)
            signal_thread.start()

            # Стартовое сообщение в канал
            if CHANNEL_ID:
                try:
                    bot.send_message(
                        CHANNEL_ID,
                        f"🎯 <b>БОТ ЗАПУЩЕН С ПРОДВИНУТЫМИ ГРАФИКАМИ!</b>\n\n"
                        f"📊 <b>Улучшения:</b>\n"
                        f"• Яркие ордер-блоки от свечи вправо до конца графика\n"
                        f"• Уровни поддержки/сопротивления (сплошные линии)\n"
                        f"• Сетка Фибоначчи (яркие желтые линии)\n"
                        f"• Диагональные уровни (трендовые линии)\n"
                        f"• Цены на максимумах и минимумах\n"
                        f"• Команда /skip для пропуска сигналов\n"
                        f"• Анализ на 120-200 свечах\n\n"
                        f"⏰ Таймфреймы: 1M, 2M, 3M\n"
                        f"📈 Инструменты: {len(OTC_INSTRUMENTS)}\n"
                        f"🕯️ Свечей в анализе: 120-200\n"
                        f"🔄 Режим: Анализ всех → Выбор лучшего → Сигнал → Результат",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки стартового сообщения: {e}")

            logger.info(f"Bot started successfully with {len(OTC_INSTRUMENTS)} instruments")

            # Улучшенный polling с обработкой ошибок SSL
            while not shutdown_event.is_set():
                try:
                    bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
                except Exception as polling_error:
                    logger.error(f"Polling error: {polling_error}")
                    if not shutdown_event.is_set():
                        logger.info("Restarting polling in 15 seconds...")
                        time.sleep(15)
                        bot.session = create_telegram_session()

        else:
            logger.error("Failed to initialize MT5")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        cleanup()