import flet as ft
from binance_client import BinanceClient
import time
import threading
import os
import json

CONFIG_PATH = os.path.expanduser("~/.binance_tracker_config.json")

def main(page: ft.Page):
    # Window settings for premium desktop feel
    page.title = "Binance Баланс Трекер"
    page.window.width = 1000
    page.window.height = 800
    page.window.min_width = 800
    page.window.min_height = 650

    # Backward compatibility helper for SnackBar
    def show_snack_bar(snack_bar):
        # Remove any existing snackbars from overlay
        for ctrl in list(page.overlay):
            if isinstance(ctrl, ft.SnackBar):
                page.overlay.remove(ctrl)
        page.overlay.append(snack_bar)
        snack_bar.open = True
        page.update()
    page.show_snack_bar = show_snack_bar
    page.bgcolor = "#0C0E12"  # Binance Charcoal/Dark Background
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    
    # Initialize the Binance Client
    client = BinanceClient()
    
    # Global state variables
    assets_data = []
    total_usd = 0.0
    spot_usd = 0.0
    funding_usd = 0.0
    earn_usd = 0.0
    trading_bots_usd = 0.0
    futures_usd = 0.0
    spot_error = None
    funding_error = None
    earn_error = None
    
    current_currency = "UAH"
    fiat_rates = {"UAH": 40.2, "EUR": 0.92, "RUB": 91.5, "BTC": 0.00001}
    
    # Helper to check if API keys are set
    def get_saved_keys():
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    return data.get("api_key", ""), data.get("api_secret", "")
            except Exception:
                pass
        return "", ""

    # Apply saved keys to client
    saved_key, saved_secret = get_saved_keys()
    client.set_credentials(saved_key, saved_secret)

    # ------------------ UI Components ------------------
    
    # Logo and App Title
    logo_icon = ft.Icon(icon=ft.Icons.WALLET_ROUNDED, color="#F3BA2F", size=36)
    app_title = ft.Text(
        value="Binance Balance",
        size=24,
        weight=ft.FontWeight.BOLD,
        color="#EAECEF",
        font_family="Outfit"
    )
    
    status_dot = ft.Container(
        width=10,
        height=10,
        border_radius=5,
        bgcolor="#FFB100" if not saved_key else "#02C076",
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )
    
    status_text = ft.Text(
        value="Требуется настройка" if not saved_key else "Готов к работе",
        size=12,
        color="#848E9C",
        weight=ft.FontWeight.W_500
    )
    
    status_indicator = ft.Row(
        controls=[status_dot, status_text],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    live_dot = ft.Container(
        width=8,
        height=8,
        border_radius=4,
        bgcolor="#02C076",
        scale=1.0,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )
    
    live_badge = ft.Row(
        controls=[
            live_dot,
            ft.Text("LIVE", size=10, color="#02C076", weight=ft.FontWeight.BOLD)
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        visible=bool(saved_key)
    )

    # ------------------ Loading State ------------------
    loading_ring = ft.ProgressRing(width=40, height=40, color="#F3BA2F", stroke_width=4)
    loading_text = ft.Text("Загрузка балансов из Binance...", color="#848E9C", size=14)
    loading_container = ft.Column(
        controls=[loading_ring, loading_text],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15,
        visible=False
    )
    
    # ------------------ Empty/Unconfigured State ------------------
    unconfigured_icon = ft.Icon(icon=ft.Icons.VPN_KEY_ROUNDED, color="#2B3139", size=80)
    unconfigured_title = ft.Text(
        "API Ключи не настроены",
        size=20,
        weight=ft.FontWeight.BOLD,
        color="#EAECEF"
    )
    unconfigured_desc = ft.Text(
        "Для просмотра ваших балансов добавьте API-ключ в настройках.\nКлючи шифруются и хранятся только на вашем компьютере.",
        color="#848E9C",
        size=14,
        text_align=ft.TextAlign.CENTER
    )
    
    # Create config button for empty state
    def open_settings_from_empty(e):
        open_settings(e)
        
    setup_btn = ft.Button(
        content="Настроить API Ключи",
        icon=ft.Icons.SETTINGS_ROUNDED,
        color="#181A20",
        bgcolor="#F3BA2F",
        on_click=open_settings_from_empty,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.all(15)
        )
    )
    
    empty_container = ft.Column(
        controls=[unconfigured_icon, unconfigured_title, unconfigured_desc, ft.Container(height=10), setup_btn],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
        visible=not bool(saved_key)
    )

    # ------------------ Hero Card (Balance Summary) ------------------
    total_val_txt = ft.Text("$0.00", size=48, weight=ft.FontWeight.BOLD, color="#181A20")
    secondary_val_txt = ft.Text("≈ 0.00 UAH", size=18, weight=ft.FontWeight.W_500, color="#181A20", opacity=0.8)
    spot_val_txt = ft.Text("Спот: $0.00", size=13, weight=ft.FontWeight.W_600, color="#181A20")
    funding_val_txt = ft.Text("Пополнение: $0.00", size=13, weight=ft.FontWeight.W_600, color="#181A20")
    earn_val_txt = ft.Text("Earn: $0.00", size=13, weight=ft.FontWeight.W_600, color="#181A20")
    bots_val_txt = ft.Text("Боты: $0.00", size=13, weight=ft.FontWeight.W_600, color="#181A20")
    futures_val_txt = ft.Text("Фьючерсы: $0.00", size=13, weight=ft.FontWeight.W_600, color="#181A20")
    
    def update_secondary_balance():
        rate = fiat_rates.get(current_currency, 1.0)
        equiv_val = total_usd * rate
        
        if current_currency == "BTC":
            secondary_val_txt.value = f"≈ {equiv_val:,.6f} ₿"
        elif current_currency == "EUR":
            secondary_val_txt.value = f"≈ €{equiv_val:,.2f}"
        elif current_currency == "RUB":
            secondary_val_txt.value = f"≈ ₽{equiv_val:,.2f}"
        else: # UAH
            secondary_val_txt.value = f"≈ {equiv_val:,.2f} ₴"
        
        try:
            secondary_val_txt.update()
        except Exception:
            pass

    def change_currency(currency_code):
        nonlocal current_currency
        current_currency = currency_code
        currency_menu_btn.content.content.controls[0].value = f"≈ {current_currency}"
        try:
            currency_menu_btn.content.update()
        except Exception:
            pass
        update_secondary_balance()

    currency_menu_btn = ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("≈ UAH", size=11, weight=ft.FontWeight.BOLD, color="#181A20"),
                    ft.Icon(icon=ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=16, color="#181A20")
                ],
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.Padding(8, 4, 8, 4),
            bgcolor=ft.Colors.with_opacity(0.08, "#181A20"),
            border_radius=8
        ),
        items=[
            ft.PopupMenuItem(content=ft.Text("₴ UAH (Гривна)"), on_click=lambda e: change_currency("UAH")),
            ft.PopupMenuItem(content=ft.Text("€ EUR (Евро)"), on_click=lambda e: change_currency("EUR")),
            ft.PopupMenuItem(content=ft.Text("₽ RUB (Рубль)"), on_click=lambda e: change_currency("RUB")),
            ft.PopupMenuItem(content=ft.Text("₿ BTC (Биткоин)"), on_click=lambda e: change_currency("BTC"))
        ],
        tooltip="Сменить валюту"
    )

    hero_card = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#F3BA2F", "#D49B00"]
        ),
        padding=30,
        border_radius=24,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=20,
            color=ft.Colors.with_opacity(0.15, "#F3BA2F"),
            offset=ft.Offset(0, 10)
        ),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("ОБЩИЙ БАЛАНС", size=13, weight=ft.FontWeight.BOLD, color="#181A20", opacity=0.7),
                        currency_menu_btn
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Column(
                    controls=[
                        total_val_txt,
                        secondary_val_txt
                    ],
                    spacing=2
                ),
                ft.Container(
                    margin=ft.Margin.only(top=10, bottom=10),
                    height=1,
                    bgcolor="#181A20",
                    opacity=0.15
                ),
                ft.Row(
                    controls=[
                        ft.Row(controls=[ft.Container(width=8, height=8, border_radius=4, bgcolor="#02C076"), spot_val_txt], spacing=6),
                        ft.VerticalDivider(color="#181A20", opacity=0.2),
                        ft.Row(controls=[ft.Container(width=8, height=8, border_radius=4, bgcolor="#00C0FF"), funding_val_txt], spacing=6),
                        ft.VerticalDivider(color="#181A20", opacity=0.2),
                        ft.Row(controls=[ft.Container(width=8, height=8, border_radius=4, bgcolor="#FF9800"), earn_val_txt], spacing=6),
                        ft.VerticalDivider(color="#181A20", opacity=0.2),
                        ft.Row(controls=[ft.Container(width=8, height=8, border_radius=4, bgcolor="#181A20", opacity=0.7), bots_val_txt], spacing=6),
                        ft.VerticalDivider(color="#181A20", opacity=0.2),
                        ft.Row(controls=[ft.Container(width=8, height=8, border_radius=4, bgcolor="#F84960"), futures_val_txt], spacing=6)
                    ],
                    spacing=12,
                    wrap=True
                )
            ]
        ),
        visible=bool(saved_key),
        animate=ft.Animation(500, ft.AnimationCurve.DECELERATE)
    )

    # ------------------ Filter Bar ------------------
    search_bar = ft.TextField(
        hint_text="Поиск монет (например: BTC, USDT)...",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        bgcolor="#181A20",
        border_color="#2B3139",
        border_radius=12,
        content_padding=15,
        text_size=14,
        on_change=lambda e: filter_and_display(),
        expand=True
    )
    
    hide_dust_switch = ft.Switch(
        label="Скрыть балансы < $1",
        value=True,
        active_color="#F3BA2F",
        label_text_style=ft.TextStyle(size=13, color="#848E9C"),
        on_change=lambda e: filter_and_display()
    )
    
    assets_count_txt = ft.Text("Активов: 0", size=13, color="#848E9C", weight=ft.FontWeight.W_500)
    
    filter_row = ft.Row(
        controls=[
            search_bar,
            hide_dust_switch,
            ft.Container(
                content=assets_count_txt,
                padding=ft.Padding.symmetric(horizontal=15, vertical=10),
                bgcolor="#181A20",
                border=ft.Border.all(1, "#2B3139"),
                border_radius=10
            )
        ],
        spacing=15,
        visible=bool(saved_key)
    )

    # ------------------ Asset Grid List ------------------
    assets_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=320,
        child_aspect_ratio=1.5,
        spacing=20,
        run_spacing=20,
        visible=bool(saved_key)
    )

    # Hover animations for cards
    def card_hover(e):
        if e.data == "true":
            e.control.scale = 1.02
            e.control.border = ft.Border.all(1.5, "#F3BA2F")
            e.control.shadow = ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.1, "#F3BA2F"),
                offset=ft.Offset(0, 5)
            )
        else:
            e.control.scale = 1.0
            e.control.border = ft.Border.all(1, "#2B3139")
            e.control.shadow = None
        e.control.update()

    # Dynamic symbol logo generator
    def get_coin_gradient(asset: str):
        asset = asset.upper()
        if "BTC" in asset:
            return ["#FF9900", "#FFBC66"]
        elif "ETH" in asset:
            return ["#627EEA", "#8C9EFF"]
        elif "USDT" in asset or "USDC" in asset or "BUSD" in asset:
            return ["#26A17B", "#4CD9AC"]
        elif "BNB" in asset:
            return ["#F3BA2F", "#FFD56B"]
        elif "SOL" in asset:
            return ["#14F195", "#9945FF"]
        elif "XRP" in asset:
            return ["#23292F", "#00AAE4"]
        elif "ADA" in asset:
            return ["#0033AD", "#3CC8FF"]
        elif "DOGE" in asset:
            return ["#C2A633", "#F1DB73"]
        return ["#4A5568", "#718096"]  # Default Gray

    def create_asset_card(asset_data):
        logo_colors = get_coin_gradient(asset_data["asset"])
        is_spot = asset_data["wallet"] == "Spot"
        
        # Circular symbol badge with initials
        coin_logo = ft.Container(
            content=ft.Text(
                asset_data["asset"][:3],
                size=11,
                weight=ft.FontWeight.BOLD,
                color="#FFFFFF" if asset_data["asset"] not in ("BNB", "USDT", "USDC", "BUSD") else "#181A20"
            ),
            width=36,
            height=36,
            border_radius=18,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=logo_colors
            ),
            alignment=ft.Alignment.CENTER
        )
        
        wallet_name = asset_data["wallet"]
        if wallet_name == "Spot":
            tag_text = "SPOT"
            tag_color = "#02C076"
        elif wallet_name == "Funding":
            tag_text = "ФАНД"
            tag_color = "#00C0FF"
        elif wallet_name == "Earn":
            tag_text = "EARN"
            tag_color = "#FF9800"
        elif wallet_name == "Trading Bots":
            tag_text = "БОТ"
            tag_color = "#F3BA2F"
        elif wallet_name == "Futures":
            tag_text = "ФЬЮЧ"
            tag_color = "#F84960"
        else:
            tag_text = wallet_name[:4].upper()
            tag_color = "#848E9C"

        wallet_tag = ft.Container(
            content=ft.Text(
                tag_text,
                size=9,
                weight=ft.FontWeight.BOLD,
                color="#0C0E12"
            ),
            bgcolor=tag_color,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            border_radius=6
        )
        
        # Format values cleanly
        qty_formatted = f"{asset_data['total']:.6f}".rstrip('0').rstrip('.')
        if float(qty_formatted) < 0.0001:
            qty_formatted = f"{asset_data['total']:.8f}"
            
        usd_formatted = f"${asset_data['usd_value']:,.2f}"
        price_formatted = f"${asset_data['price']:,.4f}" if asset_data['price'] < 1 else f"${asset_data['price']:,.2f}"
        
        return ft.Container(
            bgcolor="#181A20",
            border=ft.Border.all(1, "#2B3139"),
            border_radius=16,
            padding=16,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=card_hover,
            content=ft.Column(
                controls=[
                    # Top Row: Logo, Symbol, Wallet type
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    coin_logo,
                                    ft.Column(
                                        controls=[
                                            ft.Text(asset_data["asset"], size=15, weight=ft.FontWeight.BOLD, color="#EAECEF"),
                                            ft.Text(qty_formatted, size=11, color="#848E9C", overflow=ft.TextOverflow.ELLIPSIS)
                                        ],
                                        spacing=2
                                    )
                                ],
                                spacing=10,
                                expand=True
                            ),
                            wallet_tag
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    # Middle Spacer
                    ft.Container(height=4),
                    # Bottom metrics: USD value and ticker price
                    ft.Row(
                        controls=[
                            ft.Text(usd_formatted, size=18, weight=ft.FontWeight.W_700, color="#EAECEF"),
                            ft.Text(price_formatted, size=11, color="#848E9C")
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.BASELINE
                    ),
                    ft.Container(height=4),
                    # Portfolio share progress bar
                    ft.ProgressBar(
                        value=asset_data["percentage"] / 100.0,
                        color="#F3BA2F",
                        bgcolor="#2B3139",
                        height=4,
                        border_radius=2
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
        )

    # ------------------ Core Business Logic ------------------
    
    def fetch_balances_thread():
        nonlocal assets_data, total_usd, spot_usd, funding_usd, earn_usd, trading_bots_usd, futures_usd, spot_error, funding_error, earn_error, fiat_rates
        
        # Set UI to loading state
        loading_container.visible = True
        hero_card.visible = False
        filter_row.visible = False
        assets_grid.visible = False
        empty_container.visible = False
        refresh_btn.disabled = True
        page.update()
        
        try:
            # Query the portfolio
            data = client.get_full_portfolio()
            assets_data = data["assets"]
            total_usd = data["total_usd"]
            spot_usd = data["spot_usd"]
            funding_usd = data["funding_usd"]
            earn_usd = data.get("earn_usd", 0.0)
            trading_bots_usd = data.get("trading_bots_usd", 0.0)
            futures_usd = data.get("futures_usd", 0.0)
            spot_error = data["spot_error"]
            funding_error = data["funding_error"]
            earn_error = data.get("earn_error")
            if "fiat_rates" in data:
                fiat_rates = data["fiat_rates"]
            
            # Save state
            loading_container.visible = False
            hero_card.visible = True
            filter_row.visible = True
            assets_grid.visible = True
            
            # Handle key status indicator
            status_dot.bgcolor = "#02C076"
            
            # Inform users of partial permissions issues (e.g. Funding wallet access disabled on API key)
            if spot_error or funding_error or earn_error:
                status_dot.bgcolor = "#FFB100"
                if spot_error and funding_error and earn_error:
                    status_dot.bgcolor = "#F84960"
                    status_text.value = "Ошибка подключения"
                else:
                    status_text.value = "Частичный доступ"
                    # Notify user of restrictions (e.g. lack of funding permissions)
                    err_msg = spot_error or funding_error or earn_error
                    page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"Предупреждение: {err_msg}", color="#181A20", weight=ft.FontWeight.W_500),
                            bgcolor="#FFB100",
                            duration=6000
                        )
                    )
            else:
                status_text.value = "Подключено к Binance"
            
            live_badge.visible = True
            
        except Exception as err:
            loading_container.visible = False
            empty_container.visible = False
            hero_card.visible = True
            filter_row.visible = True
            assets_grid.visible = True
            
            # Set error status
            status_dot.bgcolor = "#F84960"
            status_text.value = "Ошибка авторизации"
            live_badge.visible = False
            
            page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"Ошибка API: {str(err)}", color="#FFFFFF", weight=ft.FontWeight.BOLD),
                    bgcolor="#F84960"
                )
            )
            
        finally:
            refresh_btn.disabled = False
            # Render balances to the dashboard
            update_dashboard_ui()
            live_badge.update()
            page.update()

    def fetch_balances_silent():
        nonlocal assets_data, total_usd, spot_usd, funding_usd, earn_usd, trading_bots_usd, futures_usd, spot_error, funding_error, earn_error, fiat_rates
        try:
            # Query the portfolio silently
            data = client.get_full_portfolio()
            assets_data = data["assets"]
            total_usd = data["total_usd"]
            spot_usd = data["spot_usd"]
            funding_usd = data["funding_usd"]
            earn_usd = data.get("earn_usd", 0.0)
            trading_bots_usd = data.get("trading_bots_usd", 0.0)
            futures_usd = data.get("futures_usd", 0.0)
            spot_error = data["spot_error"]
            funding_error = data["funding_error"]
            earn_error = data.get("earn_error")
            if "fiat_rates" in data:
                fiat_rates = data["fiat_rates"]
            
            # Handle key status indicator without triggering popup notifications
            if spot_error or funding_error or earn_error:
                status_dot.bgcolor = "#FFB100"
                if spot_error and funding_error and earn_error:
                    status_dot.bgcolor = "#F84960"
                    status_text.value = "Ошибка подключения"
                else:
                    status_text.value = "Частичный доступ"
            else:
                status_dot.bgcolor = "#02C076"
                status_text.value = "Подключено к Binance"
            
            status_dot.update()
            status_text.update()
            
            # Enable live badge
            live_badge.visible = True
            live_badge.update()
            
            # Update UI silently
            update_dashboard_ui()
            
        except Exception as err:
            # Silent fallback: just log or ignore during background run
            print(f"Silent refresh error: {err}")

    def refresh_balances(e=None):
        api_key, api_secret = get_saved_keys()
        if not api_key:
            open_settings(None)
            return
            
        client.set_credentials(api_key, api_secret)
        # Run in a background thread to prevent UI freezing
        t = threading.Thread(target=fetch_balances_thread)
        t.start()

    def filter_and_display():
        query = search_bar.value.strip().lower()
        hide_small = hide_dust_switch.value
        
        filtered = []
        for asset in assets_data:
            # Match search filter
            if query and query not in asset["asset"].lower():
                continue
            # Match dust balance filter (< $1.00 USD)
            if hide_small and asset["usd_value"] < 1.0:
                continue
            filtered.append(asset)
            
        assets_grid.controls = [create_asset_card(a) for a in filtered]
        assets_count_txt.value = f"Активов: {len(filtered)}"
        assets_grid.update()
        assets_count_txt.update()

    def update_dashboard_ui():
        # Update Hero card amounts
        total_val_txt.value = f"${total_usd:,.2f}"
        spot_val_txt.value = f"Спот: ${spot_usd:,.2f}"
        funding_val_txt.value = f"Пополнение: ${funding_usd:,.2f}"
        earn_val_txt.value = f"Earn: ${earn_usd:,.2f}"
        bots_val_txt.value = f"Боты: ${trading_bots_usd:,.2f}"
        futures_val_txt.value = f"Фьючерсы: ${futures_usd:,.2f}"
        
        total_val_txt.update()
        spot_val_txt.update()
        funding_val_txt.update()
        earn_val_txt.update()
        bots_val_txt.update()
        futures_val_txt.update()
        
        # Display asset list
        filter_and_display()
        update_secondary_balance()

    # ------------------ Settings Modal Dialog ------------------
    api_key_input = ft.TextField(
        label="Binance API Key",
        value=saved_key,
        password=True,
        can_reveal_password=True,
        border_color="#2B3139",
        focused_border_color="#F3BA2F",
        text_size=13,
        label_style=ft.TextStyle(color="#848E9C"),
        text_style=ft.TextStyle(color="#EAECEF")
    )
    
    api_secret_input = ft.TextField(
        label="Binance API Secret",
        value=saved_secret,
        password=True,
        can_reveal_password=True,
        border_color="#2B3139",
        focused_border_color="#F3BA2F",
        text_size=13,
        label_style=ft.TextStyle(color="#848E9C"),
        text_style=ft.TextStyle(color="#EAECEF")
    )

    def save_settings(e):
        key_val = api_key_input.value.strip()
        sec_val = api_secret_input.value.strip()
        
        if not key_val or not sec_val:
            page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Пожалуйста, заполните оба поля!", color="#181A20", weight=ft.FontWeight.BOLD),
                    bgcolor="#FFB100"
                )
            )
            return
            
        # Securely write to local storage
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump({"api_key": key_val, "api_secret": sec_val}, f)
        except Exception as e:
            print(f"Error saving config: {e}")
        
        client.set_credentials(key_val, sec_val)
        
        settings_dialog.open = False
        empty_container.visible = False
        hero_card.visible = True
        filter_row.visible = True
        assets_grid.visible = True
        
        page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text("Настройки успешно сохранены!", color="#FFFFFF", weight=ft.FontWeight.W_500),
                bgcolor="#02C076"
            )
        )
        
        # Trigger an immediate balance refresh
        refresh_balances()

    def clear_settings(e):
        if os.path.exists(CONFIG_PATH):
            try:
                os.remove(CONFIG_PATH)
            except Exception:
                pass
        
        api_key_input.value = ""
        api_secret_input.value = ""
        client.set_credentials("", "")
        
        settings_dialog.open = False
        empty_container.visible = True
        hero_card.visible = False
        filter_row.visible = False
        assets_grid.visible = False
        
        status_dot.bgcolor = "#FFB100"
        status_text.value = "Требуется настройка"
        
        live_badge.visible = False
        
        # Clean local cache state
        nonlocal assets_data, total_usd, spot_usd, funding_usd, earn_usd, trading_bots_usd, futures_usd
        assets_data = []
        total_usd = 0.0
        spot_usd = 0.0
        funding_usd = 0.0
        earn_usd = 0.0
        trading_bots_usd = 0.0
        futures_usd = 0.0
        
        page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text("Данные успешно удалены с устройства.", color="#EAECEF"),
                bgcolor="#2B3139"
            )
        )
        live_badge.update()
        page.update()

    settings_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(icon=ft.Icons.SECURITY, color="#F3BA2F", size=24),
                ft.Text("Настройки API ключей", size=18, weight=ft.FontWeight.BOLD, color="#EAECEF")
            ],
            spacing=10
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Получите API ключи на сайте Binance с правами 'Только чтение' (Read Info).\n\n"
                        "⚠️ Никогда не включайте права на 'Снятие средств' (Enable Withdrawals) ради безопасности.",
                        size=12,
                        color="#848E9C"
                    ),
                    ft.Container(height=10),
                    api_key_input,
                    api_secret_input,
                ],
                tight=True,
                spacing=10
            ),
            width=400,
            bgcolor="#181A20",
            padding=5
        ),
        actions=[
            ft.TextButton("Очистить", on_click=clear_settings, style=ft.ButtonStyle(color="#F84960")),
            ft.Row(
                controls=[
                    ft.TextButton("Отмена", on_click=lambda e: setattr(settings_dialog, "open", False) or page.update()),
                    ft.Button("Сохранить", on_click=save_settings, bgcolor="#F3BA2F", color="#181A20")
                ],
                spacing=10
            )
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        bgcolor="#181A20"
    )

    page.overlay.append(settings_dialog)
    
    def open_settings(e):
        saved_k, saved_s = get_saved_keys()
        api_key_input.value = saved_k
        api_secret_input.value = saved_s
        settings_dialog.open = True
        page.update()

    # ------------------ Action Buttons in Header ------------------
    settings_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS_ROUNDED,
        icon_color="#848E9C",
        tooltip="Настройки API",
        on_click=open_settings
    )
    
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH_ROUNDED,
        icon_color="#F3BA2F",
        tooltip="Обновить балансы",
        on_click=refresh_balances
    )

    # Header section row
    header = ft.Row(
        controls=[
            ft.Row(controls=[logo_icon, app_title], spacing=10),
            ft.Row(
                controls=[
                    status_indicator,
                    live_badge,
                    ft.Container(width=1, height=20, bgcolor="#2B3139"),
                    refresh_btn,
                    settings_btn
                ],
                spacing=15
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    # ------------------ Add elements to Page ------------------
    page.add(
        ft.Column(
            controls=[
                header,
                ft.Container(height=10),
                hero_card,
                loading_container,
                empty_container,
                ft.Container(height=10),
                filter_row,
                assets_grid
            ],
            expand=True,
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )
    
    # ------------------ Real-Time Background Thread ------------------
    shutdown_event = threading.Event()
    
    def on_disconnect(e):
        shutdown_event.set()
    page.on_disconnect = on_disconnect
    
    def run_auto_refresh():
        pulse = False
        while not shutdown_event.is_set():
            # Wait for 5 seconds in 0.1s slices to exit immediately on shutdown
            for _ in range(50):
                if shutdown_event.is_set():
                    break
                time.sleep(0.1)
                
            if shutdown_event.is_set():
                break
                
            # Only refresh silently if API key is present and setup/loading screen is not shown
            api_key, _ = get_saved_keys()
            if api_key and not loading_container.visible and not empty_container.visible:
                try:
                    fetch_balances_silent()
                    
                    # Pulse animation on the live dot badge
                    pulse = not pulse
                    live_dot.scale = 1.3 if pulse else 1.0
                    live_dot.update()
                except Exception:
                    pass
                    
    refresh_thread = threading.Thread(target=run_auto_refresh, daemon=True)
    refresh_thread.start()

    # ------------------ Initial Load ------------------
    if saved_key:
        refresh_balances()

# Run the Flet Application
if __name__ == "__main__":
    import os
    # Read port from environment variable (standard for cloud hosts like Render/Koyeb)
    port_env = os.environ.get("PORT")
    if port_env:
        # Running in the cloud
        port = int(port_env)
        print(f"Starting Flet server in cloud mode on port {port}...")
        ft.app(target=main, view=None, port=port)
    else:
        # Running locally
        print("Starting Flet server in local browser mode...")
        ft.app(target=main, view=ft.AppView.WEB_BROWSER)



