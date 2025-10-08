from nicegui import ui
from typing import Dict, List, Union
from .sections import create_global_stats, create_rankings, create_player_lookup
from .stats import load_data, calculate_player_stats, leaderboard_tables, get_unique_players, clear_cache, get_cache_age

@ui.page("/")
def main_page() -> None:
    def refresh_data():
        clear_cache()
        ui.open("/")

    # Header with title and refresh button
    with ui.row().classes("w-full items-center justify-between mb-4"):
        ui.label("🎴 Tractor Stats Dashboard").classes("text-h3")
        with ui.row().classes("items-center gap-2"):
            cache_age = get_cache_age()
            if cache_age:
                ui.label(f"Last updated: {cache_age}").classes("text-sm text-gray-600")
            ui.button("🔄 Refresh Data", on_click=refresh_data).classes("bg-blue-500")

    df = load_data()
    if "Error" in df.columns:
        ui.label("⚠️ Could not load data. Check Google Sheets link.")
        return

    players_list = get_unique_players(df)

    df_2decks = df[df['# decks'] == 2].copy()
    df_3decks = df[df['# decks'] == 3].copy()

    player_stats_2decks = {p: calculate_player_stats(p, df_2decks) for p in players_list}
    player_stats_3decks = {p: calculate_player_stats(p, df_3decks) for p in players_list}

    lb2 = leaderboard_tables(player_stats_2decks, "2-Deck")
    lb3 = leaderboard_tables(player_stats_3decks, "3-Deck")

    create_global_stats(df_2decks, df_3decks)
    create_rankings(lb2, lb3, player_stats_2decks, player_stats_3decks)
    create_player_lookup(players_list, player_stats_2decks, player_stats_3decks, df_2decks, df_3decks)

ui.run(
    host="0.0.0.0",
    port=7860,
    reload=True
)