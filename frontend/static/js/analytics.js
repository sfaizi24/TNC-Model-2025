const currentWeek = parseInt(document.querySelector('[data-week]').getAttribute('data-week')) || 10;

async function fetchWithTimeout(url, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

function showError(message, shouldRedirect = false) {
    const errorDiv = document.getElementById('teams-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    if (shouldRedirect) {
        setTimeout(() => { window.location.href = '/auth/google'; }, 2000);
    }
}

function hideError() {
    document.getElementById('teams-error').style.display = 'none';
}

async function checkSession() {
    try {
        const response = await fetchWithTimeout('/api/session-check', {}, 5000);
        if (response.status === 401) return { authenticated: false, error: null };
        const data = await response.json();
        return { authenticated: data.authenticated, error: null };
    } catch (error) {
        if (error.name === 'AbortError') return { authenticated: null, error: 'timeout' };
        if (error.message.includes('Failed to fetch')) return { authenticated: null, error: 'network' };
        return { authenticated: null, error: 'unknown' };
    }
}

async function loadTeams() {
    hideError();

    try {
        const sessionResult = await checkSession();
        if (sessionResult.error) {
            const msg = {
                timeout: 'Session check timed out. Please refresh the page and try again.',
                network: 'Unable to connect to server. Please check your connection and refresh the page.',
            }[sessionResult.error] || 'Error checking session. Please refresh the page and try again.';
            showError(msg);
            return;
        }
        if (!sessionResult.authenticated) {
            showError('Your session has expired. Redirecting to login...', true);
            return;
        }

        const response = await fetchWithTimeout('/api/teams', {}, 10000);
        if (!response.ok) {
            if (response.status === 401) {
                showError('Your session has expired. Redirecting to login...', true);
                return;
            }
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        if (!data.teams?.length) {
            showError('No teams are available for the current week.');
            return;
        }
        const defaultSlug = data.teams[0].slug;
        populateTeamSelect(document.getElementById('team-select'), data.teams, defaultSlug);
        populateTeamSelect(document.getElementById('opponent-select'), data.teams, '', 'Auto (scheduled opponent)');
        populateTeamSelect(document.getElementById('single-team-select'), data.teams, defaultSlug);
        syncDisabledOptions();
        hideError();
    } catch (error) {
        if (error.name === 'AbortError') showError('Request timed out. Please refresh the page and try again.');
        else if (error.message.includes('Failed to fetch')) showError('Unable to connect to server. Please check your connection and try again.');
        else showError('Failed to load teams. Please refresh the page and try again.');
    }
}

function populateTeamSelect(select, teams, defaultValue, defaultLabel) {
    select.innerHTML = '';

    if (defaultLabel !== undefined) {
        const defaultOption = document.createElement('option');
        defaultOption.value = defaultValue;
        defaultOption.textContent = defaultLabel;
        select.appendChild(defaultOption);
    }

    teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team.slug;
        option.textContent = team.label;
        if (team.slug === defaultValue) option.selected = true;
        select.appendChild(option);
    });
}

function syncDisabledOptions() {
    const left = document.getElementById('team-select');
    const right = document.getElementById('opponent-select');
    const leftLocked = left.value;
    const rightLocked = right.value || null;

    Array.from(right.options).forEach(opt => {
        opt.disabled = opt.value !== '' && opt.value === leftLocked;
    });
    Array.from(left.options).forEach(opt => {
        opt.disabled = opt.value === rightLocked;
    });
}

let matchupChart = null;
let marginChart = null;
let singleTeamChart = null;

function clearMatchupArea() {
    if (matchupChart) { matchupChart.destroy(); matchupChart = null; }
    if (marginChart) { marginChart.destroy(); marginChart = null; }
    document.getElementById('matchup-header').innerHTML = '';
    document.getElementById('matchup-stats').innerHTML = '';
    document.getElementById('matchup-lineups').innerHTML = '';
    const marginWrapper = document.getElementById('margin-canvas').parentElement;
    if (marginWrapper) marginWrapper.style.display = 'none';
}

function clearSingleTeamArea() {
    if (singleTeamChart) { singleTeamChart.destroy(); singleTeamChart = null; }
    const stats = document.getElementById('single-team-stats');
    if (stats) stats.innerHTML = '';
}

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

function winProbToFairML(p) {
    if (p == null || p <= 0 || p >= 1) return null;
    const raw = p >= 0.5 ? -100 * p / (1 - p) : 100 * (1 - p) / p;
    const rounded = Math.round(raw);
    return (rounded > 0 ? '+' : '') + rounded;
}

function formatMoneyline(storedMoneyline, winProb) {
    if (storedMoneyline) return ` (${storedMoneyline})`;
    const fair = winProbToFairML(winProb);
    return fair ? ` (${fair})` : '';
}


function renderMatchupHeader(team, opponent) {
    const header = document.getElementById('matchup-header');
    const teamProb = team.win_prob != null ? (team.win_prob * 100).toFixed(1) + '%' : '—';
    const oppProb = opponent.win_prob != null ? (opponent.win_prob * 100).toFixed(1) + '%' : '—';
    header.innerHTML = `
        <div class="side team">
            <div class="label">Team</div>
            <div class="name">${escapeHtml(team.label)}</div>
            <div class="win-prob">${teamProb}</div>
            <div class="moneyline">Win prob${formatMoneyline(team.moneyline, team.win_prob)}</div>
        </div>
        <div class="side opponent">
            <div class="label">Opponent</div>
            <div class="name">${escapeHtml(opponent.label)}</div>
            <div class="win-prob">${oppProb}</div>
            <div class="moneyline">Win prob${formatMoneyline(opponent.moneyline, opponent.win_prob)}</div>
        </div>
    `;
}

function renderMatchupStats(team, opponent) {
    const container = document.getElementById('matchup-stats');
    const rows = [
        ['Floor (10th)', team.p10, opponent.p10],
        ['Median', team.p50, opponent.p50],
        ['Ceiling (90th)', team.p90, opponent.p90],
    ];
    container.innerHTML = rows.map(([label, t, o]) => `
        <div class="stat">
            <div class="stat-label">${label}</div>
            <div class="stat-row">
                <span class="team-val">${t.toFixed(1)}</span>
                <span class="opp-val">${o.toFixed(1)}</span>
            </div>
        </div>
    `).join('');
}

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'nearest', intersect: false },
    scales: {
        x: {
            type: 'linear',
            title: { display: true, text: 'Projected points', color: '#8B949E' },
            ticks: { color: '#8B949E' },
            grid: { color: 'rgba(255,255,255,0.05)' },
        },
        y: {
            title: { display: true, text: 'Probability density', color: '#8B949E' },
            ticks: { color: '#8B949E', callback: () => '' },
            grid: { color: 'rgba(255,255,255,0.05)' },
        },
    },
    plugins: {
        legend: { labels: { color: '#FFFFFF' } },
        tooltip: {
            callbacks: {
                title: (items) => `${items[0].parsed.x.toFixed(1)} pts`,
                label: (item) => `${item.dataset.label}: ${(item.parsed.y * 100).toFixed(2)}% density`,
            },
        },
    },
};

function densityDataset(label, x, y, color) {
    const fillRgba = color === '#1493FF' ? 'rgba(20, 147, 255, 0.25)' : 'rgba(255, 107, 107, 0.25)';
    return {
        label,
        data: x.map((xi, i) => ({ x: xi, y: y[i] })),
        borderColor: color,
        backgroundColor: fillRgba,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
    };
}

function renderDistributionChart(payload) {
    const ctx = document.getElementById('distribution-canvas').getContext('2d');
    const { team, opponent } = payload;

    if (opponent) {
        renderMatchupHeader(team, opponent);
        renderMatchupStats(team, opponent);
    } else {
        document.getElementById('matchup-header').innerHTML =
            `<div class="side team"><div class="label">Team</div><div class="name">${escapeHtml(team.label)}</div></div>` +
            `<div class="matchup-warning">No opponent data available for this pair.</div>`;
        document.getElementById('matchup-stats').innerHTML = '';
    }

    if (matchupChart) matchupChart.destroy();

    const datasets = [densityDataset(team.label, payload.x, team.y, '#1493FF')];
    if (opponent) datasets.push(densityDataset(opponent.label, payload.x, opponent.y, '#FF6B6B'));

    matchupChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: chartDefaults,
    });

    const marginWrapper = document.getElementById('margin-canvas').parentElement;
    if (payload.margin && opponent) {
        marginWrapper.style.display = '';
        renderMarginChart(payload.margin, team.label, opponent.label);
    } else {
        marginWrapper.style.display = 'none';
        if (marginChart) { marginChart.destroy(); marginChart = null; }
    }
}

function renderMarginChart(margin, teamLabel, opponentLabel) {
    const ctx = document.getElementById('margin-canvas').getContext('2d');
    const left = margin.left_x.map((x, i) => ({ x, y: margin.left_y[i] }));
    const right = margin.right_x.map((x, i) => ({ x, y: margin.right_y[i] }));

    if (marginChart) marginChart.destroy();

    marginChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: `${opponentLabel} wins by ≥ x`,
                    data: left,
                    borderColor: '#FF6B6B',
                    backgroundColor: 'rgba(255, 107, 107, 0.25)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: `${teamLabel} wins by ≥ x`,
                    data: right,
                    borderColor: '#1493FF',
                    backgroundColor: 'rgba(20, 147, 255, 0.25)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    borderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'nearest', intersect: false },
            scales: {
                x: {
                    type: 'linear',
                    min: -40,
                    max: 40,
                    title: { display: true, text: 'Win margin (points)', color: '#8B949E' },
                    ticks: { color: '#8B949E', stepSize: 10, callback: (v) => Math.abs(v) },
                    grid: {
                        color: (c) => c.tick.value === 0 ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.05)',
                        lineWidth: (c) => c.tick.value === 0 ? 2 : 1,
                    },
                },
                y: {
                    min: 0,
                    max: 1,
                    title: { display: true, text: 'Probability', color: '#8B949E' },
                    ticks: { color: '#8B949E', stepSize: 0.2, callback: (v) => (v * 100).toFixed(0) + '%' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                },
            },
            plugins: {
                legend: { labels: { color: '#FFFFFF' } },
                tooltip: {
                    callbacks: {
                        title: () => '',
                        label: (item) => {
                            const who = item.datasetIndex === 0 ? opponentLabel : teamLabel;
                            const margin = Math.abs(item.parsed.x).toFixed(0);
                            return `${who} wins by ≥ ${margin}: ${(item.parsed.y * 100).toFixed(1)}%`;
                        },
                    },
                },
            },
        },
    });
}

function renderSingleTeamChart(payload) {
    const ctx = document.getElementById('single-distribution-canvas').getContext('2d');
    const { team } = payload;

    const statsContainer = document.getElementById('single-team-stats');
    statsContainer.innerHTML = `
        <div class="stat">
            <div class="stat-label">Floor (10th)</div>
            <div class="stat-row"><span class="team-val">${team.p10.toFixed(1)}</span></div>
        </div>
        <div class="stat">
            <div class="stat-label">Median</div>
            <div class="stat-row"><span class="team-val">${team.p50.toFixed(1)}</span></div>
        </div>
        <div class="stat">
            <div class="stat-label">Ceiling (90th)</div>
            <div class="stat-row"><span class="team-val">${team.p90.toFixed(1)}</span></div>
        </div>
    `;

    if (singleTeamChart) singleTeamChart.destroy();
    singleTeamChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: team.label,
                data: payload.x.map((xi, i) => ({ x: xi, y: team.cdf[i] })),
                borderColor: '#1493FF',
                backgroundColor: 'rgba(20, 147, 255, 0.25)',
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'nearest', intersect: false },
            scales: {
                x: {
                    type: 'linear',
                    min: 50,
                    max: 200,
                    title: { display: true, text: 'Projected points', color: '#8B949E' },
                    ticks: { color: '#8B949E' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                },
                y: {
                    min: 0,
                    max: 1,
                    title: { display: true, text: 'Cumulative probability', color: '#8B949E' },
                    ticks: { color: '#8B949E', stepSize: 0.2, callback: (v) => (v * 100).toFixed(0) + '%' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                },
            },
            plugins: {
                legend: { labels: { color: '#FFFFFF' } },
                tooltip: {
                    callbacks: {
                        title: (items) => `${items[0].parsed.x.toFixed(1)} pts`,
                        label: (item) => `P(score ≤ x): ${(item.parsed.y * 100).toFixed(1)}%`,
                    },
                },
            },
        },
    });
}

async function loadDistribution(teamParam, opponentParam) {
    try {
        let url = `/api/team_distribution?team=${teamParam}&week=${currentWeek}`;
        if (opponentParam) url += `&opponent=${opponentParam}`;
        const response = await fetchWithTimeout(url, {}, 10000);
        if (!response.ok) {
            clearMatchupArea();
            if (response.status === 401) showError('Your session has expired. Redirecting to login...', true);
            else if (response.status === 404) showError('Matchup data is not available for the selected teams yet.');
            else showError('Failed to load matchup chart. Please refresh the page and try again.');
            return false;
        }
        const payload = await response.json();
        hideError();
        renderDistributionChart(payload);
        if (payload.opponent) {
            loadMatchupLineups(payload.team.owner, payload.opponent.owner);
        } else {
            document.getElementById('matchup-lineups').innerHTML = '';
        }
        return true;
    } catch (error) {
        clearMatchupArea();
        if (error.name === 'AbortError') showError('Matchup chart request timed out. Please try again.');
        else showError('Unable to load matchup chart. Please check your connection and try again.');
        return false;
    }
}

function splitPlayerName(name) {
    const safe = escapeHtml(name);
    const i = safe.indexOf(' ');
    return i === -1 ? safe : `${safe.slice(0, i)}<br>${safe.slice(i + 1)}`;
}

function renderLineupCol(lineup) {
    if (!lineup?.length) return '<div class="tnc-lp-col"><div class="tnc-lp-empty">No lineup</div></div>';
    const rows = lineup.map(p => `
        <div class="tnc-lp-row">
            <span class="tnc-lp-name">${splitPlayerName(p.player_name)}</span>
            <span class="tnc-lp-pos">${escapeHtml(p.position)}</span>
            <span class="tnc-lp-pts tnc-tab-num">${(p.projected_points || 0).toFixed(1)}</span>
        </div>
    `).join('');
    return `<div class="tnc-lp-col">${rows}</div>`;
}

async function loadMatchupLineups(leftOwner, rightOwner) {
    const container = document.getElementById('matchup-lineups');
    const placeholder = '<div class="tnc-lp-col"><div class="tnc-lp-empty">Loading…</div></div>';
    container.innerHTML = `${placeholder}<div class="tnc-mc-divider"></div>${placeholder}`;

    try {
        const [leftRes, rightRes] = await Promise.all([
            fetchWithTimeout(`/api/lineup/${encodeURIComponent(leftOwner)}`, {}, 10000),
            fetchWithTimeout(`/api/lineup/${encodeURIComponent(rightOwner)}`, {}, 10000),
        ]);
        if (!leftRes.ok || !rightRes.ok) return;
        const [left, right] = await Promise.all([leftRes.json(), rightRes.json()]);
        container.innerHTML = `${renderLineupCol(left)}<div class="tnc-mc-divider"></div>${renderLineupCol(right)}`;
    } catch (error) {
        console.error('Error loading matchup lineups:', error);
        container.innerHTML = '';
    }
}

async function loadSingleTeamDistribution(teamParam) {
    try {
        const url = `/api/team_distribution?team=${teamParam}&week=${currentWeek}`;
        const response = await fetchWithTimeout(url, {}, 10000);
        if (!response.ok) {
            clearSingleTeamArea();
            if (response.status === 401) showError('Your session has expired. Redirecting to login...', true);
            else if (response.status === 404) showError('Distribution data is not available for the selected team yet.');
            else showError('Failed to load team chart. Please refresh the page and try again.');
            return false;
        }
        hideError();
        renderSingleTeamChart(await response.json());
        return true;
    } catch (error) {
        clearSingleTeamArea();
        if (error.name === 'AbortError') showError('Team chart request timed out. Please try again.');
        else showError('Unable to load team chart. Please check your connection and try again.');
        return false;
    }
}

async function loadPlayers(teamParam, playersContainer) {
    try {
        const response = await fetchWithTimeout(`/api/team_players?team=${teamParam}`, {}, 10000);
        if (!response.ok) {
            if (response.status === 401) {
                showError('Your session has expired. Redirecting to login...', true);
                return;
            }
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        if (!(data.starters?.length || data.bench?.length)) {
            playersContainer.innerHTML = '<p style="color: var(--tnc-fg-muted); text-align: center; padding: 30px;">No player data available for this team.</p>';
            return;
        }

        let html = `
            <div style="overflow-x: auto;">
                <table style="width: 100%; background: var(--tnc-surface); border-radius: 12px; overflow: hidden; border: 1px solid var(--tnc-border);">
                    <thead>
                        <tr style="background: var(--tnc-bg-deep); border-bottom: 2px solid var(--tnc-blue);">
                            <th style="padding: 8px 10px; text-align: left; color: var(--tnc-blue); font-weight: 600; font-size: 12px;">Player</th>
                            <th style="padding: 8px 10px; text-align: center; color: var(--tnc-blue); font-weight: 600; font-size: 12px;">Pos</th>
                            <th style="padding: 8px 10px; text-align: right; color: var(--tnc-blue); font-weight: 600; font-size: 12px;">Proj</th>
                            <th style="padding: 8px 10px; text-align: right; color: var(--tnc-blue); font-weight: 600; font-size: 12px;">Var</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        let rowIndex = 0;
        const renderRow = (player) => {
            const muDisplay = player.mu !== null ? player.mu.toFixed(1) : '-';
            const varDisplay = player.var !== null ? player.var.toFixed(1) : '-';
            html += `
                <tr style="border-bottom: 1px solid var(--tnc-border); ${rowIndex % 2 === 0 ? 'background: rgba(20, 147, 255, 0.05);' : ''}">
                    <td style="padding: 6px 8px; color: var(--tnc-fg); font-size: 13px;">${escapeHtml(player.player_first_name)} ${escapeHtml(player.player_last_name)}</td>
                    <td style="padding: 6px 8px; text-align: center; color: var(--tnc-fg-muted); font-weight: 600; font-size: 12px;">${escapeHtml(player.position)}</td>
                    <td style="padding: 6px 8px; text-align: right; color: var(--tnc-blue); font-weight: 600; font-size: 14px;">${muDisplay}</td>
                    <td style="padding: 6px 8px; text-align: right; color: var(--tnc-fg-muted); font-weight: 600; font-size: 13px;">${varDisplay}</td>
                </tr>
            `;
            rowIndex++;
        };

        data.starters?.forEach(renderRow);
        if (data.bench?.length) {
            html += `<tr><td colspan="4" class="roster-divider">Bench Players</td></tr>`;
            data.bench.forEach(renderRow);
        }
        html += `</tbody></table></div>`;
        playersContainer.innerHTML = html;
    } catch (error) {
        const msg = error.name === 'AbortError' ? 'Request timed out. Please try again.'
            : error.message.includes('Failed to fetch') ? 'Unable to connect to server. Please check your connection.'
            : 'Error loading player data.';
        playersContainer.innerHTML = `<p style="color: #ef4444; text-align: center; padding: 30px;">${msg}</p>`;
    }
}

async function renderMatchup() {
    syncDisabledOptions();
    const left = document.getElementById('team-select').value;
    const right = document.getElementById('opponent-select').value;
    if (!left) return false;

    const teamParam = encodeURIComponent(left);
    const opponentParam = right ? encodeURIComponent(right) : null;
    return loadDistribution(teamParam, opponentParam);
}

async function renderSingleTeam() {
    const team = document.getElementById('single-team-select').value;
    if (!team) return false;
    const teamParam = encodeURIComponent(team);
    const [ok] = await Promise.all([
        loadSingleTeamDistribution(teamParam),
        loadPlayers(teamParam, document.getElementById('players-table-container')),
    ]);
    return ok;
}

let matchupsRendered = false;
let teamsRendered = false;

async function activateTab(tab) {
    document.querySelectorAll('.tnc-tab').forEach(t => {
        t.classList.toggle('is-on', t.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.style.display = panel.dataset.panel === tab ? '' : 'none';
    });

    if (tab === 'matchups' && !matchupsRendered) {
        matchupsRendered = await renderMatchup();
    }
    if (tab === 'teams' && !teamsRendered) {
        teamsRendered = await renderSingleTeam();
    }
}

function bindEvents() {
    document.getElementById('analytics-tabs').addEventListener('click', e => {
        const tab = e.target.closest('.tnc-tab');
        if (tab) activateTab(tab.dataset.tab);
    });

    document.getElementById('team-select').addEventListener('change', renderMatchup);
    document.getElementById('opponent-select').addEventListener('change', renderMatchup);
    document.getElementById('single-team-select').addEventListener('change', renderSingleTeam);
}

bindEvents();
loadTeams();
