import pandas as pd
from typing import Dict, List, Tuple, Any, Union, Optional
from datetime import datetime, timedelta

from .constants import ATTACKING_PLAYER_COLS, DEFENDING_PLAYER_COLS, ALL_PLAYER_COLS, DEALER_COL, MIN_SAMPLE_SIZE

# Cache for data
_cache = {
    'data': None,
    'timestamp': None,
    'cache_duration': timedelta(minutes=5)
}

def get_level_change_value(result: Any) -> int:
    """Convert game result to level change value"""
    if pd.isna(result):
        return 0
    
    result = str(result).strip()
    
    if result == 'Draw':
        return 0
    elif result.startswith('A+'):
        try:
            return int(result[2:])
        except (ValueError, IndexError):
            return 0
    elif result.startswith('D+'):
        try:
            return -int(result[2:])
        except (ValueError, IndexError):
            return 0
    else:
        return 0

def load_data(force_refresh: bool = False) -> pd.DataFrame:
    """Load data from Google Sheets with caching

    Args:
        force_refresh: If True, bypass cache and force a fresh load
    """
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKJVlAjGE_TRXpBGIvUR-po05xTuBCV2chd5B76hdvVItNpP1qMNgfLCVMBwj5gCsvjhDS9A87Kgoi/pub?gid=0&single=true&output=csv"

    # Check if cache is valid
    if not force_refresh and _cache['data'] is not None and _cache['timestamp'] is not None:
        time_since_cache = datetime.now() - _cache['timestamp']
        if time_since_cache < _cache['cache_duration']:
            return _cache['data']

    # Cache is invalid or force refresh - fetch new data
    try:
        df = pd.read_csv(URL)
        _cache['data'] = df
        _cache['timestamp'] = datetime.now()
        return df
    except Exception as e:
        # If fetch fails but we have cached data, return it
        if _cache['data'] is not None:
            return _cache['data']
        return pd.DataFrame({"Error": [str(e)]})

def clear_cache() -> None:
    """Clear the data cache to force a fresh load on next request"""
    _cache['data'] = None
    _cache['timestamp'] = None

def calculate_player_stats(player_name: str, df: pd.DataFrame) -> Dict[str, Union[float, int]]:
    defending_other_columns = DEFENDING_PLAYER_COLS[1:]  # D2, D3, D4 (not dealer)

    df_player = df[df[ALL_PLAYER_COLS].apply(lambda row: player_name in row.values, axis=1)].copy()

    # Attacking stats
    df_attacking_games = df_player[df_player[ATTACKING_PLAYER_COLS].apply(lambda row: player_name in row.values, axis=1)]
    average_attacking_points = df_attacking_games['Points'].mean() if not df_attacking_games.empty else 0
    attacking_sample_size = len(df_attacking_games)

    # Defending stats (all defenders)
    df_defending_games = df_player[df_player[DEFENDING_PLAYER_COLS].apply(lambda row: player_name in row.values, axis=1)]
    average_defending_points = df_defending_games['Points'].mean() if not df_defending_games.empty else 0
    defending_sample_size = len(df_defending_games)

    # Defending stats (not dealer)
    df_defending_other_games = df_player[df_player[defending_other_columns].apply(lambda row: player_name in row.values, axis=1)]
    average_defending_other_points = df_defending_other_games['Points'].mean() if not df_defending_other_games.empty else 0
    defending_other_sample_size = len(df_defending_other_games)

    # Defending stats (dealer)
    df_defending_d1_games = df_player[df_player[DEALER_COL] == player_name]
    average_defending_d1_points = df_defending_d1_games['Points'].mean() if not df_defending_d1_games.empty else 0
    defending_d1_sample_size = len(df_defending_d1_games)

    # Level change
    def calculate_game_level_change(row: pd.Series, player: str) -> int:
        result = row['Result']
        level_change = get_level_change_value(result)
        
        if player in row[ATTACKING_PLAYER_COLS].values:
            return level_change
        elif player in row[DEFENDING_PLAYER_COLS].values:
            return -level_change
        return 0

    df_player['level_change'] = df_player.apply(lambda row: calculate_game_level_change(row, player_name), axis=1)
    average_level_change = df_player['level_change'].mean() if not df_player.empty else 0
    level_change_sample_size = len(df_player)

    return {
        'avg. collected when attacking': average_attacking_points,
        'attacking sample size': attacking_sample_size,
        'avg. opponents collected when defending': average_defending_points,
        'defending sample size': defending_sample_size,
        'avg. opponents collected defending (teammate)': average_defending_other_points,
        'defending teammate sample size': defending_other_sample_size,
        'avg. opponents collected defending (dealer)': average_defending_d1_points,
        'defending dealer sample size': defending_d1_sample_size,
        'avg. level change': average_level_change,
        'level change sample size': level_change_sample_size
    }

def leaderboard_tables(player_stats_dict: Dict[str, Dict[str, Union[float, int]]], title_prefix: str) -> Dict[str, pd.DataFrame]:
    """Return a dict of sorted DataFrames for leaderboards (sample size ≥5)."""
    df_stats = pd.DataFrame.from_dict(player_stats_dict, orient="index")

    configs = [
        ("avg. collected when attacking", "attacking sample size", False),
        ("avg. opponents collected when defending", "defending sample size", True),
        ("avg. opponents collected defending (teammate)", "defending teammate sample size", True),
        ("avg. opponents collected defending (dealer)", "defending dealer sample size", True),
        ("avg. level change", "level change sample size", False),
    ]

    results = {}
    for metric, sample_col, ascending in configs:
        df_filtered = df_stats[df_stats[sample_col] >= MIN_SAMPLE_SIZE].copy()
        if df_filtered.empty:
            continue
        df_sorted = df_filtered[[metric, sample_col]].sort_values(by=metric, ascending=ascending)
        # format points/level change to 3 decimals
        if df_sorted[metric].dtype.kind in "fc":
            df_sorted[metric] = df_sorted[metric].round(3)
        df_sorted = df_sorted.reset_index().rename(columns={"index": "Player"})
        df_sorted.insert(0, 'Rank', range(1, len(df_sorted) + 1))
        results[metric] = df_sorted
    return results

def get_unique_players(df: pd.DataFrame) -> List[str]:
    """Extract unique players from the dataframe"""
    unique_players = pd.unique(df[ALL_PLAYER_COLS].values.ravel())
    return [p for p in unique_players if pd.notna(p)]

def calculate_teammate_opponent_stats(player_name: str, df: pd.DataFrame, min_games: int = MIN_SAMPLE_SIZE) -> Tuple[Dict[str, Dict[str, Union[float, int]]], Dict[str, Dict[str, Union[float, int]]]]:
    """Calculate how other players perform as teammates and opponents"""
    # Get all games where the selected player participated
    player_games = df[df[ALL_PLAYER_COLS].apply(lambda row: player_name in row.values, axis=1)].copy()
    
    if player_games.empty:
        return {}, {}
    
    def get_level_change(row: pd.Series, player: str) -> int:
        result = row['Result']
        level_change = get_level_change_value(result)
        
        if player in row[ATTACKING_PLAYER_COLS].values:
            return level_change
        elif player in row[DEFENDING_PLAYER_COLS].values:
            return -level_change
        return 0
    
    teammate_stats = {}
    opponent_stats = {}
    
    # Get all unique players except the selected one
    all_players = set()
    for col in ALL_PLAYER_COLS:
        all_players.update(player_games[col].dropna().unique())
    all_players.discard(player_name)
    
    for other_player in all_players:
        teammate_games = []
        opponent_games = []
        
        for _, game in player_games.iterrows():
            # Find where each player is positioned
            player_pos = None
            other_pos = None
            
            for col in ALL_PLAYER_COLS:
                if game[col] == player_name:
                    player_pos = col
                if game[col] == other_player:
                    other_pos = col
            
            if player_pos and other_pos:
                # Determine if they're teammates or opponents
                player_attacking = player_pos in ATTACKING_PLAYER_COLS
                other_attacking = other_pos in ATTACKING_PLAYER_COLS
                
                level_change = get_level_change(game, player_name)
                
                if player_attacking == other_attacking:
                    # Same team (both attacking or both defending)
                    teammate_games.append(level_change)
                else:
                    # Opposing teams
                    opponent_games.append(level_change)
        
        # Calculate averages if enough games
        if len(teammate_games) >= min_games:
            teammate_stats[other_player] = {
                'avg. level change': sum(teammate_games) / len(teammate_games),
                'games': len(teammate_games)
            }
        
        if len(opponent_games) >= min_games:
            opponent_stats[other_player] = {
                'avg. level change': sum(opponent_games) / len(opponent_games),
                'games': len(opponent_games)
            }
    
    return teammate_stats, opponent_stats