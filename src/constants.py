from typing import List

# Player column constants
ATTACKING_PLAYER_COLS: List[str] = ['A1', 'A2', 'A3', 'A4', 'A5']
DEFENDING_PLAYER_COLS: List[str] = ['D1', 'D2', 'D3', 'D4']
ALL_PLAYER_COLS: List[str] = ATTACKING_PLAYER_COLS + DEFENDING_PLAYER_COLS
DEALER_COL: str = DEFENDING_PLAYER_COLS[0]  # D1

# Minimum sample size for leaderboards and rankings
MIN_SAMPLE_SIZE: int = 5