class FPLDashboard {
    constructor() {
        this.players = [];
        this.fixtures = [];
        this.teams = {};
        this.playerData = {
            Goalkeepers: [],
            Defenders: [],
            Midfielders: [],
            Attackers: []
        };
        this.currentSort = { column: 'xvalue', direction: 'desc' };
        this.currentPosition = 'Goalkeepers';
        
        this.init();
    }

    async init() {
        try {
            await this.fetchData();
            this.renderTables();
            this.setupEventListeners();
            this.hideLoading();
            this.updateLastUpdated();
        } catch (error) {
            this.showError('Failed to load FPL data. Please try again later.');
            console.error('Error initializing dashboard:', error);
        }
    }

    async fetchData() {
        try {
            console.log('Fetching FPL data...');
            
            const response = await fetch('/api/fpl-data');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                if (result.loading) {
                    // Data is being processed, show loading message and retry
                    this.showLoadingMessage(result.message);
                    // Retry after 5 seconds
                    setTimeout(() => {
                        this.fetchData();
                    }, 5000);
                    return;
                }
                throw new Error(result.error || 'Failed to fetch FPL data');
            }

            // The data is already processed by the Python backend
            this.playerData = result.data;
            this.lastUpdated = result.last_updated;
            this.cacheAge = result.cache_age_minutes;
            this.isUpdating = result.is_updating;
            
            console.log(`FPL data loaded successfully! Cache age: ${this.cacheAge} minutes`);
            
            // Show update status if data is being refreshed in background
            if (this.isUpdating) {
                this.showUpdateStatus();
            }
            
        } catch (error) {
            console.error('Error fetching FPL data:', error);
            throw new Error('Unable to fetch FPL data from proxy server.');
        }
    }

    // Poisson distribution function
    poissonProb(lambda, k) {
        return (Math.pow(lambda, k) * Math.exp(-lambda)) / this.factorial(k);
    }

    factorial(n) {
        if (n <= 1) return 1;
        return n * this.factorial(n - 1);
    }

    // Calculate pFDR and fFDR for a team
    calculateFDR(teamId) {
        const currentDate = new Date();
        const teamFixtures = this.fixtures.filter(fixture => 
            fixture.team_h === teamId || fixture.team_a === teamId
        );

        const pastFixtures = teamFixtures
            .filter(fixture => new Date(fixture.kickoff_time) < currentDate)
            .sort((a, b) => new Date(b.kickoff_time) - new Date(a.kickoff_time))
            .slice(0, 4);

        const futureFixtures = teamFixtures
            .filter(fixture => new Date(fixture.kickoff_time) >= currentDate)
            .sort((a, b) => new Date(a.kickoff_time) - new Date(b.kickoff_time))
            .slice(0, 4);

        const pastFDRs = pastFixtures.map(fixture => 
            fixture.team_h === teamId ? fixture.team_h_difficulty : fixture.team_a_difficulty
        );

        const futureFDRs = futureFixtures.map(fixture => 
            fixture.team_h === teamId ? fixture.team_h_difficulty : fixture.team_a_difficulty
        );

        const pFDR = pastFDRs.length > 0 ? pastFDRs.reduce((a, b) => a + b, 0) / pastFDRs.length : null;
        const fFDR = futureFDRs.length > 0 ? futureFDRs.reduce((a, b) => a + b, 0) / futureFDRs.length : null;

        return { pFDR, fFDR };
    }

    async fetchPlayerHistory(playerId) {
        try {
            const response = await fetch(`https://fantasy.premierleague.com/api/element-summary/${playerId}/`);
            const data = await response.json();
            return data.history.slice(-4); // Last 4 games
        } catch (error) {
            console.error(`Error fetching history for player ${playerId}:`, error);
            return [];
        }
    }

    async processPlayerData() {
        const batchSize = 10;
        const batches = [];
        
        // Split players into batches to avoid overwhelming the API
        for (let i = 0; i < this.players.length; i += batchSize) {
            batches.push(this.players.slice(i, i + batchSize));
        }

        for (const batch of batches) {
            const promises = batch.map(async (player) => {
                const history = await this.fetchPlayerHistory(player.id);
                return this.calculatePlayerStats(player, history);
            });

            const batchResults = await Promise.all(promises);
            batchResults.forEach(playerStats => {
                if (playerStats && playerStats.xValue > 0) {
                    const position = this.getPositionName(playerStats.position);
                    this.playerData[position].push(playerStats);
                }
            });

            // Add small delay between batches to be respectful to the API
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Sort all position arrays by xValue
        Object.keys(this.playerData).forEach(position => {
            this.playerData[position].sort((a, b) => b.xValue - a.xValue);
        });
    }

    calculatePlayerStats(player, history) {
        if (history.length === 0) return null;

        const fullName = `${player.first_name} ${player.second_name}`;
        const position = player.element_type;
        const teamId = player.team;
        const { pFDR, fFDR } = this.calculateFDR(teamId);

        // Calculate totals from last 4 games
        let totalXG = 0, totalXA = 0, totalXGC = 0, totalPoints = 0;
        let totalMinutes = 0, totalBonus = 0, totalSaves = 0;

        history.forEach(game => {
            totalXG += parseFloat(game.expected_goals || 0);
            totalXA += parseFloat(game.expected_assists || 0);
            totalXGC += parseFloat(game.expected_goals_conceded || 0);
            totalPoints += game.total_points || 0;
            totalMinutes += game.minutes || 0;
            totalBonus += game.bonus || 0;
            if (position === 1) { // Goalkeeper
                totalSaves += game.saves || 0;
            }
        });

        // Calculate averages
        const avgXG = totalXG / 4;
        const avgXA = totalXA / 4;
        const avgXGC = totalXGC / 4;
        const avgPoints = totalPoints / 4;
        const avgMinutes = totalMinutes / 4;
        const avgBonus = totalBonus / 4;
        const avgSaves = totalSaves / 4;

        const minutesCategory = avgMinutes === 0 ? 0 : (avgMinutes < 60 ? 1 : 2);
        const pX0 = this.poissonProb(avgXGC, 0);
        const price = player.now_cost / 10;

        let xPPG = 0;

        // Calculate xPPG based on position
        switch (position) {
            case 1: // Goalkeeper
                xPPG = 3 * avgXA + minutesCategory + avgBonus + (avgSaves / 3);
                if (avgMinutes >= 60) {
                    xPPG += 4 * pX0; // Clean sheet points
                    for (let i = 2; i < 15; i += 2) {
                        xPPG -= this.poissonProb(avgXGC, i);
                    }
                }
                break;
            case 2: // Defender
                xPPG = 6 * avgXG + 3 * avgXA + minutesCategory + avgBonus;
                if (avgMinutes >= 60) {
                    xPPG += 4 * pX0; // Clean sheet points
                    for (let i = 2; i < 15; i += 2) {
                        xPPG -= this.poissonProb(avgXGC, i);
                    }
                }
                break;
            case 3: // Midfielder
                const csPoints = minutesCategory === 2 ? pX0 : 0;
                xPPG = 5 * avgXG + 3 * avgXA + minutesCategory + avgBonus + csPoints;
                break;
            case 4: // Attacker
                xPPG = 4 * avgXG + 3 * avgXA + minutesCategory + avgBonus;
                break;
        }

        const xValue = xPPG / price;
        const value = avgPoints / price;

        return {
            name: fullName,
            position,
            xG: avgXG,
            xA: avgXA,
            xGC: avgXGC,
            bonus: avgBonus,
            minutes: avgMinutes,
            saves: avgSaves,
            xPPG,
            points: avgPoints,
            price,
            value,
            xValue,
            pFDR,
            fFDR
        };
    }

    getPositionName(positionId) {
        const positions = {
            1: 'Goalkeepers',
            2: 'Defenders',
            3: 'Midfielders',
            4: 'Attackers'
        };
        return positions[positionId];
    }

    renderTables() {
        Object.keys(this.playerData).forEach(position => {
            this.renderTable(position, this.playerData[position]);
        });
    }

    renderTable(position, players) {
        const tableId = `${position.toLowerCase()}-table`;
        const tbody = document.querySelector(`#${tableId} tbody`);
        
        if (!tbody) return;

        tbody.innerHTML = '';

        players.forEach((player, index) => {
            const row = document.createElement('tr');
            
            const cells = this.createTableCells(player, index + 1, position);
            cells.forEach(cell => row.appendChild(cell));
            
            tbody.appendChild(row);
        });
    }

    createTableCells(player, rank, position) {
        const cells = [];
        
        // Rank
        cells.push(this.createCell(rank));
        
        // Player Name
        cells.push(this.createCell(player.name));
        
        // Position-specific columns
        if (position === 'Goalkeepers') {
            cells.push(this.createCell(player.xA.toFixed(2)));
            cells.push(this.createCell(player.xGC.toFixed(2)));
            cells.push(this.createCell(player.bonus.toFixed(1)));
            cells.push(this.createCell(player.minutes.toFixed(0)));
            cells.push(this.createCell(player.saves.toFixed(1)));
        } else if (position === 'Attackers') {
            cells.push(this.createCell(player.xG.toFixed(2)));
            cells.push(this.createCell(player.xA.toFixed(2)));
            cells.push(this.createCell(player.bonus.toFixed(1)));
            cells.push(this.createCell(player.minutes.toFixed(0)));
        } else {
            cells.push(this.createCell(player.xG.toFixed(2)));
            cells.push(this.createCell(player.xA.toFixed(2)));
            cells.push(this.createCell(player.xGC.toFixed(2)));
            cells.push(this.createCell(player.bonus.toFixed(1)));
            cells.push(this.createCell(player.minutes.toFixed(0)));
        }
        
        // Common columns
        cells.push(this.createCell(player.xPPG.toFixed(2)));
        cells.push(this.createCell(player.points.toFixed(1)));
        cells.push(this.createCell(`£${player.price.toFixed(1)}`, 'price-cell'));
        
        // Value with styling
        const valueCell = this.createCell(player.value.toFixed(2));
        this.styleValueCell(valueCell, player.value);
        cells.push(valueCell);
        
        // xValue with styling
        const xValueCell = this.createCell(player.xValue.toFixed(2));
        this.styleValueCell(xValueCell, player.xValue);
        cells.push(xValueCell);
        
        // FDR columns
        const pFDRCell = this.createCell(player.pFDR ? player.pFDR.toFixed(1) : 'N/A');
        const fFDRCell = this.createCell(player.fFDR ? player.fFDR.toFixed(1) : 'N/A');
        
        if (player.pFDR) this.styleFDRCell(pFDRCell, player.pFDR);
        if (player.fFDR) this.styleFDRCell(fFDRCell, player.fFDR);
        
        cells.push(pFDRCell);
        cells.push(fFDRCell);
        
        return cells;
    }

    createCell(content, className = '') {
        const cell = document.createElement('td');
        cell.textContent = content;
        if (className) cell.className = className;
        return cell;
    }

    styleValueCell(cell, value) {
        if (value >= 0.7) {
            cell.classList.add('value-high');  // green
        } else if (value >= 0.4) {
            cell.classList.add('value-medium');  // yellow
        } else {
            cell.classList.add('value-low');  // red
        }
    }

    styleFDRCell(cell, fdr) {
        if (fdr <= 2) {
            cell.classList.add('fdr-excellent');
        } else if (fdr <= 3) {
            cell.classList.add('fdr-good');
        } else if (fdr <= 4) {
            cell.classList.add('fdr-average');
        } else {
            cell.classList.add('fdr-difficult');
        }
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const position = e.target.dataset.position;
                this.switchPosition(position);
            });
        });

        // Search functionality
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', (e) => {
            this.filterPlayers(e.target.value);
        });

        // Table sorting
        document.querySelectorAll('.stats-table th[data-sort]').forEach(header => {
            header.addEventListener('click', (e) => {
                const column = e.target.dataset.sort;
                this.sortTable(column);
            });
        });
    }

    switchPosition(position) {
        // Update active tab
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-position="${position}"]`).classList.add('active');

        // Update active section
        document.querySelectorAll('.position-section').forEach(section => section.classList.remove('active'));
        document.getElementById(position).classList.add('active');

        this.currentPosition = position;
    }

    filterPlayers(searchTerm) {
        const currentTable = document.querySelector(`#${this.currentPosition} .stats-table tbody`);
        const rows = currentTable.querySelectorAll('tr');

        rows.forEach(row => {
            const playerName = row.cells[1].textContent.toLowerCase();
            const matches = playerName.includes(searchTerm.toLowerCase());
            row.style.display = matches ? '' : 'none';
        });
    }

    sortTable(column) {
        const direction = this.currentSort.column === column && this.currentSort.direction === 'desc' ? 'asc' : 'desc';
        this.currentSort = { column, direction };

        // Update header styling
        document.querySelectorAll('.stats-table th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });
        
        const currentHeader = document.querySelector(`#${this.currentPosition} th[data-sort="${column}"]`);
        currentHeader.classList.add(direction === 'asc' ? 'sorted-asc' : 'sorted-desc');

        // Sort the data
        const sortedData = [...this.playerData[this.currentPosition]].sort((a, b) => {
            let aVal = this.getSortValue(a, column);
            let bVal = this.getSortValue(b, column);

            if (direction === 'asc') {
                return aVal - bVal;
            } else {
                return bVal - aVal;
            }
        });

        this.renderTable(this.currentPosition, sortedData);
    }

    getSortValue(player, column) {
        const columnMap = {
            rank: 0, // Will be handled separately
            name: player.name,
            xg: player.xG,
            xa: player.xA,
            xgc: player.xGC,
            bp: player.bonus,
            minutes: player.minutes,
            saves: player.saves,
            xppg: player.xPPG,
            points: player.points,
            price: player.price,
            value: player.value,
            xvalue: player.xValue,
            pfdr: player.pFDR || 999,
            ffdr: player.fFDR || 999
        };

        return columnMap[column] || 0;
    }

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';
    }

    showLoadingMessage(message) {
        document.getElementById('loading').innerHTML = `
            <div class="spinner"></div>
            <p>${message}</p>
            <p style="font-size: 14px; color: #666; margin-top: 10px;">This may take a few minutes on first load...</p>
        `;
    }

    showError(message) {
        document.getElementById('loading').innerHTML = `
            <div class="error-message">
                <h3>Error Loading FPL Data</h3>
                <p>${message}</p>
                <div style="margin-top: 15px; padding: 10px; background: #f0f9ff; border-radius: 6px; border-left: 4px solid #0ea5e9;">
                    <strong>💡 Solution:</strong> This error occurs due to CORS restrictions when opening the file directly.<br>
                    <strong>To fix this:</strong> Access the website via: <a href="http://localhost:8000" target="_blank" style="color: #0ea5e9;">http://localhost:8000</a>
                </div>
            </div>
        `;
    }

    showUpdateStatus() {
        // Create or update status banner
        let statusBanner = document.getElementById('updateStatus');
        if (!statusBanner) {
            statusBanner = document.createElement('div');
            statusBanner.id = 'updateStatus';
            statusBanner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #0ea5e9;
                color: white;
                padding: 8px;
                text-align: center;
                font-size: 14px;
                z-index: 1000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            `;
            document.body.insertBefore(statusBanner, document.body.firstChild);
        }
        
        statusBanner.innerHTML = `
            <span>🔄 Updating FPL data in background... Current data is ${this.cacheAge} minutes old</span>
        `;
        
        // Remove banner after 10 seconds
        setTimeout(() => {
            if (statusBanner) {
                statusBanner.remove();
            }
        }, 10000);
    }

    updateLastUpdated() {
        if (this.lastUpdated) {
            const lastUpdateDate = new Date(this.lastUpdated * 1000);
            const timeString = lastUpdateDate.toLocaleString('en-GB', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            document.getElementById('lastUpdated').textContent = `${timeString} (${this.cacheAge} min ago)`;
        } else {
            const now = new Date();
            const timeString = now.toLocaleString('en-GB', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            document.getElementById('lastUpdated').textContent = timeString;
        }
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new FPLDashboard();
});
