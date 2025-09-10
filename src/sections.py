from nicegui import ui
import pandas as pd
import plotly.express as px
from typing import Dict, List, Any, Union, Optional

from .utils import get_color_for_result
from .stats import calculate_teammate_opponent_stats
from .constants import MIN_SAMPLE_SIZE

def format_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if "Points" in col:
            df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
    return df

def format_table_with_colors(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Format table with background colors based on performance outliers"""
    df = df.copy()
    
    # Format numeric values
    for col in df.columns:
        if "Points" in col:
            df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
    
    return df

def get_table_row_classes(df: pd.DataFrame, metric: str) -> List[str]:
    """Get CSS classes for table rows based on performance"""
    if len(df) <= 2:
        return []
    
    # Get the metric column for color coding
    metric_col = None
    for col in df.columns:
        if col == metric:
            metric_col = col
            break
    
    if not metric_col:
        return []
    
    # Calculate quartiles for color coding
    values = df[metric_col].astype(float)
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    
    # Determine if higher values are better (for attacking points and level change)
    higher_is_better = "Attacking" in metric or "Level Change" in metric
    
    row_classes = []
    for idx, row in df.iterrows():
        value = float(row[metric_col])
        if higher_is_better:
            if value >= q3:
                row_classes.append("bg-green-100")  # Good performance
            elif value <= q1:
                row_classes.append("bg-red-100")    # Poor performance
            else:
                row_classes.append("")
        else:  # For defending points, lower is better
            if value <= q1:
                row_classes.append("bg-green-100")  # Good performance
            elif value >= q3:
                row_classes.append("bg-red-100")    # Poor performance
            else:
                row_classes.append("")
    
    return row_classes

def create_colored_table(df: pd.DataFrame, metric: str, all_player_stats: Optional[Dict[str, Dict[str, Union[float, int]]]] = None) -> None:
    """Create a colored table using HTML with standard deviation-based coloring"""
    df_formatted = format_table_with_colors(df, metric)
    
    if len(df) <= 2:
        # Just create a simple table without colors
        ui.table.from_pandas(df_formatted).classes("text-xs").props("hide-header")
        return
    
    # Get the metric column for color coding
    metric_col = None
    for col in df.columns:
        if col == metric:
            metric_col = col
            break
    
    if not metric_col:
        ui.table.from_pandas(df_formatted).classes("text-xs").props("hide-header")
        return
    
    # Calculate mean and standard deviation from ALL players (not just n>=5)
    if all_player_stats:
        # Use all player stats for mean/std calculation
        all_values = []
        for player_stats in all_player_stats.values():
            if metric in player_stats:
                all_values.append(player_stats[metric])
        if all_values:
            mean_val = sum(all_values) / len(all_values)
            variance = sum((x - mean_val) ** 2 for x in all_values) / len(all_values)
            std_val = variance ** 0.5
        else:
            values = df[metric_col].astype(float)
            mean_val = values.mean()
            std_val = values.std()
    else:
        # Fallback to using just the displayed values
        values = df[metric_col].astype(float)
        mean_val = values.mean()
        std_val = values.std()
    
    if std_val == 0:  # All values are the same
        ui.table.from_pandas(df_formatted).classes("text-xs").props("hide-header")
        return
    
    # Determine if higher values are better
    higher_is_better = "attacking" in metric or "level change" in metric
    
    def get_background_color(z_score, is_good_performance):
        """Get background color based on z-score with continuous gradient"""
        abs_z = abs(z_score)
        
        # Only color if z-score is at least 0.5 (mild outlier threshold)
        if abs_z < 0.5:
            return ""
        
        # Cap the intensity at z-score of 2 (strong outliers get maximum color)
        # This creates a smooth gradient from 0.5 to 2.0 standard deviations
        capped_z = min(abs_z, 2.0)
        
        # Map z-score to opacity: 0.5σ -> 0.1 opacity, 2.0σ -> 0.75 opacity
        # Formula: opacity = (capped_z - 0.5) / (2.0 - 0.5) * (0.75 - 0.1) + 0.1
        opacity = (capped_z - 0.5) / 1.5 * 0.65 + 0.1
        
        if is_good_performance:
            # Green for good performance
            return f"background-color: rgba(34, 197, 94, {opacity});"
        else:
            # Red for poor performance  
            return f"background-color: rgba(220, 38, 38, {opacity});"
    
    # Create HTML table
    html_content = '<div style="font-size: 14px; min-width: 200px;"><table style="width: 100%; border-collapse: collapse;">'
    
    for idx, row in df_formatted.iterrows():
        value = float(df.loc[idx, metric_col])  # Use original df for numeric comparison
        z_score = (value - mean_val) / std_val
        
        # Determine if this is good or poor performance
        if higher_is_better:
            is_good = z_score > 0  # Above mean is good
        else:
            is_good = z_score < 0  # Below mean is good (for defending points)
        
        # Only color outliers (abs(z_score) >= 0.5)
        bg_color = ""
        if abs(z_score) >= 0.5:
            bg_color = get_background_color(z_score, is_good)
        
        html_content += f'<tr style="{bg_color}">'
        for col_val in row:
            html_content += f'<td style="padding: 4px 6px; text-align: center;">{col_val}</td>'
        html_content += '</tr>'
    
    html_content += '</table></div>'
    ui.html(html_content)

def create_colored_teammate_opponent_table(data: List[Dict[str, Any]], title: str, subtitle: str) -> None:
    """Create a colored table for teammate/opponent rankings"""
    if not data:
        ui.label(title).classes("text-h6 font-bold")
        ui.label(subtitle).classes("text-sm text-gray-600 mb-2")
        ui.label(f"No data available (n≥{MIN_SAMPLE_SIZE})")
        return
    
    # Calculate mean and standard deviation for coloring
    level_changes = [float(row['Avg. Level Change']) for row in data]
    if len(level_changes) <= 1:
        # Not enough data for meaningful coloring
        df_table = pd.DataFrame(data)[["Rank", "Player", "Avg. Level Change", "Games"]]
        ui.label(title).classes("text-h6 font-bold")
        ui.label(subtitle).classes("text-sm text-gray-600 mb-2")
        ui.table.from_pandas(df_table).classes("text-xs").props("hide-header")
        return
    
    mean_val = sum(level_changes) / len(level_changes)
    variance = sum((x - mean_val) ** 2 for x in level_changes) / len(level_changes)
    std_val = variance ** 0.5
    
    if std_val == 0:
        # All values are the same
        df_table = pd.DataFrame(data)[["Rank", "Player", "Avg. Level Change", "Games"]]
        ui.label(title).classes("text-h6 font-bold")
        ui.label(subtitle).classes("text-sm text-gray-600 mb-2")
        ui.table.from_pandas(df_table).classes("text-xs").props("hide-header")
        return
    
    def get_background_color(level_change_str: str) -> str:
        """Get background color based on z-score"""
        value = float(level_change_str)
        z_score = (value - mean_val) / std_val
        abs_z = abs(z_score)
        
        # Only color if z-score is at least 0.5
        if abs_z < 0.5:
            return ""
        
        # Cap at 2.0 standard deviations
        capped_z = min(abs_z, 2.0)
        
        # Map to opacity: 0.5σ -> 0.1, 2.0σ -> 0.75
        opacity = (capped_z - 0.5) / 1.5 * 0.65 + 0.1
        
        # For level change, higher is always better (green), lower is worse (red)
        if z_score > 0:
            return f"background-color: rgba(34, 197, 94, {opacity});"  # Green
        else:
            return f"background-color: rgba(220, 38, 38, {opacity});"   # Red
    
    # Create HTML table with colors
    html_content = f'''
    <div style="min-width: 200px;">
        <h6 style="font-weight: bold; margin-bottom: 4px; font-size: 18px; white-space: nowrap;">{title}</h6>
        <p style="font-size: 14px; color: #6b7280; margin-bottom: 12px;">{subtitle}</p>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    '''
    
    for row in data:
        bg_color = get_background_color(row['Avg. Level Change'])
        html_content += f'<tr style="{bg_color}">'
        html_content += f'<td style="padding: 4px 6px; text-align: center;">{row["Rank"]}</td>'
        html_content += f'<td style="padding: 4px 6px; text-align: center;">{row["Player"]}</td>'
        html_content += f'<td style="padding: 4px 6px; text-align: center;">{row["Avg. Level Change"]}</td>'
        html_content += f'<td style="padding: 4px 6px; text-align: center;">{row["Games"]}</td>'
        html_content += '</tr>'
    
    html_content += '</table></div>'
    ui.html(html_content)

def create_global_stats(df_2decks: pd.DataFrame, df_3decks: pd.DataFrame) -> None:
    """Create the global statistics section"""
    result_counts_2decks = df_2decks['Result'].value_counts()
    result_counts_3decks = df_3decks['Result'].value_counts()
    
    average_points_2decks = df_2decks['Points'].mean()
    average_points_3decks = df_3decks['Points'].mean()
    
    
    with ui.card():
        ui.label("🌍 Global Statistics").classes('text-h5')
        with ui.row().classes("gap-4 flex-wrap"):
            with ui.card().classes("flex-1 p-4 min-w-0"):
                ui.label("2-Deck Games").classes('text-h6')
                ui.label(f"Total games: {len(df_2decks)}").classes('font-bold')
                ui.label(f"Average points collected: {average_points_2decks:.2f}").classes('font-bold')
                
                colors_2deck = [get_color_for_result(result) for result in result_counts_2decks.index]
                fig_2deck = px.pie(
                    values=result_counts_2decks.values,
                    names=result_counts_2decks.index,
                    title="",
                    color_discrete_sequence=colors_2deck
                )
                fig_2deck.update_layout(
                    height=400, 
                    width=650,
                    margin=dict(t=10, b=60, l=10, r=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.15,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10)
                    )
                )
                ui.plotly(fig_2deck)
                
            with ui.card().classes("flex-1 p-4 min-w-0"):
                ui.label("3-Deck Games").classes('text-h6')
                ui.label(f"Total games: {len(df_3decks)}").classes('font-bold')
                ui.label(f"Average points collected: {average_points_3decks:.2f}").classes('font-bold')
                
                colors_3deck = [get_color_for_result(result) for result in result_counts_3decks.index]
                fig_3deck = px.pie(
                    values=result_counts_3decks.values,
                    names=result_counts_3decks.index,
                    title="",
                    color_discrete_sequence=colors_3deck
                )
                fig_3deck.update_layout(
                    height=400, 
                    width=650,
                    margin=dict(t=10, b=60, l=10, r=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.15,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10)
                    )
                )
                ui.plotly(fig_3deck)
                

def create_rankings(lb2: Dict[str, pd.DataFrame], lb3: Dict[str, pd.DataFrame], lb2_all_stats: Dict[str, Dict[str, Union[float, int]]], lb3_all_stats: Dict[str, Dict[str, Union[float, int]]]) -> None:
    """Create the leaderboards section"""
    ui.label("🏆 Leaderboards").classes("text-h4 mt-4")
    
    with ui.card():
        ui.label("2 Decks").classes("text-h5")
        ui.label(f"* n>={MIN_SAMPLE_SIZE} is required")
        with ui.row().classes("flex-nowrap gap-2"):
            for metric, table in lb2.items():
                with ui.card().classes("p-2 flex-1"):
                    ui.label(metric).classes("font-bold").style("font-size: 18px;")
                    create_colored_table(table, metric, lb2_all_stats)

    with ui.card():
        ui.label("3 Decks").classes("text-h5")
        ui.label(f"* n>={MIN_SAMPLE_SIZE} is required")
        with ui.row().classes("flex-nowrap gap-2"):
            for metric, table in lb3.items():
                with ui.card().classes("p-2 flex-1"):
                    ui.label(metric).classes("font-bold").style("font-size: 18px;")
                    create_colored_table(table, metric, lb3_all_stats)

def create_player_lookup(unique_players_no_nan: List[str], player_stats_2decks: Dict[str, Dict[str, Union[float, int]]], player_stats_3decks: Dict[str, Dict[str, Union[float, int]]], df_2decks: pd.DataFrame, df_3decks: pd.DataFrame) -> None:
    """Create the player lookup section"""
    with ui.card():
        ui.label("🔍 Player Stats Lookup").classes("text-h5")

        # Set default player to "Terry" if available, otherwise first player
        default_player = "Terry" if "Terry" in unique_players_no_nan else unique_players_no_nan[0]
        
        with ui.row().classes("gap-4 mt-4 items-start"):
            # Dropdown controls on the left
            with ui.column().classes("gap-2"):
                deck_choice = ui.select([2, 3], value=2, label="Number of Decks").classes("w-40")
                player_choice = ui.select(unique_players_no_nan, value=default_player, label="Player").classes("w-40")
            
            # Player stats card
            player_card = ui.card().classes("flex-1 p-4")
            
            # Teammate rankings card
            teammate_card = ui.card().classes("flex-1 p-4")
            
            # Opponent rankings card  
            opponent_card = ui.card().classes("flex-1 p-4")

        def update_player_stats():
            chosen_decks = deck_choice.value
            chosen_player = player_choice.value
            stats_dict = player_stats_2decks if chosen_decks == 2 else player_stats_3decks
            df = df_2decks if chosen_decks == 2 else df_3decks
            
            # Clear all cards
            player_card.clear()
            teammate_card.clear()
            opponent_card.clear()

            if not chosen_player or chosen_player not in stats_dict:
                player_card.add(ui.label("No data available."))
                return

            # Update player stats card
            player_data = []
            stats = stats_dict[chosen_player]
            
            # Define metric groups with their corresponding sample size keys
            metric_groups = [
                ("avg. collected when attacking", "attacking sample size"),
                ("avg. opponents collected when defending", "defending sample size"),
                ("avg. opponents collected defending (teammate)", "defending teammate sample size"),
                ("avg. opponents collected defending (dealer)", "defending dealer sample size"),
                ("avg. level change", "level change sample size")
            ]
            
            for metric, sample_key in metric_groups:
                if metric in stats and sample_key in stats:
                    value = stats[metric]
                    sample_size = stats[sample_key]
                    
                    # Format the value
                    if isinstance(value, (int, float)):
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    
                    player_data.append({
                        "Metric": metric,
                        "Points": formatted_value,
                        "# of Games": int(sample_size)
                    })
            
            # Update player stats card
            if player_data:
                df_player = pd.DataFrame(player_data)
                
                with player_card:
                    ui.label(f"Stats for {chosen_player}").classes("text-h6 font-bold")
                    ui.label(f"({chosen_decks}-deck games)").classes("text-sm text-gray-600 mb-2")
                    ui.table.from_pandas(df_player).classes("text-xs")
            else:
                with player_card:
                    ui.label(f"Stats for {chosen_player}").classes("text-h6 font-bold")
                    ui.label("No data available.")
            
            # Update teammate and opponent rankings
            teammate_stats, opponent_stats = calculate_teammate_opponent_stats(chosen_player, df)
            
            # Prepare teammate data
            teammate_data = []
            if teammate_stats:
                for player, stats in teammate_stats.items():
                    teammate_data.append({
                        "Player": player,
                        "Avg. Level Change": f"{stats['avg. level change']:.2f}",
                        "Games": stats['games']
                    })
                
                # Sort by avg. level change (descending - higher is better)
                teammate_data.sort(key=lambda x: float(x['Avg. Level Change']), reverse=True)
                
                # Add rank
                for i, row in enumerate(teammate_data):
                    row["Rank"] = i + 1
            
            # Prepare opponent data
            opponent_data = []
            if opponent_stats:
                for player, stats in opponent_stats.items():
                    opponent_data.append({
                        "Player": player,
                        "Avg. Level Change": f"{stats['avg. level change']:.2f}",
                        "Games": stats['games']
                    })
                
                # Sort by avg. level change (ascending - lower means tougher opponent)
                opponent_data.sort(key=lambda x: float(x['Avg. Level Change']), reverse=False)
                
                # Add rank
                for i, row in enumerate(opponent_data):
                    row["Rank"] = i + 1
            
            # Create colored tables
            with teammate_card:
                create_colored_teammate_opponent_table(
                    teammate_data, 
                    "Best Teammates", 
                    "(avg. level change with you)"
                )
            
            with opponent_card:
                create_colored_teammate_opponent_table(
                    opponent_data, 
                    "Toughest Opponents", 
                    "(avg. level change against)"
                )
                    

        # Connect change events to auto-update
        deck_choice.on_value_change(lambda: update_player_stats())
        player_choice.on_value_change(lambda: update_player_stats())
        
        # Initialize with default values
        update_player_stats()