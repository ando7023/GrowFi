# config.py

# API Configuration
API_BASE_URL = "https://api.binance.com/api/v3/" # Example: Binance

# Game Parameters
INITIAL_HEIGHT_DAYS = 20         # For calculating initial average price
BASE_COEFFICIENT_DEFAULT = 0.1   # H₀ = 20日均价 × 基础系数
SENSITIVITY_PARAMETER_DEFAULT = 2000 # ΔH = ((Cₜ - Cₜ₋₁) / Cₜ₋₁) × 灵敏度参数

# Symbol-specific overrides (optional)
SYMBOL_SPECIFIC_CONFIG = {
    "BTCUSDT": {"base_coefficient": 0.1, "sensitivity_parameter": 2000},
    "ETHUSDT": {"base_coefficient": 1.0, "sensitivity_parameter": 1000},
    # Add other symbols if they need specific tuning
}

# ΔH limits
DELTA_H_MIN = -100  # Max decrease in height per 5 min interval
DELTA_H_MAX = 200   # Max increase in height per 5 min interval

# Scythe Mechanism Triggers
SCYTHE_VOLUME_THRESHOLD_MULTIPLIER = 3.0 # Current volume >= X times 3-hour average
SCYTHE_PRICE_DROP_THRESHOLD = -3.0       # K-line body drop <= -3%

# Fertilizer Mechanism Triggers
FERTILIZER_VOLUME_THRESHOLD_MULTIPLIER = 3.0 # Current volume >= X times 3-hour average
FERTILIZER_PRICE_RISE_THRESHOLD = 3.0        # K-line body rise >= 3%

# Yellowing Mechanism Triggers
YELLOWING_VOLUME_THRESHOLD_RATIO = 0.20
YELLOWING_PRICE_VOLATILITY_THRESHOLD = 0.5
YELLOWING_T_MAX_INTERVALS = 30  # 仍然可以用作连续触发的上限
# 新增配置:
YELLOWING_THRESHOLD_FOR_SLIGHTLY_YELLOW = 5 # 连续触发5次变黄条件后，进入"微黄"状态
YELLOWING_RECOVERY_THRESHOLD = 1 # 当连续触发次数降到1次以下（即0次）时，恢复"健康"状态

# Game End Conditions
GAME_TARGET_HEIGHT_WIN = 6000 # Corresponds to visual "60"
GAME_MIN_HEIGHT_LOSE = 10     # Corresponds to visual "1" or a low threshold

# K-line and History Configuration
KLINE_INTERVAL = "5m"
KLINE_HISTORY_COUNT_SHORT = 36  # For 3-hour average (3 hours * 12 klines/hour)
KLINE_HISTORY_COUNT_LONG = 288 # For 24-hour average (24 hours * 12 klines/hour)

# Simulation settings for main.py
SIMULATION_MAX_RUNS = 200      # Number of 5-min intervals to simulate
SIMULATION_SLEEP_INTERVAL_SECONDS = 10 # Seconds to wait between intervals (for testing)
                                      # Use 300 for actual 5 minutes

PRICE_TICKER_INTERVAL_SECONDS = 5 # Interval to fetch current price for display (e.g., 5 seconds)
LEEK_CANVAS_WIDTH = 200           # Width of the leek visualization canvas
LEEK_CANVAS_HEIGHT = 400          # Max height of the leek visualization canvas
LEEK_RECT_WIDTH = 100              # Width of the rectangle representing the leek