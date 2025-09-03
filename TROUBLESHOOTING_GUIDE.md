# FPL Stats Website - Troubleshooting Guide

## Quick Diagnostics

### Check if Website is Working
```bash
# Test the live API
curl https://fpl-stats-a10fe9ee4f83.herokuapp.com/api/fpl-data

# Should return JSON with success: true
```

### Check Heroku App Status
```bash
heroku ps --app fpl-stats
heroku logs --tail --app fpl-stats
```

## Common Issues & Solutions

### 1. Website Shows "Loading..." Forever

**Symptoms**: Frontend stuck on loading screen
**Causes**: API endpoint not responding, CORS issues, JavaScript errors

**Solutions**:
```bash
# Check if API is responding
curl https://fpl-stats-a10fe9ee4f83.herokuapp.com/api/fpl-data

# Check browser console for JavaScript errors
# Open browser dev tools (F12) → Console tab

# Check server logs
heroku logs --tail --app fpl-stats
```

### 2. All Players Show Same Stats

**Symptoms**: Players in same position have identical xG, xA, xGC values
**Cause**: Position-based minimums overriding individual data

**Solution**: Check `calculate_player_stats_from_totals()` function
- Ensure it uses actual player data: `player.get('goals_scored', 0)`
- Verify minimums only apply to players with zero playing time
- Test with debug script: `python3 debug_fpl.py`

### 3. Heroku App Crashed

**Symptoms**: Website returns "Application Error"
**Check**: `heroku logs --app fpl-stats`

**Common Causes**:
- **Memory limit exceeded**: Reduce data processing or optimize code
- **Timeout**: FPL API taking too long, add error handling
- **Missing dependencies**: Check `requirements.txt`

**Solutions**:
```bash
# Restart the app
heroku restart --app fpl-stats

# Check dyno status
heroku ps --app fpl-stats

# Scale up if needed (costs money)
heroku ps:scale web=1 --app fpl-stats
```

### 4. Deployment Failed

**Symptoms**: `git push heroku master` fails
**Check**: Build logs in terminal output

**Common Issues**:
- **Python syntax errors**: Fix code errors
- **Missing requirements**: Update `requirements.txt`
- **Procfile issues**: Ensure `Procfile` contains: `web: python fpl_proxy.py`

**Solutions**:
```bash
# Check what's different
git status
git diff

# Test locally first
python3 fpl_proxy.py

# Fix issues and redeploy
git add .
git commit -m "Fix deployment issue"
git push heroku master
```

### 5. Data Not Updating

**Symptoms**: Stats seem outdated, cache not refreshing
**Cause**: Background refresh failing, API issues

**Solutions**:
```bash
# Force restart to clear cache
heroku restart --app fpl-stats

# Check if FPL API is accessible
curl https://fantasy.premierleague.com/api/bootstrap-static/

# Monitor logs during data refresh
heroku logs --tail --app fpl-stats
```

### 6. Frontend Not Loading Properly

**Symptoms**: Broken layout, missing styles, JavaScript errors
**Check**: Browser developer tools (F12)

**Solutions**:
- **CSS not loading**: Check file paths in `index.html`
- **JavaScript errors**: Check console for syntax errors
- **CORS issues**: Ensure API endpoints have proper headers

### 7. Performance Issues

**Symptoms**: Website slow to load, timeouts
**Causes**: Large data processing, API rate limits

**Solutions**:
- **Optimize data processing**: Reduce API calls, improve caching
- **Upgrade Heroku plan**: More memory/CPU (costs money)
- **Add loading indicators**: Better user experience

## Emergency Procedures

### Complete Website Down
1. **Check Heroku status**: https://status.heroku.com/
2. **Restart app**: `heroku restart --app fpl-stats`
3. **Check logs**: `heroku logs --tail --app fpl-stats`
4. **Rollback if needed**: `heroku rollback v12 --app fpl-stats`

### Data Corruption
1. **Restart to clear cache**: `heroku restart --app fpl-stats`
2. **Test API manually**: `curl https://fantasy.premierleague.com/api/bootstrap-static/`
3. **Check calculation logic**: Review recent code changes
4. **Rollback if needed**: `heroku rollback v12 --app fpl-stats`

### Rollback to Previous Version
```bash
# See recent releases
heroku releases --app fpl-stats

# Rollback to specific version
heroku rollback v12 --app fpl-stats

# Verify rollback worked
curl https://fpl-stats-a10fe9ee4f83.herokuapp.com/api/fpl-data
```

## Monitoring & Maintenance

### Regular Checks
- **Weekly**: Check website functionality
- **Monthly**: Review Heroku logs for errors
- **Season start**: Verify season detection works
- **After FPL updates**: Test data processing

### Log Analysis
```bash
# Search for errors
heroku logs --app fpl-stats | grep -i error

# Monitor memory usage
heroku logs --app fpl-stats | grep -i memory

# Check processing times
heroku logs --app fpl-stats | grep "Processing took"
```

### Performance Monitoring
- **Data processing time**: Should be 1-3 seconds
- **Memory usage**: Should stay under 512MB
- **API response time**: Should be under 5 seconds
- **Cache hit rate**: Most requests should use cached data

## Contact Information
- **Heroku Dashboard**: https://dashboard.heroku.com/apps/fpl-stats
- **GitHub Repository**: https://github.com/Montydawson/FPL.git
- **Live Website**: https://fpl-stats-a10fe9ee4f83.herokuapp.com/
