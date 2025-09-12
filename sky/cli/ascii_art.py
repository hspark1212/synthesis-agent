"""
ASCII Art for SKY - Synthesis Knowledge  Agent
"""

SKY_FULL_LOGO = """
╭───────────────────────────╮
│                           │
│ ███████╗██╗  ██╗██╗   ██╗ │
│ ██╔════╝██║ ██╔╝╚██╗ ██╔╝ │
│ ███████╗█████╔╝  ╚████╔╝  │
│ ╚════██║██╔═██╗   ╚██╔╝   │
│ ███████║██║  ██╗   ██║    │
│ ╚══════╝╚═╝  ╚═╝   ╚═╝    │
│                           │
╰───────────────────────────╯
"""

SKY_COMPACT_LOGO = """
╭─────────────────────────╮
│ ███████╗██╗  ██╗██╗   ██╗ │
│ ██╔════╝██║ ██╔╝╚██╗ ██╔╝ │
│ ███████╗█████╔╝  ╚████╔╝  │
│ ╚════██║██╔═██╗   ╚██╔╝   │
│ ███████║██║  ██╗   ██║    │
│ ╚══════╝╚═╝  ╚═╝   ╚═╝    │
╰─────────────────────────╯
"""

SKY_MINIMAL_LOGO = """
┌─────────┐
│ ╔═╗╦╔═╦ ╦ │
│ ╚═╗╠╩╗╚╦╝ │
│ ╚═╝╩ ╩ ╩  │
└─────────┘
"""

def get_responsive_logo(terminal_width: int) -> str:
    """
    Get the appropriate logo size based on terminal width.
    
    Args:
        terminal_width: Current terminal width in characters
        
    Returns:
        ASCII art string or text fallback
    """
    if terminal_width >= 80:
        return SKY_FULL_LOGO
    elif terminal_width >= 60:
        return SKY_COMPACT_LOGO
    elif terminal_width >= 30:
        return SKY_MINIMAL_LOGO
    else:
        return "SKY"