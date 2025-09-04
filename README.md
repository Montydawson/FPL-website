# FPL Dashboard Project

A modern web application that displays Fantasy Premier League player statistics including xG, xA, Points, Price and fixture difficulty ratings. With the main goal of predicting their future value (xValue - Expected Points/Price) based off of these statistics. Website link:https://fpl-stats-a10fe9ee4f83.herokuapp.com/

##  Project Structure

```
FPL/
├── README.md                 # This file - project overview
├── DEVELOPMENT_GUIDE.md       # Development instructions
├── deploy.sh                # Deployment script
├── requirements.txt         # Python dependencies
├── Procfile                 # Heroku deployment config
├── fpl_proxy.py            # Main Python server (backend)
├── index.html              # Main webpage structure
├── styles.css              # Website styling
├── script.js               # Frontend JavaScript
├── FPL data.py             # Python script
└── test-api.html           # API testing page
```



## Features

- **Live Data**: Real-time FPL API integration
- **Advanced Stats**: xG, xA, xGC, xPPG, xValue, Value, pFDR, fFDR
- **Interactive Tables**: Sort by any column, search players
- **Color-Coded Values**: Visual indicators for player value
- **Mobile Responsive**: Works on all devices
- **Position Filtering**: Separate tabs for each position


### Making Changes

**Frontend (HTML/CSS/JS):**
- `index.html` - Page structure and layout
- `styles.css` - Visual styling and colors
- `script.js` - Interactive functionality

**Backend (Python):**
- `fpl_proxy.py` - Server logic and FPL data processing
- Modify calculations in `calculate_player_stats()` method

### Testing Changes

1. Stop the current server (Ctrl+C)
2. Make your changes
3. Restart: `python3 fpl_proxy.py`
4. Refresh browser to see changes



## Data Sources

- **FPL API**: https://fantasy.premierleague.com/api/bootstrap-static/
- **Player Data**: Last 4 games for each player
- **Fixtures**: https://fantasy.premierleague.com/api/fixtures/
- **Update Frequency**: FPL stats are updated automatically every 30 minutes, with cached data served instantly for fast loading.



##  Troubleshooting

**No data loading:**
- Check internet connection
- FPL API might be temporarily down
- Check console for error messages

**Changes not showing:**
- Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
- Clear browser cache
- Restart the Python server

## Future Ideas
- Add player comparison features
- Historical data tracking
- Team optimization suggestions
- Price change predictions
- Transfer recommendations

## Documentation

For detailed guides on managing this project:
- **[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)** - Development workflow and code structure
- **[TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md)** - Common issues and solutions
