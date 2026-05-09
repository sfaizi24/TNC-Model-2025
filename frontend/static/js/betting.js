let selectedBets = {};
let userBalance = window.userBalance;
const isAuthenticated = window.isAuthenticated;
const LOGIN_URL = '/login';

let allMatchups = [];
let allTeams = [];
let allHighestScorer = [];
let allLowestScorer = [];
let activeBetsData = [];

const lineupCache = {};

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : '⚠';
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${message}</div>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}

function setBalance(value) {
    userBalance = value;
    const display = document.getElementById('userBalance');
    if (display) display.textContent = `$${value.toFixed(2)}`;
}

function calculatePayout(amount, odds) {
    const oddsNum = parseInt(odds, 10);
    if (oddsNum > 0) return amount * (oddsNum / 100);
    return amount * (100 / Math.abs(oddsNum));
}

function paysOutText(amount, odds) {
    if (!amount || amount <= 0) return '';
    const win = calculatePayout(amount, odds);
    const total = amount + win;
    return `Pays out $${total.toFixed(2)}`;
}

document.querySelectorAll('.betting-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        document.querySelectorAll('.betting-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.betting-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

function placeBetButton(idx, prefix, handlerName) {
    if (!isAuthenticated) {
        return `<a class="btn-place-bet" href="${LOGIN_URL}">Login</a>`;
    }
    return `<button class="btn-place-bet" id="${prefix}-btn-${idx}" onclick="${handlerName}(${idx})" disabled>Place Bet</button>`;
}

function quickStakeChips(idx, prefix, oddsArg = '') {
    const handler = {
        '': 'setQuickBetAmount',
        'team': 'setQuickTeamBetAmount',
        'hs': 'setQuickHSBetAmount',
        'ls': 'setQuickLSBetAmount',
    }[prefix];
    return [10, 25, 50, 100].map(amount => {
        const args = oddsArg ? `${idx}, ${amount}, '${oddsArg}'` : `${idx}, ${amount}`;
        return `<button class="quick-bet-btn" onclick="${handler}(${args})">$${amount}</button>`;
    }).join('');
}

function setQuickBetAmount(idx, amount) {
    const input = document.getElementById(`amount-${idx}`);
    if (input) {
        input.value = amount;
        updatePotentialWin(idx);
    }
}

function setQuickTeamBetAmount(idx, amount) {
    const input = document.getElementById(`team-amount-${idx}`);
    if (input) {
        input.value = amount;
        updateTeamPotentialWin(idx);
    }
}

function setQuickHSBetAmount(idx, amount, odds) {
    const input = document.getElementById(`hs-amount-${idx}`);
    if (input) {
        input.value = amount;
        updateHighestScorerPotentialWin(idx, odds);
    }
}

function setQuickLSBetAmount(idx, amount, odds) {
    const input = document.getElementById(`ls-amount-${idx}`);
    if (input) {
        input.value = amount;
        updateLowestScorerPotentialWin(idx, odds);
    }
}

async function loadMatchups() {
    try {
        const response = await fetch('/api/matchups');
        allMatchups = await response.json();
        renderMatchups();
    } catch (error) {
        console.error('Error loading matchups:', error);
    }
}

function renderMatchups() {
    const grid = document.getElementById('matchupsGrid');
    grid.innerHTML = allMatchups.map((m, idx) => `
        <div class="matchup-card" id="matchup-card-${idx}">
            <div class="bet-strip-slot" id="matchup-strip-${idx}"></div>
            <div class="teams-container">
                <div class="team-section">
                    <div class="team-name">${m.team1_name}</div>
                    <div class="win-prob">${(m.team1_win_prob * 100).toFixed(1)}% win</div>
                    <button class="odds-button ${m.team1_ml.startsWith('+') ? 'positive-odds' : ''}"
                            onclick="selectOdds(${idx}, 'team1')"
                            id="odds-${idx}-team1">${m.team1_ml}</button>
                </div>
                <div class="vs-text">VS</div>
                <div class="team-section">
                    <div class="team-name">${m.team2_name}</div>
                    <div class="win-prob">${(m.team2_win_prob * 100).toFixed(1)}% win</div>
                    <button class="odds-button ${m.team2_ml.startsWith('+') ? 'positive-odds' : ''}"
                            onclick="selectOdds(${idx}, 'team2')"
                            id="odds-${idx}-team2">${m.team2_ml}</button>
                </div>
            </div>
            <div class="quick-bet-buttons">${quickStakeChips(idx, '')}</div>
            <div class="pays-out-line" id="potential-${idx}"></div>
            <div class="bet-controls">
                <div class="bet-input-group">
                    <input type="number" class="bet-amount-input" id="amount-${idx}"
                           placeholder="Bet $" min="0" step="0.01"
                           oninput="updatePotentialWin(${idx})">
                </div>
                ${placeBetButton(idx, 'matchup', 'placeBet')}
            </div>
            <button class="show-teams-btn" onclick='toggleLineups(event, ${idx}, ${JSON.stringify(m.team1_name)}, ${JSON.stringify(m.team2_name)})'>
                Show lineups <span class="dropdown-arrow" id="arrow-${idx}">▼</span>
            </button>
            <div class="lineups-container" id="lineups-${idx}" style="display: none;">
                <div class="lineup-grid">
                    <div class="lineup-column"><div class="lineup-loading">Loading...</div></div>
                    <div class="lineup-divider"></div>
                    <div class="lineup-column"><div class="lineup-loading">Loading...</div></div>
                </div>
            </div>
        </div>
    `).join('');
    applyBetStrips();
}

function selectOdds(matchupIdx, team) {
    const otherTeam = team === 'team1' ? 'team2' : 'team1';
    const btn1 = document.getElementById(`odds-${matchupIdx}-${team}`);
    const btn2 = document.getElementById(`odds-${matchupIdx}-${otherTeam}`);
    if (btn1.disabled) return;
    btn1.classList.add('selected');
    btn2.classList.remove('selected');
    selectedBets[matchupIdx] = { team, odds: btn1.textContent.trim() };
    updatePotentialWin(matchupIdx);
}

function updatePotentialWin(matchupIdx) {
    if (!isAuthenticated) return;
    const amount = parseFloat(document.getElementById(`amount-${matchupIdx}`).value) || 0;
    const selected = selectedBets[matchupIdx];
    const potentialDiv = document.getElementById(`potential-${matchupIdx}`);
    const btn = document.getElementById(`matchup-btn-${matchupIdx}`);

    if (selected && amount > 0) {
        potentialDiv.textContent = paysOutText(amount, selected.odds);
        btn.textContent = 'Place Bet';
        btn.disabled = false;
    } else {
        potentialDiv.textContent = '';
        btn.disabled = true;
        btn.textContent = !selected ? 'Select a Team' : 'Enter Amount';
    }
}

function updateTeamPotentialWin(teamIdx) {
    if (!isAuthenticated) return;
    const amount = parseFloat(document.getElementById(`team-amount-${teamIdx}`).value) || 0;
    const selected = selectedTeamBets[teamIdx];
    const potentialDiv = document.getElementById(`team-potential-${teamIdx}`);
    const btn = document.getElementById(`team-btn-${teamIdx}`);

    if (selected && amount > 0) {
        potentialDiv.textContent = paysOutText(amount, '+100');
        btn.textContent = 'Place Bet';
        btn.disabled = false;
    } else {
        potentialDiv.textContent = '';
        btn.disabled = true;
        btn.textContent = !selected ? 'Select Over/Under' : 'Enter Amount';
    }
}

function updateHighestScorerPotentialWin(idx, odds) {
    updateScorerPotentialWin(idx, odds, 'hs');
}

function updateLowestScorerPotentialWin(idx, odds) {
    updateScorerPotentialWin(idx, odds, 'ls');
}

function updateScorerPotentialWin(idx, odds, prefix) {
    if (!isAuthenticated) return;
    const amount = parseFloat(document.getElementById(`${prefix}-amount-${idx}`).value) || 0;
    const potentialDiv = document.getElementById(`${prefix}-potential-win-${idx}`);
    const btn = document.getElementById(`${prefix}-btn-${idx}`);

    if (amount > 0) {
        potentialDiv.textContent = paysOutText(amount, odds);
        btn.textContent = 'Place Bet';
        btn.disabled = false;
    } else {
        potentialDiv.textContent = '';
        btn.disabled = true;
        btn.textContent = 'Enter Amount';
    }
}

async function placeBet(matchupIdx) {
    const selected = selectedBets[matchupIdx];
    const amount = parseFloat(document.getElementById(`amount-${matchupIdx}`).value);

    if (!selected || !amount || amount <= 0) {
        showToast('Please select a team and enter a valid bet amount', 'error');
        return;
    }
    if (amount > userBalance) {
        showToast('Insufficient balance', 'error');
        return;
    }

    const oldBalance = userBalance;
    setBalance(userBalance - amount);

    try {
        const response = await fetch('/api/place_bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ matchup_idx: matchupIdx, team: selected.team, amount }),
        });
        const result = await response.json();
        if (result.success) {
            setBalance(result.new_balance);
            document.getElementById(`amount-${matchupIdx}`).value = '';
            document.getElementById(`odds-${matchupIdx}-team1`).classList.remove('selected');
            document.getElementById(`odds-${matchupIdx}-team2`).classList.remove('selected');
            delete selectedBets[matchupIdx];
            showToast('Bet placed!');
            loadActiveBets();
        } else {
            setBalance(oldBalance);
            showToast(result.error || 'Failed to place bet', 'error');
        }
    } catch (error) {
        console.error('Error placing bet:', error);
        setBalance(oldBalance);
        showToast('Failed to place bet', 'error');
    }
}

let selectedTeamBets = {};

async function loadTeamPerformance() {
    try {
        const response = await fetch('/api/team_performance');
        allTeams = await response.json();
        renderTeamPerformance();
    } catch (error) {
        console.error('Error loading team performance:', error);
    }
}

function renderTeamPerformance() {
    const grid = document.getElementById('teamPerformanceGrid');
    grid.innerHTML = allTeams.map((t, idx) => `
        <div class="matchup-card" id="team-card-${idx}">
            <div class="bet-strip-slot" id="team-strip-${idx}"></div>
            <div class="team-name" style="text-align: center; margin-bottom: 8px;">
                ${t.owner} O/U ${t.line.toFixed(1)}
            </div>
            <div class="teams-container">
                <div class="team-section">
                    <div class="win-prob">${(t.under_prob * 100).toFixed(1)}% win</div>
                    <button class="odds-button" onclick="selectTeamOdds(${idx}, 'under')" id="team-odds-${idx}-under">Under</button>
                </div>
                <div class="vs-text">OR</div>
                <div class="team-section">
                    <div class="win-prob">${(t.over_prob * 100).toFixed(1)}% win</div>
                    <button class="odds-button" onclick="selectTeamOdds(${idx}, 'over')" id="team-odds-${idx}-over">Over</button>
                </div>
            </div>
            <div class="quick-bet-buttons">${quickStakeChips(idx, 'team')}</div>
            <div class="pays-out-line" id="team-potential-${idx}"></div>
            <div class="bet-controls">
                <div class="bet-input-group">
                    <input type="number" class="bet-amount-input" id="team-amount-${idx}"
                           placeholder="Bet $" min="0" step="0.01"
                           oninput="updateTeamPotentialWin(${idx})">
                </div>
                ${placeBetButton(idx, 'team', 'placeTeamBet')}
            </div>
            <button class="show-teams-btn" onclick='toggleTeamLineup(event, ${idx}, ${JSON.stringify(t.owner)})'>
                Show lineup <span class="dropdown-arrow" id="team-arrow-${idx}">▼</span>
            </button>
            <div class="lineups-container" id="team-lineups-${idx}" style="display: none;">
                <div class="lineup-loading">Loading...</div>
            </div>
        </div>
    `).join('');
    applyBetStrips();
}

function selectTeamOdds(teamIdx, choice) {
    const otherChoice = choice === 'over' ? 'under' : 'over';
    const btn1 = document.getElementById(`team-odds-${teamIdx}-${choice}`);
    const btn2 = document.getElementById(`team-odds-${teamIdx}-${otherChoice}`);
    if (btn1.disabled) return;
    btn1.classList.add('selected');
    btn2.classList.remove('selected');
    selectedTeamBets[teamIdx] = { choice };
    updateTeamPotentialWin(teamIdx);
}

async function placeTeamBet(teamIdx) {
    const selected = selectedTeamBets[teamIdx];
    const amount = parseFloat(document.getElementById(`team-amount-${teamIdx}`).value);
    if (!selected || !amount || amount <= 0) {
        showToast('Please select over/under and a valid amount', 'error');
        return;
    }
    if (amount > userBalance) {
        showToast('Insufficient balance', 'error');
        return;
    }
    const oldBalance = userBalance;
    setBalance(userBalance - amount);
    try {
        const response = await fetch('/api/place_bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet_type: 'team_ou', team_idx: teamIdx, choice: selected.choice, amount }),
        });
        const result = await response.json();
        if (result.success) {
            setBalance(result.new_balance);
            document.getElementById(`team-amount-${teamIdx}`).value = '';
            document.getElementById(`team-odds-${teamIdx}-over`).classList.remove('selected');
            document.getElementById(`team-odds-${teamIdx}-under`).classList.remove('selected');
            delete selectedTeamBets[teamIdx];
            showToast('Bet placed!');
            loadActiveBets();
        } else {
            setBalance(oldBalance);
            showToast(result.error || 'Failed to place bet', 'error');
        }
    } catch (error) {
        console.error('Error placing team bet:', error);
        setBalance(oldBalance);
        showToast('Failed to place bet', 'error');
    }
}

function renderScorerGrid(prefix, gridId, data) {
    const grid = document.getElementById(gridId);
    const handlerSelect = prefix === 'hs' ? 'selectHighestScorer' : 'selectLowestScorer';
    const handlerPlace = prefix === 'hs' ? 'placeHighestScorerBet' : 'placeLowestScorerBet';
    const handlerToggle = prefix === 'hs' ? 'toggleHighestScorerLineup' : 'toggleLowestScorerLineup';
    const handlerRender = prefix === 'hs' ? renderHighestScorerLineup : renderLowestScorerLineup;

    grid.innerHTML = data.map((t, idx) => {
        const proj = t.proj_pts !== null && t.proj_pts !== undefined ? `${t.proj_pts.toFixed(1)} pts` : '—';
        return `
            <div class="matchup-card" id="${prefix}-card-${idx}">
                <div class="bet-strip-slot" id="${prefix}-strip-${idx}"></div>
                <button class="scorer-button ${t.odds.startsWith('+') ? '' : ''}"
                        id="${prefix}-select-${idx}"
                        onclick="${handlerSelect}(${idx})">
                    <div>
                        <div class="scorer-owner">${t.owner}</div>
                        <div class="scorer-prob">${t.win_prob}% win</div>
                    </div>
                    <div class="scorer-prob">${proj}</div>
                    <div class="scorer-odds ${t.odds.startsWith('+') ? 'positive-odds' : ''}">${t.odds}</div>
                </button>
                <div class="quick-bet-buttons">${quickStakeChips(idx, prefix, t.odds)}</div>
                <div class="pays-out-line" id="${prefix}-potential-win-${idx}"></div>
                <div class="bet-controls">
                    <div class="bet-input-group">
                        <input type="number" class="bet-amount-input" id="${prefix}-amount-${idx}"
                               placeholder="Bet $" min="0" step="0.01"
                               oninput="${prefix === 'hs' ? 'updateHighestScorerPotentialWin' : 'updateLowestScorerPotentialWin'}(${idx}, '${t.odds}')">
                    </div>
                    ${placeBetButton(idx, prefix, handlerPlace)}
                </div>
                <button class="show-teams-btn" onclick="${handlerToggle}(event, ${idx}, '${t.owner}')">
                    Show lineup <span class="dropdown-arrow" id="${prefix}-arrow-${idx}">▼</span>
                </button>
                <div class="lineups-container" id="${prefix}-lineups-${idx}" style="display: none;">
                    <div class="lineup-loading">Loading...</div>
                </div>
            </div>
        `;
    }).join('');
    applyBetStrips();
}

async function loadHighestScorer() {
    try {
        const response = await fetch('/api/highest_scorer');
        allHighestScorer = await response.json();
        renderScorerGrid('hs', 'highestScorerGrid', allHighestScorer);
    } catch (error) {
        console.error('Error loading highest scorer:', error);
    }
}

async function loadLowestScorer() {
    try {
        const response = await fetch('/api/lowest_scorer');
        allLowestScorer = await response.json();
        renderScorerGrid('ls', 'lowestScorerGrid', allLowestScorer);
    } catch (error) {
        console.error('Error loading lowest scorer:', error);
    }
}

function selectHighestScorer(idx) {
    const btn = document.getElementById(`hs-select-${idx}`);
    if (btn.disabled) return;
    document.querySelectorAll('[id^="hs-select-"]').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
}

function selectLowestScorer(idx) {
    const btn = document.getElementById(`ls-select-${idx}`);
    if (btn.disabled) return;
    document.querySelectorAll('[id^="ls-select-"]').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
}

async function placeScorerBet(idx, prefix, dataset, betType) {
    const team = dataset[idx];
    const amount = parseFloat(document.getElementById(`${prefix}-amount-${idx}`).value);
    if (!amount || amount <= 0) {
        showToast('Please enter a valid bet amount', 'error');
        return;
    }
    if (amount > userBalance) {
        showToast('Insufficient balance', 'error');
        return;
    }
    const oldBalance = userBalance;
    setBalance(userBalance - amount);
    try {
        const response = await fetch('/api/place_bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet_type: betType, owner: team.owner, odds: team.odds, amount }),
        });
        const result = await response.json();
        if (result.success) {
            setBalance(result.new_balance);
            document.getElementById(`${prefix}-amount-${idx}`).value = '';
            document.getElementById(`${prefix}-potential-win-${idx}`).textContent = '';
            document.getElementById(`${prefix}-select-${idx}`).classList.remove('selected');
            showToast('Bet placed!');
            loadActiveBets();
        } else {
            setBalance(oldBalance);
            showToast(result.error || 'Failed to place bet', 'error');
        }
    } catch (error) {
        console.error('Error placing scorer bet:', error);
        setBalance(oldBalance);
        showToast('Failed to place bet', 'error');
    }
}

function placeHighestScorerBet(idx) {
    placeScorerBet(idx, 'hs', allHighestScorer, 'highest_scorer');
}

function placeLowestScorerBet(idx) {
    placeScorerBet(idx, 'ls', allLowestScorer, 'lowest_scorer');
}

async function loadActiveBets() {
    try {
        const response = await fetch('/api/my_bets');
        if (response.redirected || !response.ok) return;
        activeBetsData = await response.json();
        renderActiveBetsBar();
        applyBetStrips();
    } catch (error) {
        console.error('Error loading active bets:', error);
    }
}

function classifyBet(bet) {
    const desc = bet.description || '';
    if (desc.includes('Highest Scorer')) return 'high';
    if (desc.includes('Lowest Scorer')) return 'low';
    if (desc.includes('O/U')) return 'ou';
    return 'ml';
}

function shortBetName(bet) {
    const desc = bet.description || '';
    const kind = classifyBet(bet);
    if (kind === 'high') return `${desc.split(':')[0].trim()} • Highest`;
    if (kind === 'low') return `${desc.split(':')[0].trim()} • Lowest`;
    if (kind === 'ou') return desc.replace(':', '');
    const parts = desc.split(':');
    if (parts.length < 2) return desc;
    const teamAndOdds = parts[1].trim();
    const lastSpaceIdx = teamAndOdds.lastIndexOf(' ');
    return lastSpaceIdx > 0 ? teamAndOdds.substring(0, lastSpaceIdx) : teamAndOdds;
}

function shortBetOdds(bet) {
    const desc = bet.description || '';
    const match = desc.match(/([+-]\d+)\s*$/);
    return match ? match[1] : '';
}

function renderActiveBetsBar() {
    const container = document.getElementById('activeBetsCompact');
    if (!activeBetsData.length) {
        container.innerHTML = '';
        return;
    }
    const groups = { ml: [], ou: [], high: [], low: [] };
    activeBetsData.forEach(bet => groups[classifyBet(bet)].push(bet));

    const labels = { ml: 'ML', ou: 'O/U', high: 'HIGH', low: 'LOW' };
    container.innerHTML = Object.keys(groups)
        .filter(key => groups[key].length)
        .map(key => `
            <div class="active-bets-group">
                <div class="active-bets-group-label">${labels[key]}</div>
                <div class="active-bets-chips">
                    ${groups[key].map(bet => {
                        const odds = shortBetOdds(bet);
                        return `
                            <div class="active-bet-chip">
                                <span class="active-bet-chip-name">${shortBetName(bet)}</span>
                                ${odds ? `<span class="active-bet-chip-odds">${odds}</span>` : ''}
                                <span class="active-bet-chip-stake">$${bet.amount.toFixed(0)}</span>
                                <button class="active-bet-chip-cancel" onclick="removeBet(${bet.id})" title="Cancel">✕</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `).join('');
}

function findCardForBet(bet) {
    const desc = bet.description || '';
    const kind = classifyBet(bet);
    if (kind === 'high') {
        const owner = desc.split(':')[0].trim();
        const idx = allHighestScorer.findIndex(t => t.owner === owner);
        return idx >= 0 ? { idx, prefix: 'hs' } : null;
    }
    if (kind === 'low') {
        const owner = desc.split(':')[0].trim();
        const idx = allLowestScorer.findIndex(t => t.owner === owner);
        return idx >= 0 ? { idx, prefix: 'ls' } : null;
    }
    if (kind === 'ou') {
        const owner = desc.split(' O/U')[0].trim();
        const idx = allTeams.findIndex(t => t.owner === owner);
        return idx >= 0 ? { idx, prefix: 'team' } : null;
    }
    const matchupKey = desc.split(':')[0].trim();
    const idx = allMatchups.findIndex(m => `${m.team1_name} vs ${m.team2_name}` === matchupKey);
    return idx >= 0 ? { idx, prefix: 'matchup' } : null;
}

function applyBetStrips() {
    document.querySelectorAll('.bet-strip-slot').forEach(slot => slot.innerHTML = '');
    document.querySelectorAll('.matchup-card').forEach(card => card.classList.remove('has-bet'));
    document.querySelectorAll('.odds-button, .scorer-button').forEach(btn => btn.disabled = false);

    activeBetsData.forEach(bet => {
        const target = findCardForBet(bet);
        if (!target) return;
        const card = document.getElementById(`${target.prefix === 'matchup' ? 'matchup' : target.prefix}-card-${target.idx}`);
        const slot = document.getElementById(`${target.prefix === 'matchup' ? 'matchup' : target.prefix}-strip-${target.idx}`);
        if (!card || !slot) return;

        card.classList.add('has-bet');
        slot.innerHTML = `
            <div class="bet-placed-strip">
                <span class="bet-placed-info">Bet Placed · $${bet.amount.toFixed(2)}</span>
                <button class="bet-placed-cancel" onclick="removeBet(${bet.id})">Cancel bet</button>
            </div>
        `;

        if (target.prefix === 'matchup') {
            const b1 = document.getElementById(`odds-${target.idx}-team1`);
            const b2 = document.getElementById(`odds-${target.idx}-team2`);
            if (b1) b1.disabled = true;
            if (b2) b2.disabled = true;
        } else if (target.prefix === 'team') {
            const b1 = document.getElementById(`team-odds-${target.idx}-over`);
            const b2 = document.getElementById(`team-odds-${target.idx}-under`);
            if (b1) b1.disabled = true;
            if (b2) b2.disabled = true;
        } else {
            const btn = document.getElementById(`${target.prefix}-select-${target.idx}`);
            if (btn) btn.disabled = true;
        }
    });
}

async function removeBet(betId) {
    const bet = activeBetsData.find(b => b.id === betId);
    if (!bet) return;
    const oldBalance = userBalance;
    setBalance(userBalance + bet.amount);
    try {
        const response = await fetch(`/api/remove_bet/${betId}`, { method: 'DELETE' });
        const result = await response.json();
        if (result.success) {
            setBalance(result.new_balance);
            showToast('Bet removed');
        } else {
            setBalance(oldBalance);
            showToast(result.error || 'Failed to remove bet', 'error');
        }
    } catch (error) {
        console.error('Error removing bet:', error);
        setBalance(oldBalance);
        showToast('Failed to remove bet', 'error');
    }
    loadActiveBets();
}

async function toggleLineups(event, idx, team1Owner, team2Owner) {
    event.stopPropagation();
    const container = document.getElementById(`lineups-${idx}`);
    const arrow = document.getElementById(`arrow-${idx}`);
    if (container.style.display === 'none') {
        container.style.display = 'block';
        arrow.textContent = '▲';
        const cacheKey = `${team1Owner}-${team2Owner}`;
        if (!lineupCache[cacheKey]) {
            try {
                const [lineup1, lineup2] = await Promise.all([
                    fetch(`/api/lineup/${encodeURIComponent(team1Owner)}`).then(r => r.json()),
                    fetch(`/api/lineup/${encodeURIComponent(team2Owner)}`).then(r => r.json()),
                ]);
                lineupCache[cacheKey] = { lineup1, lineup2 };
                renderLineups(idx, lineup1, lineup2);
            } catch (error) {
                console.error('Error fetching lineups:', error);
            }
        } else {
            renderLineups(idx, lineupCache[cacheKey].lineup1, lineupCache[cacheKey].lineup2);
        }
    } else {
        container.style.display = 'none';
        arrow.textContent = '▼';
    }
}

function lineupRow(player) {
    return `
        <div class="lineup-player">
            <div class="player-name">${player.player_name}</div>
            <div class="player-stats">
                <span class="player-position">${player.position}</span>
                <span class="player-points">${player.projected_points}</span>
            </div>
        </div>
    `;
}

function renderLineups(idx, lineup1, lineup2) {
    const grid = document.getElementById(`lineups-${idx}`).querySelector('.lineup-grid');
    grid.innerHTML = `
        <div class="lineup-column">${lineup1.map(lineupRow).join('')}</div>
        <div class="lineup-divider"></div>
        <div class="lineup-column">${lineup2.map(lineupRow).join('')}</div>
    `;
}

async function toggleSingleLineup(event, idx, owner, prefix) {
    event.stopPropagation();
    const container = document.getElementById(`${prefix}-lineups-${idx}`);
    const arrow = document.getElementById(`${prefix}-arrow-${idx}`);
    if (container.style.display === 'none') {
        container.style.display = 'block';
        arrow.textContent = '▲';
        if (!lineupCache[owner]) {
            try {
                lineupCache[owner] = await fetch(`/api/lineup/${encodeURIComponent(owner)}`).then(r => r.json());
            } catch (error) {
                console.error('Error fetching lineup:', error);
                return;
            }
        }
        container.innerHTML = `<div class="single-lineup">${lineupCache[owner].map(lineupRow).join('')}</div>`;
    } else {
        container.style.display = 'none';
        arrow.textContent = '▼';
    }
}

function toggleTeamLineup(event, idx, owner) {
    return toggleSingleLineup(event, idx, owner, 'team');
}

function toggleHighestScorerLineup(event, idx, owner) {
    return toggleSingleLineup(event, idx, owner, 'hs');
}

function toggleLowestScorerLineup(event, idx, owner) {
    return toggleSingleLineup(event, idx, owner, 'ls');
}

function renderHighestScorerLineup() {}
function renderLowestScorerLineup() {}

async function initialize() {
    if (isAuthenticated) {
        await loadActiveBets();
    }
    await Promise.all([loadMatchups(), loadTeamPerformance(), loadHighestScorer(), loadLowestScorer()]);
    applyBetStrips();
}

initialize();
