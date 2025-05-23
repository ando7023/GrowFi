# ui_main.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import datetime
import colorsys
from PIL import Image, ImageTk # 导入Pillow库

import leek_game
import api_client
import config

# Global variables
player_leek = None
game_update_id = None  # For the 5-minute game logic update
price_ticker_update_id = None  # For the few-seconds price ticker update
current_monitoring_symbol = None  # To store the symbol being monitored

# Global storage for image objects to prevent garbage collection
leek_images = {
    "initial": None,
    "healthy": None,
    "slightly_yellow": None,
    "fallback_pot": None # For fallback image when loading fails
}

def load_leek_images():
    """
    Load leek images.
    'healthy' and 'slightly_yellow' images are scaled to have a width of config.LEEK_RECT_WIDTH,
    with height scaled proportionally.
    'initial' image is scaled to have a width of config.LEEK_RECT_WIDTH * 1.1 (can be adjusted),
    with height scaled proportionally.
    """
    try:
        target_leek_width = config.LEEK_RECT_WIDTH

        # Healthy state image
        img_healthy_orig = Image.open("assets/healthy.jpg") # Assuming .png, adjust if .jpg
        original_width_h, original_height_h = img_healthy_orig.size
        if original_width_h == 0: raise ValueError("Healthy image original width is zero.") # Prevent division by zero
        
        scale_ratio_h = target_leek_width / original_width_h
        new_height_h = int(original_height_h * scale_ratio_h)
        new_width_h = target_leek_width # Explicitly set to target width
        
        img_healthy_resized = img_healthy_orig.resize((new_width_h, new_height_h), Image.Resampling.LANCZOS)
        leek_images["healthy"] = ImageTk.PhotoImage(img_healthy_resized)

        # Slightly yellow state image
        img_sy_orig = Image.open("assets/slightly_yellow.jpg") # Assuming .png
        original_width_sy, original_height_sy = img_sy_orig.size
        if original_width_sy == 0: raise ValueError("Slightly yellow image original width is zero.")

        scale_ratio_sy = target_leek_width / original_width_sy
        new_height_sy = int(original_height_sy * scale_ratio_sy)
        new_width_sy = target_leek_width

        img_sy_resized = img_sy_orig.resize((new_width_sy, new_height_sy), Image.Resampling.LANCZOS)
        leek_images["slightly_yellow"] = ImageTk.PhotoImage(img_sy_resized)
        
        # Initial state image (e.g., a pot)
        target_initial_width = int(target_leek_width * 1.1) # Make pot slightly wider than leek, adjust as needed
        img_initial_orig = Image.open("assets/initial.jpg") # Assuming .png
        original_width_i, original_height_i = img_initial_orig.size
        if original_width_i == 0: raise ValueError("Initial image original width is zero.")

        scale_ratio_i = target_initial_width / original_width_i
        new_height_i = int(original_height_i * scale_ratio_i)
        new_width_i = target_initial_width

        img_initial_resized = img_initial_orig.resize((new_width_i, new_height_i), Image.Resampling.LANCZOS)
        leek_images["initial"] = ImageTk.PhotoImage(img_initial_resized)

        print("Leek images loaded and proportionally scaled.")
        return True
    except FileNotFoundError as e:
        messagebox.showerror("Image Error", f"Image file not found: {e}. Please ensure 'assets' folder and .png images exist.")
        leek_images["healthy"] = None
        leek_images["slightly_yellow"] = None
        leek_images["initial"] = None
        return False
    except ValueError as e: # Catch division by zero if original width is 0
        messagebox.showerror("Image Error", f"Error processing image dimensions: {e}. Original width might be zero.")
        leek_images["healthy"] = None
        leek_images["slightly_yellow"] = None
        leek_images["initial"] = None
        return False
    except Exception as e:
        messagebox.showerror("Image Error", f"Error loading or resizing images: {e}. Will use color drawing instead.")
        leek_images["healthy"] = None
        leek_images["slightly_yellow"] = None
        leek_images["initial"] = None
        return False

def hsl_to_rgb_hex(h, s, l_val):
    if h is None or s is None or l_val is None:
        return "#222222"  # Default dark color if not set
    try:
        r, g, b = colorsys.hls_to_rgb(h / 360.0, l_val / 100.0, s / 100.0)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    except Exception:
        return "#222222"


def draw_leek_visualization():
    leek_canvas.delete("all")

    image_to_draw_id = None
    use_fallback_color = False
    current_image_obj = None

    if player_leek and player_leek.game_state == "running" and player_leek.H0 is not None and player_leek.H0 > 0:
        status = player_leek.get_status()
        visual_state = status.get("visual_state", "healthy")

        if visual_state == "slightly_yellow":
            image_to_draw_id = "slightly_yellow"
        else: # "healthy"
            image_to_draw_id = "healthy"
        
        current_image_obj = leek_images.get(image_to_draw_id)
        if not current_image_obj:
            use_fallback_color = True
            leek_fill_color = hsl_to_rgb_hex(*status.get("color_hsl", (120,100,50)))
        
        game_height = player_leek.current_height
        base_height = player_leek.H0
        
        # Height scaling logic (calculates how many pixels of the image to show)
        min_visual_height = max(base_height * 0.1, 10)
        max_visual_height = base_height * 2.0
        if max_visual_height <= min_visual_height:
            max_visual_height = min_visual_height + (1000 if base_height <=0 else base_height)

        clamped_game_height = max(min_visual_height, min(game_height, max_visual_height))
        denominator = max_visual_height - min_visual_height
        height_proportion = 0.5 if denominator <= 0 else (clamped_game_height - min_visual_height) / denominator
        
        min_pixel_height_display = 20 
        max_render_height = config.LEEK_CANVAS_HEIGHT - min_pixel_height_display
        
        # This is the calculated height IN GAME UNITS, converted to pixels to show on canvas
        pixel_height_to_show_on_canvas = min_pixel_height_display + (height_proportion * max_render_height)
        pixel_height_to_show_on_canvas = max(min_pixel_height_display, min(pixel_height_to_show_on_canvas, config.LEEK_CANVAS_HEIGHT))

        # Drawing
        image_center_x = config.LEEK_CANVAS_WIDTH / 2
        
        if not use_fallback_color and current_image_obj:
            img_actual_width = current_image_obj.width()
            img_actual_height = current_image_obj.height()

            # Ensure pixel_height_to_show_on_canvas does not exceed the actual image height
            # This is how much of the *image's own height* we will make visible from the bottom
            effective_visible_image_height = min(pixel_height_to_show_on_canvas, img_actual_height)

            # Draw the image, anchored at its bottom center
            # The image's bottom will align with the canvas's bottom.
            leek_canvas.create_image(image_center_x, config.LEEK_CANVAS_HEIGHT,
                                     image=current_image_obj, anchor='s')
            
            # Mask the top part of the image
            # mask_top_y is the y-coordinate on the canvas where the visible part of the image begins
            mask_top_y_on_canvas = config.LEEK_CANVAS_HEIGHT - effective_visible_image_height
            
            # The mask's x-coordinates are relative to the centered image
            mask_x0 = image_center_x - img_actual_width / 2
            mask_x1 = image_center_x + img_actual_width / 2

            if mask_top_y_on_canvas > 0: # Only mask if not showing full image or more
                 # Create a rectangle from canvas top (y=0) down to mask_top_y_on_canvas
                 # spanning the width of the image.
                leek_canvas.create_rectangle(
                    mask_x0, 0, 
                    mask_x1, mask_top_y_on_canvas,
                    fill=leek_canvas.cget('bg'),
                    outline=leek_canvas.cget('bg')
                )
        else: # Fallback to color drawing
            # Use config.LEEK_RECT_WIDTH for fallback rectangle width
            fallback_rect_half_width = config.LEEK_RECT_WIDTH / 2
            x0 = image_center_x - fallback_rect_half_width
            x1 = image_center_x + fallback_rect_half_width
            y1_rect = config.LEEK_CANVAS_HEIGHT
            y0_rect = config.LEEK_CANVAS_HEIGHT - pixel_height_to_show_on_canvas # Use the general pixel height for fallback
            leek_canvas.create_rectangle(x0, y0_rect, x1, y1_rect, fill=leek_fill_color, outline="darkgreen", width=2)

        # Current height text (position relative to the image or fallback rect)
        # If image was drawn, use its width, otherwise use LEEK_RECT_WIDTH for fallback
        display_item_width = img_actual_width if not use_fallback_color and current_image_obj else config.LEEK_RECT_WIDTH
        text_x_pos = (image_center_x + display_item_width / 2) + 5
        
        # Y position of text, vertically centered on the visible part of the leek
        visible_part_top_y = config.LEEK_CANVAS_HEIGHT - (effective_visible_image_height if not use_fallback_color and current_image_obj else pixel_height_to_show_on_canvas)
        text_y_pos_candidate = visible_part_top_y + ( (effective_visible_image_height if not use_fallback_color and current_image_obj else pixel_height_to_show_on_canvas) / 2)
        text_y_pos = max(10, min(text_y_pos_candidate, config.LEEK_CANVAS_HEIGHT - 10))
        
        leek_canvas.create_text(text_x_pos, text_y_pos, text=f"{game_height:.0f}",
                               fill="black", font=("Arial", 10, "bold"), anchor="w")

    else: # Initial state or error state - display initial.png
        initial_img_obj = leek_images.get("initial")
        if initial_img_obj:
            # Draw initial image, centered, anchored at its bottom to a position near canvas bottom
            img_center_x = config.LEEK_CANVAS_WIDTH / 2
            # Anchor its bottom slightly above the absolute bottom of the canvas for padding
            img_anchor_y = config.LEEK_CANVAS_HEIGHT - 5 
            leek_canvas.create_image(img_center_x, img_anchor_y,
                                     image=initial_img_obj, anchor='s')
        else: # Fallback for initial image loading failure
             leek_canvas.create_text(config.LEEK_CANVAS_WIDTH / 2, config.LEEK_CANVAS_HEIGHT / 2,
                                text="Initializing...", fill="grey", font=("Arial", 12))
            # Fallback pot drawing logic can be added here if desired


def update_ui_status(status):
    if not status:
        return

    height_var.set(f"{status['height']:.2f}")
    h0_var.set(f"{status['H0']:.2f}")
    game_state_var.set(status['game_state'])

    ct_minus_1 = status.get('Ct-1', 'N/A')
    if isinstance(ct_minus_1, (float, int)):
        ct_minus_1_var.set(f"{ct_minus_1:.2f}")
    else:
        ct_minus_1_var.set(str(ct_minus_1))

    if status['last_kline_time_ms'] and status['last_kline_time_ms'] > 0:
        kline_time_str = datetime.datetime.fromtimestamp(status['last_kline_time_ms'] / 1000).strftime(
            '%H:%M:%S')  # Shorter time format
        last_kline_time_var.set(kline_time_str)
    else:
        last_kline_time_var.set("N/A")

    h, s, l_ = status['color_hsl']
    leek_color_hsl_var.set(f"H:{h:.1f}, S:{s:.1f}, L:{l_:.1f}")

    draw_leek_visualization()  # Update leek drawing

    if status['game_state'] not in ["running", "initializing", "aborted_by_user"]:
        log_message_var.set(f"游戏结束: {status['game_state']}")
        if "won" in status['game_state'] or "lost" in status['game_state']:
            display_nft_data(status)


def update_price_ticker():
    """Fetches and updates the live price display."""
    global price_ticker_update_id, current_monitoring_symbol

    if current_monitoring_symbol and player_leek and (
            player_leek.game_state == "running" or player_leek.game_state == "initializing"):
        ticker_data = api_client.get_current_ticker_data(current_monitoring_symbol)
        if ticker_data:
            current_price_var.set(
                f"{ticker_data['price']:.{get_decimal_places(ticker_data['price'])}f}")  # Dynamic decimal places
            price_change_percent_var.set(f"{ticker_data['price_change_percent']:.2f}%")

            # Change color based on price change
            if ticker_data['price_change_percent'] > 0:
                price_change_percent_label.config(foreground="green")
                current_price_label.config(foreground="green")
            elif ticker_data['price_change_percent'] < 0:
                price_change_percent_label.config(foreground="red")
                current_price_label.config(foreground="red")
            else:
                price_change_percent_label.config(foreground="black")  # Or system default
                current_price_label.config(foreground="black")
        else:
            current_price_var.set("获取失败")
            price_change_percent_var.set("N/A")
            price_change_percent_label.config(foreground="black")
            current_price_label.config(foreground="black")

        price_ticker_update_id = root.after(config.PRICE_TICKER_INTERVAL_SECONDS * 1000, update_price_ticker)
    else:
        # If no symbol or game not running, clear ticker and stop updates for it
        current_price_var.set("N/A")
        price_change_percent_var.set("N/A")
        price_change_percent_label.config(foreground="black")
        current_price_label.config(foreground="black")
        if price_ticker_update_id:
            root.after_cancel(price_ticker_update_id)
            price_ticker_update_id = None


def get_decimal_places(price):
    """Determine appropriate number of decimal places for price display."""
    if price is None: return 2
    if price >= 100: return 2
    if price >= 1: return 4
    if price > 0.0001: return 6
    return 8


def display_nft_data(final_status):
    pot_type_example = "陶瓷花盆"
    purchase_datetime = datetime.datetime.fromtimestamp(final_status['start_time_unix']).strftime('%Y-%m-%d %H:%M:%S')
    nft_data = {
        "韭菜代号": final_status['symbol'], "种植时间": purchase_datetime, "花盆种类": pot_type_example,
        "最终高度": round(final_status['height'], 2), "结束状态": final_status['game_state'],
        "视觉特征": {"颜色HSL": (round(final_status['color_hsl'][0], 1), round(final_status['color_hsl'][1], 1),
                                 round(final_status['color_hsl'][2], 1)),
                     "镰刀标记": final_status['game_state'] == "lost_scythe",
                     "是否开花": "won" in final_status['game_state'] and "height" in final_status[
                         'game_state'] or "fertilizer" in final_status['game_state']}
    }
    nft_str = "\n--- NFT 产出概念 ---\n"
    for key, value in nft_data.items():
        if isinstance(value, dict):
            nft_str += f"{key}:\n"
            for sub_key, sub_value in value.items(): nft_str += f"  {sub_key}: {sub_value}\n"
        else:
            nft_str += f"{key}: {value}\n"
    nft_details_var.set(nft_str)


def game_tick():
    global player_leek, game_update_id

    if player_leek and player_leek.game_state == "running":
        log_message_var.set(f"处理 {player_leek.symbol} 的5分钟K线周期...")
        latest_klines = api_client.get_klines_from_api(player_leek.symbol, config.KLINE_INTERVAL, limit=1)

        if not latest_klines:
            log_message_var.set(
                f"获取K线失败 for {player_leek.symbol}. {config.SIMULATION_SLEEP_INTERVAL_SECONDS}秒后重试。")
            game_update_id = root.after(config.SIMULATION_SLEEP_INTERVAL_SECONDS * 1000, game_tick)
            return

        new_kline = latest_klines[0]
        if new_kline['open_time'] <= player_leek.last_processed_kline_open_time:
            log_message_var.set(f"K线 ({new_kline['open_time']}) 已处理或过时。等待新周期。")
        else:
            player_leek.update_state(new_kline)

        status = player_leek.get_status()
        update_ui_status(status)

        if player_leek.game_state != "running":
            stop_game("游戏逻辑已结束。")  # Will also stop price ticker
            return
        game_update_id = root.after(config.SIMULATION_SLEEP_INTERVAL_SECONDS * 1000, game_tick)
    else:
        if player_leek and player_leek.game_state != "initializing":
            stop_game(f"游戏状态: {player_leek.game_state if player_leek else 'N/A'}")


def initialize_leek_thread(symbol_to_monitor):
    global player_leek, current_monitoring_symbol
    try:
        current_monitoring_symbol = symbol_to_monitor  # Set for price ticker
        log_message_var.set(f"正在初始化 {symbol_to_monitor}...")

        symbol_cfg = config.SYMBOL_SPECIFIC_CONFIG.get(symbol_to_monitor, {})
        base_coeff = symbol_cfg.get("base_coefficient", config.BASE_COEFFICIENT_DEFAULT)
        sensitivity_param = symbol_cfg.get("sensitivity_parameter", config.SENSITIVITY_PARAMETER_DEFAULT)

        player_leek = leek_game.Leek(symbol_to_monitor, base_coeff, sensitivity_param)

        while player_leek.game_state == "initializing": time.sleep(0.1)

        if player_leek.game_state == "running":
            initial_status = player_leek.get_status()
            root.after(0, lambda: update_ui_status(initial_status))
            root.after(0, lambda: log_message_var.set(f"{symbol_to_monitor} 初始化完成。开始监控..."))
            root.after(0, game_tick)
            root.after(0, update_price_ticker)  # Start the price ticker loop
        else:
            root.after(0, lambda: log_message_var.set(f"{symbol_to_monitor} 初始化失败: {player_leek.game_state}"))
            root.after(0, lambda: start_button.config(state=tk.NORMAL))
            current_monitoring_symbol = None  # Clear if init failed

    except Exception as e:
        player_leek = None
        current_monitoring_symbol = None
        root.after(0, lambda: messagebox.showerror("初始化错误", f"初始化时发生错误: {e}"))
        root.after(0, lambda: start_button.config(state=tk.NORMAL))
        root.after(0, lambda: log_message_var.set("初始化失败。"))


def start_game_ui():
    global player_leek, game_update_id, price_ticker_update_id, current_monitoring_symbol

    # Stop any existing game/ticker before starting a new one
    if game_update_id: root.after_cancel(game_update_id); game_update_id = None
    if price_ticker_update_id: root.after_cancel(price_ticker_update_id); price_ticker_update_id = None

    # Reset UI elements for new game
    current_price_var.set("N/A")
    price_change_percent_var.set("N/A")
    height_var.set("N/A")
    h0_var.set("N/A")
    game_state_var.set("未开始")
    ct_minus_1_var.set("N/A")
    last_kline_time_var.set("N/A")
    leek_color_hsl_var.set("H:N/A, S:N/A, L:N/A")
    nft_details_var.set("")
    leek_canvas.delete("all")
    leek_canvas.create_text(config.LEEK_CANVAS_WIDTH / 2, config.LEEK_CANVAS_HEIGHT / 2, text="准备中...", fill="grey")

    symbol_to_monitor = symbol_entry.get().upper()
    if not symbol_to_monitor:
        messagebox.showerror("错误", "请输入加密货币交易对!")
        return

    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

    init_thread = threading.Thread(target=initialize_leek_thread, args=(symbol_to_monitor,), daemon=True)
    init_thread.start()


def stop_game(reason="游戏已手动停止。"):
    global game_update_id, price_ticker_update_id, player_leek, current_monitoring_symbol

    if game_update_id: root.after_cancel(game_update_id); game_update_id = None
    if price_ticker_update_id: root.after_cancel(price_ticker_update_id); price_ticker_update_id = None

    current_monitoring_symbol = None  # Stop price ticker from trying to fetch for this symbol

    if player_leek:
        if player_leek.game_state == "running": player_leek.game_state = "aborted_by_user"
        final_status = player_leek.get_status()
        update_ui_status(final_status)  # Update UI one last time
        if "won" in final_status['game_state'] or "lost" in final_status['game_state'] or final_status[
            'game_state'] == "aborted_by_user":
            display_nft_data(final_status)
    else:  # If player_leek was None or initialization failed
        # Ensure a clean state for visualization if game never fully started or leek is None
        if 'leek_canvas' in globals() and leek_canvas.winfo_exists():  # Check if canvas exists
            draw_leek_visualization()  # Draw empty state if player_leek is None

    log_message_var.set(reason)
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    current_price_var.set("N/A")  # Reset ticker display
    price_change_percent_var.set("N/A")
    price_change_percent_label.config(foreground="black")
    current_price_label.config(foreground="black")


# --- UI Setup ---
root = tk.Tk()
root.title("《韭菜》游戏监控")
root.geometry("800x850")  # Increased window size for canvas

# Load images before creating any image-dependent components
images_loaded_successfully = load_leek_images() # Call to load images

# Main frame
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# Left panel for controls and status
left_panel = ttk.Frame(main_frame)
left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

# Right panel for leek visualization
right_panel = ttk.Frame(main_frame)
right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# --- Input Frame (in left_panel) ---
input_frame = ttk.LabelFrame(left_panel, text="设置")
input_frame.pack(padx=5, pady=5, fill="x")

ttk.Label(input_frame, text="交易对:").pack(side=tk.LEFT, padx=(5, 2), pady=5)
symbol_entry = ttk.Entry(input_frame, width=12)
symbol_entry.pack(side=tk.LEFT, padx=(0, 5), pady=5)
symbol_entry.insert(0, "BTCUSDT")

start_button = ttk.Button(input_frame, text="开始", command=start_game_ui, width=6)
start_button.pack(side=tk.LEFT, padx=5, pady=5)

stop_button = ttk.Button(input_frame, text="停止", command=lambda: stop_game("用户手动停止。"), state=tk.DISABLED,
                         width=6)
stop_button.pack(side=tk.LEFT, padx=5, pady=5)

# --- Price Ticker Frame (in left_panel) ---
ticker_frame = ttk.LabelFrame(left_panel, text="实时行情")
ticker_frame.pack(padx=5, pady=5, fill="x")

current_price_var = tk.StringVar(value="N/A")
price_change_percent_var = tk.StringVar(value="N/A")

ttk.Label(ticker_frame, text="当前价格:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
current_price_label = ttk.Label(ticker_frame, textvariable=current_price_var, font=("TkDefaultFont", 10, "bold"))
current_price_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

ttk.Label(ticker_frame, text="24h涨跌:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
price_change_percent_label = ttk.Label(ticker_frame, textvariable=price_change_percent_var)
price_change_percent_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

# --- Status Frame (in left_panel) ---
status_frame = ttk.LabelFrame(left_panel, text="韭菜游戏状态 (5分钟周期)")
status_frame.pack(padx=5, pady=5, fill="x")
status_frame.columnconfigure(1, weight=1)

height_var = tk.StringVar(value="N/A")
h0_var = tk.StringVar(value="N/A")
game_state_var = tk.StringVar(value="未开始")
ct_minus_1_var = tk.StringVar(value="N/A")
last_kline_time_var = tk.StringVar(value="N/A")
leek_color_hsl_var = tk.StringVar(value="H:N/A, S:N/A, L:N/A")

ttk.Label(status_frame, text="当前高度 (H):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, textvariable=height_var).grid(row=0, column=1, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, text="初始高度 (H₀):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, textvariable=h0_var).grid(row=1, column=1, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, text="游戏状态:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, textvariable=game_state_var).grid(row=2, column=1, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, text="前K线收盘价:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, textvariable=ct_minus_1_var).grid(row=3, column=1, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, text="最后K线时间:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, textvariable=last_kline_time_var).grid(row=4, column=1, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, text="韭菜颜色 (HSL):").grid(row=5, column=0, sticky="w", padx=5, pady=2)
ttk.Label(status_frame, textvariable=leek_color_hsl_var).grid(row=5, column=1, sticky="w", padx=5, pady=2)

# --- Log Frame (in left_panel) ---
log_frame = ttk.LabelFrame(left_panel, text="日志/事件")
log_frame.pack(padx=5, pady=5, fill="x")
log_message_var = tk.StringVar(value="欢迎使用韭菜游戏监控!")
log_label = ttk.Label(log_frame, textvariable=log_message_var, wraplength=300)  # Adjusted wraplength
log_label.pack(padx=5, pady=5, fill="x")

# --- NFT Details Frame (in left_panel) ---
nft_frame = ttk.LabelFrame(left_panel, text="NFT 产出信息")
nft_frame.pack(padx=5, pady=5, fill="both", expand=True)
nft_details_var = tk.StringVar()
nft_label = ttk.Label(nft_frame, textvariable=nft_details_var, anchor="nw", justify=tk.LEFT, wraplength=300)  # Adjusted
nft_label.pack(padx=5, pady=5, fill="both", expand=True)

# --- Leek Visualization Canvas (in right_panel) ---
canvas_frame = ttk.LabelFrame(right_panel, text="韭菜可视化")
canvas_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

leek_canvas = tk.Canvas(canvas_frame, width=config.LEEK_CANVAS_WIDTH, height=config.LEEK_CANVAS_HEIGHT, bg="lightgrey")
leek_canvas.pack(pady=10, padx=10, anchor="center")
draw_leek_visualization()  # Initial draw (placeholder)


def on_closing():
    if messagebox.askokcancel("退出", "确定要退出吗? 当前监控将停止。"):
        stop_game("窗口关闭，游戏停止。")
        root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
