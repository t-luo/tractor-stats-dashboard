def get_color_for_result(result: str) -> str:
    """Get color based on result type"""
    if result == 'Draw':
        return '#808080'  # Gray
    elif result.startswith('A+'):
        level = int(result[2:])
        # Blue gradient: lighter for lower, darker for higher
        blue_colors = {1: '#CCE5FF', 2: '#99CCFF', 3: '#66B2FF', 
                      4: '#3399FF', 5: '#0080FF', 6: '#0066CC'}
        return blue_colors.get(level, '#0080FF')
    elif result.startswith('D+'):
        level = int(result[2:])
        # Red gradient: lighter for lower, darker for higher
        red_colors = {1: '#FFCCCC', 2: '#FF9999', 3: '#FF6666', 
                     4: '#FF3333', 5: '#FF0000', 6: '#CC0000'}
        return red_colors.get(level, '#FF0000')
    return '#CCCCCC'  # Default gray