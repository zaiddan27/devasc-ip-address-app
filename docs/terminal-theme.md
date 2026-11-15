# Demo terminal theme ("Paper")

IP_PAPI uses the terminal's own text colour, so it works on any background. For the demo video it looks best on a paper-coloured terminal that matches the team's reference board (palette 111111, 333333, 777777, BEB8AD, E6E1D7, F6F4EE).

## Windows Terminal

1. Open Windows Terminal → **Settings** → **Open JSON file** (bottom left).
2. Add this to the `"schemes"` list:

```json
{
    "name": "IP_PAPI Paper",
    "background": "#F6F4EE",
    "foreground": "#111111",
    "cursorColor": "#333333",
    "selectionBackground": "#E6E1D7",
    "black": "#111111",
    "red": "#7A3B2E",
    "green": "#4F5B3A",
    "yellow": "#8A6D3B",
    "blue": "#333333",
    "purple": "#555555",
    "cyan": "#777777",
    "white": "#BEB8AD",
    "brightBlack": "#777777",
    "brightRed": "#7A3B2E",
    "brightGreen": "#4F5B3A",
    "brightYellow": "#8A6D3B",
    "brightBlue": "#333333",
    "brightPurple": "#555555",
    "brightCyan": "#777777",
    "brightWhite": "#E6E1D7"
}
```

3. In your profile (e.g. PowerShell) → **Appearance** → **Color scheme** → choose **IP_PAPI Paper**. A font such as Cascadia Mono at 16–18 pt reads well in a recording.
