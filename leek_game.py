# leek_game.py

import time
from collections import deque
import api_client  # Import our new api_client
import config  # Import our new config file


class Leek:
    def __init__(self, symbol, base_coefficient, sensitivity_parameter):
        self.symbol = symbol
        self.base_coefficient = base_coefficient
        self.sensitivity_parameter = sensitivity_parameter

        self.H0 = 0.0
        self.current_height = 0.0
        self.previous_close_price = None  # Cₜ₋₁

        self.kline_history_short = deque(maxlen=config.KLINE_HISTORY_COUNT_SHORT)
        self.kline_history_long = deque(maxlen=config.KLINE_HISTORY_COUNT_LONG)

        self.consecutive_yellowing_triggers = 0
        self.color_h = 120.0
        self.color_s = 100.0
        self.color_l = 50.0

        self.visual_state = "healthy"  # "healthy", "slightly_yellow"

        self.game_state = "initializing"  # "initializing", "running", "won_height", "won_fertilizer", "lost_height", "lost_scythe"
        self.last_processed_kline_open_time = 0
        self.start_time_unix = time.time()  # For NFT conceptual data

        print(f"Initializing Leek for {self.symbol}...")
        self._initialize_height_and_history()

    def _initialize_height_and_history(self):
        print(
            f"[{self.symbol}] Fetching {config.INITIAL_HEIGHT_DAYS}-day historical daily klines for initial height...")
        # Fetch INITIAL_HEIGHT_DAYS daily klines + 1 to ensure the last one used for average is complete
        daily_klines = api_client.get_klines_from_api(self.symbol, "1d", config.INITIAL_HEIGHT_DAYS + 1)

        if not daily_klines or len(daily_klines) < config.INITIAL_HEIGHT_DAYS:
            print(
                f"[{self.symbol}] ERROR: Could not fetch enough daily klines for initial height (got {len(daily_klines)}). Using default H0=0.")
            self.H0 = 0.0
        else:
            # Use closing prices of the *config.INITIAL_HEIGHT_DAYS* oldest klines from the fetched set.
            closing_prices = [k['close'] for k in daily_klines[:config.INITIAL_HEIGHT_DAYS]]
            avg_price = sum(closing_prices) / len(closing_prices) if closing_prices else 0
            self.H0 = avg_price * self.base_coefficient
            print(
                f"[{self.symbol}] {config.INITIAL_HEIGHT_DAYS}-day Avg Close Price: {avg_price:.2f}, Base Coeff: {self.base_coefficient}")

        self.current_height = self.H0
        if self.H0 <=0: # 如果H0无效，则游戏可能无法正常开始，设置一个极小高度或错误状态
            print(f"[{self.symbol}] Warning: H0 is {self.H0}. Current height set to 0 or a minimum.")
            self.current_height = 1 # 避免为0导致后续计算问题，或者在UI层面直接显示错误/初始状态
            self.game_state = "error_no_h0" # 或者保持initializing，让UI决定

        print(f"[{self.symbol}] Initial Height H₀: {self.current_height:.2f}")

        print(f"[{self.symbol}] Fetching initial {config.KLINE_INTERVAL} klines for volume history...")
        num_initial_klines = max(config.KLINE_HISTORY_COUNT_SHORT, config.KLINE_HISTORY_COUNT_LONG) + 1
        initial_5m_klines = api_client.get_klines_from_api(self.symbol, config.KLINE_INTERVAL, num_initial_klines)

        if initial_5m_klines:
            if len(initial_5m_klines) > 1:  # Need at least 2 klines to set previous_close_price and populate history
                # The last kline in the list is the most recent *completed* one. This becomes Cₜ₋₁
                self.previous_close_price = initial_5m_klines[-1]['close']
                self.last_processed_kline_open_time = initial_5m_klines[-1]['open_time']
                print(
                    f"[{self.symbol}] Set initial Cₜ₋₁: {self.previous_close_price:.2f} (from kline @ {self.last_processed_kline_open_time})")

                # Populate history deques with klines *before* the last one
                for kline in initial_5m_klines[:-1]:
                    self.kline_history_short.append(kline)
                    self.kline_history_long.append(kline)
                print(
                    f"[{self.symbol}] Populated short history with {len(self.kline_history_short)} klines, long with {len(self.kline_history_long)} klines.")
            elif len(initial_5m_klines) == 1:  # Only one kline fetched
                self.previous_close_price = initial_5m_klines[0]['close']  # Will be used in the first update
                self.last_processed_kline_open_time = initial_5m_klines[0]['open_time']
                print(
                    f"[{self.symbol}] Only 1 initial kline fetched. Cₜ₋₁ set to {self.previous_close_price:.2f}. History will build up.")
            else:  # No klines fetched
                print(
                    f"[{self.symbol}] WARNING: Could not fetch initial {config.KLINE_INTERVAL} klines. Volume averages will be inaccurate at start.")

        else:  # API call returned empty or error
            print(
                f"[{self.symbol}] WARNING: Could not fetch initial {config.KLINE_INTERVAL} klines. Volume averages will be inaccurate at start.")

        # 确保在初始化结束时，如果H0有效，则状态为running
        if self.H0 > 0 :
            self.game_state = "running"
        # else game_state 可能是 "initializing" 或 "error_no_h0"

    def update_state(self, new_kline_data):
        if self.game_state != "running":
            # print(f"[{self.symbol}] Game is not running (state: {self.game_state}). Skipping update.")
            return

        if new_kline_data['open_time'] <= self.last_processed_kline_open_time:
            # print(f"[{self.symbol}] Kline {new_kline_data['open_time']} already processed or is old. Skipping.")
            return

        Ct = new_kline_data['close']
        Ot = new_kline_data['open']
        Ht = new_kline_data['high']
        Lt = new_kline_data['low']
        Vt = new_kline_data['volume']

        print(
            f"\n[{self.symbol}] Processing Kline @ {new_kline_data['open_time']}: O:{Ot:.2f} H:{Ht:.2f} L:{Lt:.2f} C:{Ct:.2f} V:{Vt:.2f}")

        if self.previous_close_price is None or self.previous_close_price == 0:
            delta_h = 0 # 安全起见
            if self.previous_close_price is None:
                 print(f"[{self.symbol}] First live kline. Setting Cₜ₋₁ to {Ct:.2f}. Height unchanged this cycle.")
            else: # previous_close_price == 0
                 print(f"[{self.symbol}] Warning: Cₜ₋₁ is zero. ΔH set to 0.")
        else:
            price_change_ratio = (Ct - self.previous_close_price) / self.previous_close_price
            delta_h = price_change_ratio * self.sensitivity_parameter
            delta_h = max(config.DELTA_H_MIN, min(delta_h, config.DELTA_H_MAX))

        self.current_height += delta_h
        self.current_height = max(0, self.current_height) # 确保高度不为负
        ct_minus_1_str = f"{self.previous_close_price:.2f}" if isinstance(self.previous_close_price, float) else str(self.previous_close_price) if self.previous_close_price is not None else "N/A"
        print(
            f"[{self.symbol}] Cₜ₋₁:{ct_minus_1_str}, Cₜ:{Ct:.2f} => ΔH:{delta_h:.2f}, New Height:{self.current_height:.2f}")
        
        self.previous_close_price = Ct
        self.last_processed_kline_open_time = new_kline_data['open_time']
        self.kline_history_short.append(new_kline_data)
        self.kline_history_long.append(new_kline_data)

        if self.current_height >= config.GAME_TARGET_HEIGHT_WIN:
            self.game_state = "won_height"
            print(f"[{self.symbol}] VICTORY! Leek reached target height: {self.current_height:.2f}")
            return
        if self.current_height <= config.GAME_MIN_HEIGHT_LOSE:
            self.game_state = "lost_height"
            print(f"[{self.symbol}] DEFEAT! Leek height fell to {self.current_height:.2f}. Pot shatters!")
            return

        kline_body_percentage_change = ((Ct - Ot) / Ot * 100) if Ot != 0 else 0

        volumes_short = [k['volume'] for k in self.kline_history_short if
                         k]  # Ensure k is not None if deque was not full
        avg_volume_3hr = sum(volumes_short) / len(volumes_short) if volumes_short else 0

        scythe_by_volume = avg_volume_3hr > 0 and Vt >= avg_volume_3hr * config.SCYTHE_VOLUME_THRESHOLD_MULTIPLIER
        scythe_by_price = kline_body_percentage_change <= config.SCYTHE_PRICE_DROP_THRESHOLD

        if scythe_by_volume: print(
            f"[{self.symbol}] Scythe (Volume): Current Vol {Vt:.2f} vs Avg 3hr Vol {avg_volume_3hr:.2f} (x{config.SCYTHE_VOLUME_THRESHOLD_MULTIPLIER})")
        if scythe_by_price: print(
            f"[{self.symbol}] Scythe (Price): Body Change {kline_body_percentage_change:.2f}% <= {config.SCYTHE_PRICE_DROP_THRESHOLD}%")

        if scythe_by_volume and scythe_by_price:
            self.game_state = "lost_scythe"
            print(f"[{self.symbol}] DEFEAT! Scythe Mechanism triggered.")
            return

        fertilizer_by_volume = avg_volume_3hr > 0 and Vt >= avg_volume_3hr * config.FERTILIZER_VOLUME_THRESHOLD_MULTIPLIER
        fertilizer_by_price = kline_body_percentage_change >= config.FERTILIZER_PRICE_RISE_THRESHOLD

        if fertilizer_by_volume: print(
            f"[{self.symbol}] Fertilizer (Volume): Current Vol {Vt:.2f} vs Avg 3hr Vol {avg_volume_3hr:.2f} (x{config.FERTILIZER_VOLUME_THRESHOLD_MULTIPLIER})")
        if fertilizer_by_price: print(
            f"[{self.symbol}] Fertilizer (Price): Body Change {kline_body_percentage_change:.2f}% >= {config.FERTILIZER_PRICE_RISE_THRESHOLD}%")

        if fertilizer_by_volume and fertilizer_by_price:
            self.game_state = "won_fertilizer"
            print(f"[{self.symbol}] VICTORY! Fertilizer Mechanism triggered.")
            return

        volumes_long = [k['volume'] for k in self.kline_history_long if k]
        avg_volume_24hr = sum(volumes_long) / len(volumes_long) if volumes_long else 0

        kline_price_volatility = ((Ht - Lt) / Lt * 100) if Lt != 0 else 0

        yellowing_by_volume = avg_volume_24hr > 0 and Vt <= avg_volume_24hr * config.YELLOWING_VOLUME_THRESHOLD_RATIO
        yellowing_by_volatility = kline_price_volatility <= config.YELLOWING_PRICE_VOLATILITY_THRESHOLD

        if yellowing_by_volume: print(
            f"[{self.symbol}] Yellowing (Volume): Current Vol {Vt:.2f} vs Avg 24hr Vol {avg_volume_24hr:.2f} (Ratio: {config.YELLOWING_VOLUME_THRESHOLD_RATIO})")
        if yellowing_by_volatility: print(
            f"[{self.symbol}] Yellowing (Volatility): Kline Volatility {kline_price_volatility:.2f}% <= {config.YELLOWING_PRICE_VOLATILITY_THRESHOLD}%")

        conditions_for_yellowing_met = yellowing_by_volume and yellowing_by_volatility

        if conditions_for_yellowing_met:
            self.consecutive_yellowing_triggers = min(self.consecutive_yellowing_triggers + 1,
                                                      config.YELLOWING_T_MAX_INTERVALS)
            print(
                f"[{self.symbol}] Yellowing conditions met. Consecutive triggers: {self.consecutive_yellowing_triggers}/{config.YELLOWING_T_MAX_INTERVALS}")
        else:
            # 允许从变黄状态恢复
            self.consecutive_yellowing_triggers = max(0, self.consecutive_yellowing_triggers - 1)

        if self.consecutive_yellowing_triggers >= config.YELLOWING_THRESHOLD_FOR_SLIGHTLY_YELLOW:
            self.visual_state = "slightly_yellow"
            # 更新HSL值以反映微黄（可选，如果UI文本中还显示HSL）
            self.color_h = 80.0  # 例如，黄绿色
            self.color_s = 90.0
            self.color_l = 55.0
        elif self.consecutive_yellowing_triggers < config.YELLOWING_RECOVERY_THRESHOLD: # 通常是0
            self.visual_state = "healthy"
            # 恢复健康绿色HSL值（可选）
            self.color_h = 120.0 # 鲜绿
            self.color_s = 100.0
            self.color_l = 50.0
        # 如果介于两者之间，visual_state 保持不变

        print(f"[{self.symbol}] Visual State: {self.visual_state}, Yellowing Triggers: {self.consecutive_yellowing_triggers}")

    def get_status(self):
        return {
            "symbol": self.symbol,
            "height": self.current_height,
            "H0": self.H0,
            "game_state": self.game_state,
            "visual_state": self.visual_state,
            "color_hsl": (self.color_h, self.color_s, self.color_l),
            "last_kline_time_ms": self.last_processed_kline_open_time,
            "Ct-1": self.previous_close_price,
            "start_time_unix": self.start_time_unix
        }
