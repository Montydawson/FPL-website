# FPL Stats Website - Development Guide

## Project Structure

### Core Files
- **`fpl_proxy.py`** - Main Python server that handles:
  - HTTP requests and routing
  - FPL API data fetching
  - Player statistics calculation
  - Data caching (30-minute cache)
  - Background data refresh

- **`index.html`** - Main webpage structure
- **`script.js`** - Frontend JavaScript for:
  - Data fetching from API
  - Table rendering and sorting
  - Search functionality
  - Tab switching between positions

- **`styles.css`** - Website styling and responsive design

### Configuration Files
- **`requirements.txt`** - Python dependencies
- **`Procfile`** - Heroku process definition
- **`deploy.sh`** - Deployment script

## How the System Works

### Data Flow
1. **FPL API Fetch** → `fpl_proxy.py` fetches from Fantasy Premier League API
2. **Data Processing** → Calculates xG, xA, xGC, xPPG, xValue for each player
3. **Caching** → Stores processed data for 30 minutes
4. **Frontend Request** → `script.js` requests data from `/api/fpl-data`
5. **Display** → Tables are rendered with individual player stats

### Key Functions in fpl_proxy.py

#### `calculate_player_stats_from_totals(player, fixtures)`
- Used when season hasn't started or no recent games
- Calculates stats from season totals (goals, assists, minutes, etc.)
- **Important**: Uses individual player data, not hardcoded values

#### `calculate_player_stats(player, history, fixtures)`
- Used when current season has started
- Calculates stats from last 4 games

#### `fetch_and_process_data()`
- Main data processing function
- Handles both pre-season and in-season scenarios

## Making Changes

### Backend Changes (fpl_proxy.py)
- **Player Calculation Logic**: Modify calculation functions
- **API Endpoints**: Add new routes in `do_GET()` method
- **Data Processing**: Update processing logic in fetch functions

### Frontend Changes
- **`script.js`**: Modify table rendering, add new features
- **`index.html`**: Change page structure, add new sections
- **`styles.css`**: Update styling, colors, layout

### Testing Changes Locally
```bash
# Run server locally
python3 fpl_proxy.py

# Test in browser
open http://localhost:8001

# Test API directly
curl http://localhost:8001/api/fpl-data | python3 -m json.tool
```

## Common Development Tasks

### Adding a New Stat Column
1. **Backend**: Modify calculation functions to include new stat
2. **Frontend**: Update `createTableCells()` in script.js
3. **HTML**: Add new column header in index.html
4. **CSS**: Style the new column if needed

### Changing Calculation Logic
1. Edit `calculate_player_stats_from_totals()` or `calculate_player_stats()`
2. Test locally with debug script
3. Deploy changes

### Debugging Data Issues
```bash
# Use the debug script
python3 debug_fpl.py

# Check specific player data
python3 -c "
import requests
response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
players = response.json()['elements']
player = players[0]  # First player
print(f'Player: {player[\"first_name\"]} {player[\"second_name\"]}')
print(f'Goals: {player.get(\"goals_scored\", 0)}')
print(f'Assists: {player.get(\"assists\", 0)}')
print(f'Minutes: {player.get(\"minutes\", 0)}')
"
```



## Deploying changes

```bash
# Check what files have changed
git status

# Add changes
git add <filename>
# Or add all changes:
git add .

# Commit with a descriptive message
git commit -m "..."

# Push to github
git push origin master

# Deploy to Heroku 
git push heroku master

# Verify Deployment:

# Check deployment status
heroku logs --tail --app fpl-stats

# Test the live website
curl https://fpl-stats-a10fe9ee4f83.herokuapp.com/api/fpl-data
```

## Common Commands

```bash
# Check App Status
heroku ps --app fpl-stats

# View Logs

heroku logs --tail --app fpl-stats


# Restart App

heroku restart --app fpl-stats


# Check Git Status

git status
git log --oneline -10  # See last 10 commits
```

## Troubleshooting

### If Deployment Fails
1. Check the build logs: `heroku logs --tail --app fpl-stats`
2. Ensure all required files are committed
3. Check that `requirements.txt` includes all dependencies
4. Verify `Procfile` is correct: `web: python fpl_proxy.py`

### If Website Shows Errors
1. Check server logs: `heroku logs --tail --app fpl-stats`
2. Test API endpoint: `curl https://fpl-stats-a10fe9ee4f83.herokuapp.com/api/fpl-data`
3. Check if data is processing correctly

### Emergency Rollback
```bash
# See recent releases
heroku releases --app fpl-stats

# Rollback to previous version (replace v12 with desired version)
heroku rollback v12 --app fpl-stats
```
## Important Notes

### Data Caching
- Data is cached for 30 minutes
- Background refresh starts when cache expires
- Users get old data immediately while new data loads

### Season Detection
- System automatically detects if season has started
- Uses different calculation methods for pre-season vs in-season

### Error Handling
- Server continues serving cached data if API fails
- Frontend shows error messages for failed requests
- Logs errors for debugging

## Performance Considerations
- Processing 658 players takes ~1-2 seconds
- API rate limiting: Small delays between batch requests
- Heroku dyno limitations: 512MB RAM, shared CPU
