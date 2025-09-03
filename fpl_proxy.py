#!/usr/bin/env python3
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time
from math import exp, factorial
from datetime import datetime

# Global variables to share data between requests
fpl_data_cache = {
    'processed_data': None,
    'last_update': None,
    'is_updating': False
}

class FPLProxyHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/fpl-data':
            self.handle_fpl_data()
        elif parsed_path.path == '/':
            self.serve_file('index.html', 'text/html')
        elif parsed_path.path.endswith('.css'):
            self.serve_file(parsed_path.path[1:], 'text/css')
        elif parsed_path.path.endswith('.js'):
            self.serve_file(parsed_path.path[1:], 'application/javascript')
        elif parsed_path.path.endswith('.html'):
            self.serve_file(parsed_path.path[1:], 'text/html')
        else:
            self.send_error(404)

    def serve_file(self, filename, content_type):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404)

    def handle_fpl_data(self):
        try:
            current_time = time.time()
            cache_duration = 1800  # 30 minutes in seconds
            
            # Check if we have cached data
            if fpl_data_cache['processed_data'] is None:
                # No cached data - return loading message and start processing in background
                if not fpl_data_cache['is_updating']:
                    print("No cached data found. Starting background data fetch...")
                    fpl_data_cache['is_updating'] = True
                    threading.Thread(target=self.background_refresh, daemon=True).start()
                
                # Return loading response
                self.send_response(202)  # 202 Accepted - processing
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                loading_response = {
                    'success': False,
                    'loading': True,
                    'message': 'FPL data is being processed. Please refresh in a few moments.',
                    'is_updating': True
                }
                
                self.wfile.write(json.dumps(loading_response).encode('utf-8'))
                return
                
            elif current_time - fpl_data_cache['last_update'] > cache_duration:
                # Cache expired - serve old data immediately, refresh in background
                if not fpl_data_cache['is_updating']:
                    print("Cache expired. Starting background refresh...")
                    fpl_data_cache['is_updating'] = True
                    # Start background thread to update data
                    threading.Thread(target=self.background_refresh, daemon=True).start()
                else:
                    print("Background refresh already in progress...")
            
            # Always serve the cached data (even if it's being refreshed)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            cache_age_minutes = (current_time - fpl_data_cache['last_update']) / 60 if fpl_data_cache['last_update'] else 0
            
            response_data = {
                'success': True,
                'data': fpl_data_cache['processed_data'],
                'last_updated': fpl_data_cache['last_update'],
                'cache_age_minutes': round(cache_age_minutes, 1),
                'is_updating': fpl_data_cache['is_updating']
            }
            
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error handling FPL data request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'success': False,
                'error': str(e)
            }
            
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def background_refresh(self):
        """Background thread to refresh data without blocking requests"""
        try:
            print("Background refresh started...")
            self.fetch_and_process_data()
            print("Background refresh completed!")
        except Exception as e:
            print(f"Background refresh failed: {e}")
        finally:
            fpl_data_cache['is_updating'] = False

    def fetch_and_process_data(self):
        # Fetch data from FPL API
        bootstrap_response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        fixtures_response = requests.get('https://fantasy.premierleague.com/api/fixtures/')
        
        bootstrap_data = bootstrap_response.json()
        fixtures_data = fixtures_response.json()
        
        players = bootstrap_data['elements']
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        events = bootstrap_data['events']
        
        # Check if season has started (any gameweek finished)
        season_started = any(event['finished'] for event in events)
        print(f"Season started: {season_started}")
        
        # Process player data
        player_data = {
            "Goalkeepers": [],
            "Defenders": [],
            "Midfielders": [],
            "Attackers": []
        }
        
        print(f"Processing {len(players)} players...")
        
        for i, player in enumerate(players):
            if i % 100 == 0:
                print(f"Processed {i}/{len(players)} players...")
                
            try:
                if season_started:
                    # Fetch player history for current season
                    history_url = f"https://fantasy.premierleague.com/api/element-summary/{player['id']}/"
                    history_response = requests.get(history_url)
                    history_data = history_response.json()
                    
                    # Get current season games only (filter by season and get last 4)
                    current_season_games = self.filter_current_season_games(history_data['history'], events)
                    last_4_games = current_season_games[-4:] if len(current_season_games) > 4 else current_season_games
                    
                    if len(last_4_games) == 0:
                        # No recent games - fall back to season totals
                        player_stats = self.calculate_player_stats_from_totals(player, fixtures_data)
                    else:
                        # Calculate player stats from recent games
                        player_stats = self.calculate_player_stats(player, last_4_games, fixtures_data)
                else:
                    # Season hasn't started - use season totals as estimates
                    player_stats = self.calculate_player_stats_from_totals(player, fixtures_data)
                
                if player_stats:  # Include all valid player stats
                    position = self.get_position_name(player['element_type'])
                    player_data[position].append(player_stats)
                    
            except Exception as e:
                print(f"Error processing player {player['id']}: {e}")
                continue
        
        # Sort by xValue
        for position in player_data:
            player_data[position].sort(key=lambda x: x['xValue'], reverse=True)
        
        # Update global cache
        fpl_data_cache['processed_data'] = player_data
        fpl_data_cache['last_update'] = time.time()
        print("Data processing complete!")

    def calculate_player_stats_from_totals(self, player, fixtures):
        """Calculate player stats from season totals when no recent games available"""
        full_name = f"{player['first_name']} {player['second_name']}"
        position = player['element_type']
        team_id = player['team']
        
        # Calculate FDR
        pFDR, fFDR = self.calculate_fdr(team_id, fixtures)
        
        # Use season totals and estimate per-game averages
        total_points = player.get('total_points', 0)
        total_minutes = player.get('minutes', 0)
        price = player['now_cost'] / 10
        
        # Use actual player stats from FPL API instead of hardcoded estimates
        total_goals = player.get('goals_scored', 0)
        total_assists = player.get('assists', 0)
        total_goals_conceded = player.get('goals_conceded', 0)
        total_saves = player.get('saves', 0)
        total_bonus = player.get('bonus', 0)
        total_clean_sheets = player.get('clean_sheets', 0)
        
        # Estimate games played from minutes (assuming 90 minutes per full game)
        games_played = max(1, total_minutes / 90) if total_minutes > 0 else 1
        
        # Calculate per-game averages from actual season data
        avg_points = total_points / games_played
        avg_minutes = total_minutes / games_played
        avg_bonus = total_bonus / games_played
        avg_saves = total_saves / games_played if position == 1 else 0
        
        # Calculate individual xG and xA based on actual goals and assists
        # Use actual values to preserve individual differences
        avg_xg = (total_goals / games_played) * 1.1 if total_goals > 0 else 0.0
        avg_xa = (total_assists / games_played) * 1.2 if total_assists > 0 else 0.0
        
        # Calculate xGC based on actual goals conceded per game
        if position in [1, 2]:  # GK and Defenders
            avg_xgc = total_goals_conceded / games_played if games_played > 0 and total_goals_conceded > 0 else 0.0
        elif position == 3:  # Midfielders
            avg_xgc = (total_goals_conceded / games_played) * 0.8 if games_played > 0 and total_goals_conceded > 0 else 0.0
        else:  # Attackers
            avg_xgc = 0  # Attackers don't get points for clean sheets
        
        # Apply very small minimums only for players with no data to avoid division by zero
        # But preserve the actual zeros for players who genuinely have no goals/assists
        if position == 1:  # Goalkeeper
            if total_minutes == 0:  # Only apply minimums for players with no playing time
                avg_xg = 0.001
                avg_xa = 0.001
                avg_xgc = 1.0
                avg_saves = 0.1
            else:
                # For players with playing time, use small minimums only if needed
                avg_xg = max(avg_xg, 0.001)
                avg_xa = max(avg_xa, 0.001)
                avg_xgc = max(avg_xgc, 0.1)
                avg_saves = max(avg_saves, 0.1)
        elif position == 2:  # Defender
            if total_minutes == 0:
                avg_xg = 0.01
                avg_xa = 0.01
                avg_xgc = 1.0
            else:
                avg_xg = max(avg_xg, 0.001)
                avg_xa = max(avg_xa, 0.001)
                avg_xgc = max(avg_xgc, 0.1)
        elif position == 3:  # Midfielder
            if total_minutes == 0:
                avg_xg = 0.05
                avg_xa = 0.05
                avg_xgc = 0.8
            else:
                avg_xg = max(avg_xg, 0.001)
                avg_xa = max(avg_xa, 0.001)
                avg_xgc = max(avg_xgc, 0.1)
        else:  # Attacker
            if total_minutes == 0:
                avg_xg = 0.1
                avg_xa = 0.02
            else:
                avg_xg = max(avg_xg, 0.001)
                avg_xa = max(avg_xa, 0.001)
            avg_xgc = 0
        
        minutes_category = 0 if avg_minutes == 0 else (1 if avg_minutes < 60 else 2)
        p_x0 = self.poisson_prob(avg_xgc, 0) if avg_xgc > 0 else 0.3
        
        # Calculate xPPG based on position
        xppg = 0
        
        if position == 1:  # Goalkeeper
            xppg = 3 * avg_xa + minutes_category + avg_bonus + (avg_saves / 3)
            if avg_minutes >= 60:
                xppg += 4 * p_x0
                for i in range(2, 15, 2):
                    xppg -= self.poisson_prob(avg_xgc, i)
        elif position == 2:  # Defender
            xppg = 6 * avg_xg + 3 * avg_xa + minutes_category + avg_bonus
            if avg_minutes >= 60:
                xppg += 4 * p_x0
                for i in range(2, 15, 2):
                    xppg -= self.poisson_prob(avg_xgc, i)
        elif position == 3:  # Midfielder
            cs_points = p_x0 if minutes_category == 2 else 0
            xppg = 5 * avg_xg + 3 * avg_xa + minutes_category + avg_bonus + cs_points
        elif position == 4:  # Attacker
            xppg = 4 * avg_xg + 3 * avg_xa + minutes_category + avg_bonus
        
        x_value = xppg / price if price > 0 else 0
        value = avg_points / price if price > 0 else 0
        
        return {
            'name': full_name,
            'position': position,
            'xG': avg_xg,
            'xA': avg_xa,
            'xGC': avg_xgc,
            'bonus': avg_bonus,
            'minutes': avg_minutes,
            'saves': avg_saves,
            'xPPG': xppg,
            'points': avg_points,
            'price': price,
            'value': value,
            'xValue': x_value,
            'pFDR': pFDR,
            'fFDR': fFDR
        }

    def calculate_player_stats(self, player, history, fixtures):
        full_name = f"{player['first_name']} {player['second_name']}"
        position = player['element_type']
        team_id = player['team']
        
        # Calculate FDR
        pFDR, fFDR = self.calculate_fdr(team_id, fixtures)
        
        # Calculate totals from last 4 games
        total_xg = sum(float(game.get('expected_goals', 0)) for game in history)
        total_xa = sum(float(game.get('expected_assists', 0)) for game in history)
        total_xgc = sum(float(game.get('expected_goals_conceded', 0)) for game in history)
        total_points = sum(game.get('total_points', 0) for game in history)
        total_minutes = sum(game.get('minutes', 0) for game in history)
        total_bonus = sum(game.get('bonus', 0) for game in history)
        total_saves = sum(game.get('saves', 0) for game in history) if position == 1 else 0
        
        # Calculate averages
        avg_xg = total_xg / 4
        avg_xa = total_xa / 4
        avg_xgc = total_xgc / 4
        avg_points = total_points / 4
        avg_minutes = total_minutes / 4
        avg_bonus = total_bonus / 4
        avg_saves = total_saves / 4
        
        minutes_category = 0 if avg_minutes == 0 else (1 if avg_minutes < 60 else 2)
        p_x0 = self.poisson_prob(avg_xgc, 0)
        price = player['now_cost'] / 10
        
        # Calculate xPPG based on position
        xppg = 0  # Initialize xppg
        
        if position == 1:  # Goalkeeper
            xppg = 3 * avg_xa + minutes_category + avg_bonus + (avg_saves / 3)
            if avg_minutes >= 60:
                xppg += 4 * p_x0
                for i in range(2, 15, 2):
                    xppg -= self.poisson_prob(avg_xgc, i)
        elif position == 2:  # Defender
            xppg = 6 * avg_xg + 3 * avg_xa + minutes_category + avg_bonus
            if avg_minutes >= 60:
                xppg += 4 * p_x0
                for i in range(2, 15, 2):
                    xppg -= self.poisson_prob(avg_xgc, i)
        elif position == 3:  # Midfielder
            cs_points = p_x0 if minutes_category == 2 else 0
            xppg = 5 * avg_xg + 3 * avg_xa + minutes_category + avg_bonus + cs_points
        elif position == 4:  # Attacker
            xppg = 4 * avg_xg + 3 * avg_xa + minutes_category + avg_bonus
        
        x_value = xppg / price if price > 0 else 0
        value = avg_points / price if price > 0 else 0
        
        return {
            'name': full_name,
            'position': position,
            'xG': avg_xg,
            'xA': avg_xa,
            'xGC': avg_xgc,
            'bonus': avg_bonus,
            'minutes': avg_minutes,
            'saves': avg_saves,
            'xPPG': xppg,
            'points': avg_points,
            'price': price,
            'value': value,
            'xValue': x_value,
            'pFDR': pFDR,
            'fFDR': fFDR
        }

    def filter_current_season_games(self, history, events):
        """Filter player history to only include games from the current season"""
        if not history or not events:
            return history
        
        # Get the current season's gameweeks (events)
        current_season_events = [event for event in events if event.get('is_current', False) or event.get('is_next', False) or event.get('finished', False)]
        
        # If no current season events found, use all events from this season (2024-25)
        if not current_season_events:
            # Fallback: assume all events in the API are from current season
            current_season_events = events
        
        # Get the range of gameweeks for current season
        current_season_gws = [event['id'] for event in current_season_events]
        
        # Filter history to only include games from current season gameweeks
        current_season_history = [
            game for game in history 
            if game.get('round') in current_season_gws
        ]
        
        # Debug logging for first few players
        if len(history) > 0 and len(current_season_history) != len(history):
            print(f"Filtered games: {len(history)} -> {len(current_season_history)} (current season only)")
        
        return current_season_history

    def calculate_fdr(self, team_id, fixtures):
        current_date = datetime.now()
        team_fixtures = [f for f in fixtures if f['team_h'] == team_id or f['team_a'] == team_id]
        
        past_fixtures = [
            f for f in team_fixtures
            if datetime.strptime(f['kickoff_time'], '%Y-%m-%dT%H:%M:%SZ') < current_date
        ]
        future_fixtures = [
            f for f in team_fixtures
            if datetime.strptime(f['kickoff_time'], '%Y-%m-%dT%H:%M:%SZ') >= current_date
        ]
        
        past_fixtures = sorted(past_fixtures, key=lambda x: x['kickoff_time'], reverse=True)[:4]
        future_fixtures = sorted(future_fixtures, key=lambda x: x['kickoff_time'])[:4]
        
        past_fdrs = [
            f['team_h_difficulty'] if f['team_h'] == team_id else f['team_a_difficulty']
            for f in past_fixtures
        ]
        future_fdrs = [
            f['team_h_difficulty'] if f['team_h'] == team_id else f['team_a_difficulty']
            for f in future_fixtures
        ]
        
        pFDR = sum(past_fdrs) / len(past_fdrs) if past_fdrs else None
        fFDR = sum(future_fdrs) / len(future_fdrs) if future_fdrs else None
        
        return pFDR, fFDR

    def poisson_prob(self, l, k):
        return (l**k * exp(-l)) / factorial(k)

    def get_position_name(self, position_id):
        positions = {1: 'Goalkeepers', 2: 'Defenders', 3: 'Midfielders', 4: 'Attackers'}
        return positions[position_id]

def fetch_and_process_data_standalone():
    """Standalone function to fetch and process FPL data"""
    # Fetch data from FPL API
    bootstrap_response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    fixtures_response = requests.get('https://fantasy.premierleague.com/api/fixtures/')
    
    bootstrap_data = bootstrap_response.json()
    fixtures_data = fixtures_response.json()
    
    players = bootstrap_data['elements']
    teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
    events = bootstrap_data['events']
    
    # Check if season has started (any gameweek finished)
    season_started = any(event['finished'] for event in events)
    print(f"Season started: {season_started}")
    
    # Process player data
    player_data = {
        "Goalkeepers": [],
        "Defenders": [],
        "Midfielders": [],
        "Attackers": []
    }
    
    print(f"Processing {len(players)} players...")
    
    # Create a temporary handler instance for calculations
    temp_handler = type('TempHandler', (), {})()
    temp_handler.calculate_player_stats = FPLProxyHandler.calculate_player_stats.__get__(temp_handler)
    temp_handler.calculate_player_stats_from_totals = FPLProxyHandler.calculate_player_stats_from_totals.__get__(temp_handler)
    temp_handler.calculate_fdr = FPLProxyHandler.calculate_fdr.__get__(temp_handler)
    temp_handler.poisson_prob = FPLProxyHandler.poisson_prob.__get__(temp_handler)
    temp_handler.get_position_name = FPLProxyHandler.get_position_name.__get__(temp_handler)
    temp_handler.filter_current_season_games = FPLProxyHandler.filter_current_season_games.__get__(temp_handler)
    
    for i, player in enumerate(players):
        if i % 100 == 0:
            print(f"Processed {i}/{len(players)} players...")
            
        try:
            if season_started:
                # Fetch player history for current season
                history_url = f"https://fantasy.premierleague.com/api/element-summary/{player['id']}/"
                history_response = requests.get(history_url)
                history_data = history_response.json()
                
                # Get current season games only (filter by season and get last 4)
                current_season_games = temp_handler.filter_current_season_games(history_data['history'], events)
                last_4_games = current_season_games[-4:] if len(current_season_games) > 4 else current_season_games
                
                if len(last_4_games) == 0:
                    # No recent games - fall back to season totals
                    player_stats = temp_handler.calculate_player_stats_from_totals(player, fixtures_data)
                else:
                    # Calculate player stats from recent games
                    player_stats = temp_handler.calculate_player_stats(player, last_4_games, fixtures_data)
            else:
                # Season hasn't started - use season totals as estimates
                player_stats = temp_handler.calculate_player_stats_from_totals(player, fixtures_data)
            
            if player_stats:  # Include all valid player stats
                position = temp_handler.get_position_name(player['element_type'])
                player_data[position].append(player_stats)
                if len(player_data[position]) <= 3:  # Debug: print first few players
                    print(f"Added {player_stats['name']} to {position} with xValue: {player_stats['xValue']:.3f}")
                
        except Exception as e:
            print(f"Error processing player {player['id']}: {e}")
            continue
    
    # Sort by xValue
    for position in player_data:
        player_data[position].sort(key=lambda x: x['xValue'], reverse=True)
    
    # Update global cache
    fpl_data_cache['processed_data'] = player_data
    fpl_data_cache['last_update'] = time.time()
    print("Data processing complete!")

def preload_data():
    """Pre-load FPL data when server starts"""
    print("Pre-loading FPL data on server startup...")
    try:
        fetch_and_process_data_standalone()
        print("✅ FPL data pre-loaded successfully!")
    except Exception as e:
        print(f"⚠️ Failed to pre-load data: {e}")
        print("Data will be loaded on first request instead.")

if __name__ == '__main__':
    import os
    
    # Use environment PORT for cloud deployment, fallback to 8001 for local
    port = int(os.environ.get('PORT', 8001))
    host = '0.0.0.0' if os.environ.get('PORT') else 'localhost'
    
    # Pre-load data in background thread to avoid blocking server startup
    # Always pre-load data to avoid timeout issues
    threading.Thread(target=preload_data, daemon=True).start()
    
    server = HTTPServer((host, port), FPLProxyHandler)
    print(f"FPL Proxy server running on http://{host}:{port}")
    print(f"Access the dashboard at: http://{host}:{port}")
    server.serve_forever()
