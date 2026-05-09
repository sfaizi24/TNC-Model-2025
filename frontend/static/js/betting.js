const isAuth = window.isAuthenticated;
const QUICK_STAKES = [10, 25, 50, 100];

const state = {
    tab: 'ml',
    bets: [],
    balance: window.userBalance || 0,
    picks: {},
    stakes: {},
    opens: {},
    lineupCache: {},
    matchups: [],
    ous: [],
    hi: [],
    lo: [],
};

function americanToDecimal(odds) {
    const n = typeof odds === 'string' ? parseInt(odds, 10) : odds;
    return n > 0 ? 1 + n / 100 : 1 + 100 / Math.abs(n);
}

function fmtMoney(n) {
    return `$${Number(n).toFixed(2)}`;
}

function fmtOdds(odds) {
    if (odds === 'EVEN') return 'EVEN';
    const n = typeof odds === 'string' ? parseInt(odds, 10) : odds;
    return n > 0 ? `+${n}` : `${n}`;
}

function fmtPct(p) {
    return `${(p * 100).toFixed(0)}%`;
}

function classifyBet(bet) {
    const d = bet.description || '';
    if (d.includes('Highest Scorer')) return 'hi';
    if (d.includes('Lowest Scorer')) return 'lo';
    if (d.includes(' O/U ')) return 'ou';
    return 'ml';
}

function ownerOf(bet, kind) {
    const d = bet.description || '';
    if (kind === 'hi' || kind === 'lo') return d.split(':')[0].trim();
    if (kind === 'ou') return d.split(' O/U ')[0].trim();
    const after = (d.split(':')[1] || '').trim();
    const lastSpace = after.lastIndexOf(' ');
    return lastSpace > 0 ? after.substring(0, lastSpace).trim() : after;
}

function findCardForBet(bet) {
    const kind = classifyBet(bet);
    if (kind === 'hi') {
        const owner = ownerOf(bet, 'hi');
        const idx = state.hi.findIndex(s => s.owner === owner);
        return idx >= 0 ? { kind, idx } : null;
    }
    if (kind === 'lo') {
        const owner = ownerOf(bet, 'lo');
        const idx = state.lo.findIndex(s => s.owner === owner);
        return idx >= 0 ? { kind, idx } : null;
    }
    if (kind === 'ou') {
        const owner = ownerOf(bet, 'ou');
        const idx = state.ous.findIndex(o => o.owner === owner);
        return idx >= 0 ? { kind, idx } : null;
    }
    const matchupKey = (bet.description || '').split(':')[0].trim();
    const idx = state.matchups.findIndex(
        m => `${m.team1_name} vs ${m.team2_name}` === matchupKey
    );
    return idx >= 0 ? { kind, idx } : null;
}

function placedBetsForCard(kind, idx) {
    return state.bets.filter(bet => {
        const card = findCardForBet(bet);
        return card && card.kind === kind && card.idx === idx;
    });
}

function isMlSidePlaced(bet, side, matchup) {
    const picked = ownerOf(bet, 'ml');
    return side === 'team1' ? picked === matchup.team1_name : picked === matchup.team2_name;
}

function isOuSidePlaced(bet, side) {
    const tail = (bet.description || '').split(':')[1] || '';
    return side === (/Over/i.test(tail) ? 'over' : 'under');
}

function chevronSvg() {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>';
}

function renderPlacedStrip(bets) {
    if (!bets.length) return '';
    return `
        <div class="tnc-mc-placed-strip">
            ${bets.map(b => `
                <div class="tnc-mc-placed-row">
                    <span class="tnc-mc-placed-tag">Bet Placed</span>
                    <span class="tnc-mc-placed-info tnc-tab-num"><strong>${fmtMoney(b.amount)}</strong></span>
                    <button class="tnc-mc-placed-rm" data-action="cancel" data-bet-id="${b.id}">Cancel bet</button>
                </div>
            `).join('')}
        </div>
    `;
}

function renderStakeSection(key, odds) {
    if (!isAuth) {
        return `
            <div class="tnc-mc-stake">
                <div class="tnc-mc-stake-row">
                    <a class="tnc-mc-place" href="/login" style="flex:1;text-decoration:none;">Login to bet</a>
                </div>
            </div>
        `;
    }
    const stake = state.stakes[key] || '';
    const stakeNum = Number(stake) || 0;
    const payout = stakeNum > 0 ? stakeNum * americanToDecimal(odds) : 0;
    return `
        <div class="tnc-mc-stake">
            <div class="tnc-mc-quick">
                ${QUICK_STAKES.map(v => `<button data-action="quick" data-amount="${v}">$${v}</button>`).join('')}
            </div>
            <div class="tnc-mc-stake-row">
                <div class="tnc-mc-stake-field">
                    <input class="tnc-mc-input" data-action="stake" placeholder="Stake" inputmode="decimal" value="${stake}">
                    <span class="tnc-mc-payout tnc-tab-num"${payout > 0 ? '' : ' style="display:none;"'}>${payout > 0 ? `Pays out ${fmtMoney(payout)}` : ''}</span>
                </div>
                <button class="tnc-mc-place" data-action="place"${stakeNum > 0 ? '' : ' disabled'}>Place Bet</button>
            </div>
        </div>
    `;
}

function renderLineupCol(players) {
    if (!players || !players.length) {
        return '<div class="tnc-lp-col"><div class="tnc-lp-empty">No lineup</div></div>';
    }
    return `
        <div class="tnc-lp-col">
            ${players.map(p => `
                <div class="tnc-lp-row">
                    <span class="tnc-lp-name">${p.player_name}</span>
                    <span class="tnc-lp-pos">${p.position}</span>
                    <span class="tnc-lp-pts tnc-tab-num">${(p.projected_points || 0).toFixed(1)}</span>
                </div>
            `).join('')}
        </div>
    `;
}

function renderLineups(owners, solo) {
    const cols = owners.map(owner => {
        const cached = state.lineupCache[owner];
        return cached ? renderLineupCol(cached) : '<div class="tnc-lp-col"><div class="tnc-lp-empty">Loading…</div></div>';
    });
    const inner = solo ? cols[0] : `${cols[0]}<div class="tnc-mc-divider"></div>${cols[1]}`;
    return `<div class="tnc-mc-lineups${solo ? ' tnc-mc-lineups-solo' : ''}">${inner}</div>`;
}

function renderShowButton(open, solo) {
    const label = open ? (solo ? 'Hide lineup' : 'Hide lineups') : (solo ? 'Show lineup' : 'Show lineups');
    return `<button class="tnc-mc-show" data-action="show">${chevronSvg()}${label}</button>`;
}

function renderMatchupCard(m, idx) {
    const key = `ml-${idx}`;
    const placed = placedBetsForCard('ml', idx);
    const hasBet = placed.length > 0;
    const pick = state.picks[key];
    const open = state.opens[key];

    const odds1 = parseInt(m.team1_ml, 10);
    const odds2 = parseInt(m.team2_ml, 10);

    const sideHtml = (side, name, odds, prob) => {
        const placedHere = hasBet && isMlSidePlaced(placed[0], side, m);
        const cls = ['tnc-mc-odd', 'tnc-mc-odd-inline'];
        if (pick === side) cls.push('is-on');
        if (placedHere) cls.push('is-placed');
        return `
            <div class="tnc-mc-side">
                <div class="tnc-mc-name">${name}</div>
                <button class="${cls.join(' ')}" data-action="pick" data-side="${side}"${hasBet ? ' disabled' : ''}>
                    <span class="tnc-mc-odd-num tnc-tab-num">${fmtOdds(odds)}</span>
                    <span class="tnc-mc-odd-prob tnc-tab-num">${fmtPct(prob)}</span>
                </button>
            </div>
        `;
    };

    const stakeOdds = pick === 'team1' ? odds1 : odds2;
    const stakeHtml = pick && !hasBet ? renderStakeSection(key, stakeOdds) : '';

    return `
        <div class="tnc-mc${hasBet ? ' has-bet' : ''}${open ? ' is-open' : ''}" data-key="${key}">
            ${renderPlacedStrip(placed)}
            <div class="tnc-mc-teams">
                ${sideHtml('team1', m.team1_name, odds1, m.team1_win_prob)}
                <div class="tnc-mc-vs">VS</div>
                ${sideHtml('team2', m.team2_name, odds2, m.team2_win_prob)}
            </div>
            ${stakeHtml}
            ${renderShowButton(open, false)}
            ${open ? renderLineups([m.team1_name, m.team2_name], false) : ''}
        </div>
    `;
}

function renderOuCard(o, idx) {
    const key = `ou-${idx}`;
    const placed = placedBetsForCard('ou', idx);
    const hasBet = placed.length > 0;
    const pick = state.picks[key];
    const open = state.opens[key];

    const buttonHtml = (which, label) => {
        const placedHere = hasBet && isOuSidePlaced(placed[0], which);
        const cls = ['tnc-mc-odd', 'tnc-mc-odd-inline'];
        if (pick === which) cls.push('is-on');
        if (placedHere) cls.push('is-placed');
        return `
            <button class="${cls.join(' ')}" data-action="pick" data-side="${which}"${hasBet ? ' disabled' : ''}>
                <span class="tnc-mc-odd-label">${label}</span>
                <span class="tnc-mc-odd-num tnc-tab-num">${o.line.toFixed(1)}</span>
            </button>
        `;
    };

    const stakeHtml = pick && !hasBet ? renderStakeSection(key, 100) : '';

    return `
        <div class="tnc-mc${hasBet ? ' has-bet' : ''}${open ? ' is-open' : ''}" data-key="${key}">
            ${renderPlacedStrip(placed)}
            <div class="tnc-mc-name tnc-ou-name-solo">${o.owner}</div>
            <div class="tnc-ou-buttons">
                ${buttonHtml('over', 'Over')}
                ${buttonHtml('under', 'Under')}
            </div>
            ${stakeHtml}
            ${renderShowButton(open, true)}
            ${open ? renderLineups([o.owner], true) : ''}
        </div>
    `;
}

function renderScorerCard(s, idx, kind) {
    const key = `${kind}-${idx}`;
    const placed = placedBetsForCard(kind, idx);
    const hasBet = placed.length > 0;
    const picked = !!state.picks[key];
    const open = state.opens[key];

    const odds = parseInt(s.odds, 10);
    const prob = (s.win_prob || 0) / 100;
    const proj = (s.proj_pts != null) ? `${s.proj_pts.toFixed(1)} pts` : '—';

    const cls = ['tnc-mc-odd', 'tnc-mc-odd-inline', 'tnc-scorer-pick'];
    if (picked) cls.push('is-on');
    if (hasBet) cls.push('is-placed');

    const stakeHtml = picked && !hasBet ? renderStakeSection(key, odds) : '';

    return `
        <div class="tnc-mc${hasBet ? ' has-bet' : ''}${open ? ' is-open' : ''}" data-key="${key}">
            ${renderPlacedStrip(placed)}
            <div class="tnc-mc-name tnc-ou-name-solo">${s.owner}</div>
            <button class="${cls.join(' ')}" data-action="pick"${hasBet ? ' disabled' : ''}>
                <span class="tnc-mc-odd-num tnc-tab-num">${fmtOdds(odds)}</span>
                <span class="tnc-mc-odd-prob tnc-tab-num">${fmtPct(prob)}</span>
                <span class="tnc-mc-odd-prob tnc-tab-num">${proj}</span>
            </button>
            ${stakeHtml}
            ${renderShowButton(open, true)}
            ${open ? renderLineups([s.owner], true) : ''}
        </div>
    `;
}

function shortChipLabel(bet, kind) {
    const d = bet.description || '';
    if (kind === 'ml') return ownerOf(bet, 'ml');
    if (kind === 'hi' || kind === 'lo') return ownerOf(bet, kind);
    const m = d.match(/^(.*?) O\/U ([\d.]+): (Over|Under)$/);
    return m ? `${m[1]} ${m[3][0]} ${m[2]}` : d;
}

function renderActiveBets() {
    const container = document.getElementById('activeBets');
    if (!state.bets.length) {
        container.innerHTML = '';
        return;
    }
    const groups = { ml: [], ou: [], hi: [], lo: [] };
    state.bets.forEach(b => groups[classifyBet(b)].push(b));

    const labels = { ml: 'ML', ou: 'O/U', hi: 'HIGH', lo: 'LOW' };
    const visible = ['ml', 'ou', 'hi', 'lo'].filter(k => groups[k].length);

    container.innerHTML = `
        <div class="tnc-active">
            ${visible.map(k => `
                <div class="tnc-active-group">
                    <span class="tnc-active-label">${labels[k]}</span>
                    <div class="tnc-active-chips">
                        ${groups[k].map(b => `
                            <span class="tnc-active-chip">
                                <span class="tnc-active-chip-name">${shortChipLabel(b, k)}</span>
                                <span class="tnc-active-chip-odds tnc-tab-num">${fmtOdds(b.odds)}</span>
                                <span class="tnc-active-chip-stake tnc-tab-num">${fmtMoney(b.amount)}</span>
                                <button class="tnc-active-chip-rm" data-action="cancel" data-bet-id="${b.id}">Cancel</button>
                            </span>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderGrid() {
    const grid = document.getElementById('grid');
    const tab = state.tab;
    const data = tab === 'ml' ? state.matchups
        : tab === 'ou' ? state.ous
        : tab === 'hi' ? state.hi
        : state.lo;

    if (!data.length) {
        grid.innerHTML = '<p class="tnc-mc-loading">No bets available right now.</p>';
        return;
    }

    if (tab === 'ml') {
        grid.innerHTML = data.map((m, i) => renderMatchupCard(m, i)).join('');
    } else if (tab === 'ou') {
        grid.innerHTML = data.map((o, i) => renderOuCard(o, i)).join('');
    } else {
        grid.innerHTML = data.map((s, i) => renderScorerCard(s, i, tab)).join('');
    }
}

function render() {
    renderActiveBets();
    renderGrid();
}

function setBalance(value) {
    state.balance = value;
    const el = document.getElementById('userBalance');
    if (el) el.textContent = fmtMoney(value);
}

function toast(message, type = 'success') {
    const stack = document.getElementById('toastStack');
    if (!stack) return;
    const el = document.createElement('div');
    el.className = `tnc-toast is-${type}`;
    el.innerHTML = `<span class="ic">${type === 'success' ? '✓' : '⚠'}</span><span>${message}</span>`;
    stack.appendChild(el);
    setTimeout(() => {
        el.classList.add('is-removing');
        setTimeout(() => el.remove(), 240);
    }, 2400);
}

async function loadMatchups() {
    const r = await fetch('/api/matchups');
    state.matchups = await r.json();
}

async function loadOus() {
    const r = await fetch('/api/team_performance');
    state.ous = await r.json();
}

async function loadHi() {
    const r = await fetch('/api/highest_scorer');
    state.hi = await r.json();
}

async function loadLo() {
    const r = await fetch('/api/lowest_scorer');
    state.lo = await r.json();
}

async function loadBets() {
    if (!isAuth) return;
    try {
        const r = await fetch('/api/my_bets');
        if (!r.ok) return;
        state.bets = await r.json();
    } catch (e) {
        console.error('Error loading bets', e);
    }
}

async function loadLineup(owner) {
    if (state.lineupCache[owner]) return;
    const r = await fetch(`/api/lineup/${encodeURIComponent(owner)}`);
    state.lineupCache[owner] = await r.json();
}

function parseKey(key) {
    const [kind, idxStr] = key.split('-');
    return { kind, idx: parseInt(idxStr, 10) };
}

function ownersForKey(key) {
    const { kind, idx } = parseKey(key);
    if (kind === 'ml') {
        const m = state.matchups[idx];
        return [m.team1_name, m.team2_name];
    }
    if (kind === 'ou') return [state.ous[idx].owner];
    return [(kind === 'hi' ? state.hi : state.lo)[idx].owner];
}

function oddsForKey(key) {
    const { kind, idx } = parseKey(key);
    if (kind === 'ml') {
        const m = state.matchups[idx];
        return parseInt(state.picks[key] === 'team1' ? m.team1_ml : m.team2_ml, 10);
    }
    if (kind === 'ou') return 100;
    return parseInt((kind === 'hi' ? state.hi : state.lo)[idx].odds, 10);
}

function payloadForKey(key, amount) {
    const { kind, idx } = parseKey(key);
    if (kind === 'ml') {
        return { matchup_idx: idx, team: state.picks[key], amount };
    }
    if (kind === 'ou') {
        return { bet_type: 'team_ou', team_idx: idx, choice: state.picks[key], amount };
    }
    const s = (kind === 'hi' ? state.hi : state.lo)[idx];
    const betType = kind === 'hi' ? 'highest_scorer' : 'lowest_scorer';
    return { bet_type: betType, owner: s.owner, odds: s.odds, amount };
}

function handlePick(card, btn) {
    const key = card.dataset.key;
    const { kind } = parseKey(key);
    if (kind === 'hi' || kind === 'lo') {
        state.picks[key] = state.picks[key] ? null : true;
    } else {
        const side = btn.dataset.side;
        state.picks[key] = state.picks[key] === side ? null : side;
    }
    renderGrid();
}

function updatePayoutInPlace(card) {
    const key = card.dataset.key;
    const stake = Number(state.stakes[key]) || 0;
    const odds = oddsForKey(key);
    const payoutEl = card.querySelector('.tnc-mc-payout');
    const placeBtn = card.querySelector('.tnc-mc-place');

    if (payoutEl) {
        if (stake > 0) {
            payoutEl.textContent = `Pays out ${fmtMoney(stake * americanToDecimal(odds))}`;
            payoutEl.style.display = '';
        } else {
            payoutEl.textContent = '';
            payoutEl.style.display = 'none';
        }
    }
    if (placeBtn) placeBtn.disabled = !(stake > 0);
}

function handleStakeInput(card, input) {
    const key = card.dataset.key;
    const cleaned = input.value.replace(/[^0-9.]/g, '');
    if (cleaned !== input.value) input.value = cleaned;
    state.stakes[key] = cleaned;
    updatePayoutInPlace(card);
}

function handleQuick(card, amount) {
    const key = card.dataset.key;
    state.stakes[key] = String(amount);
    const input = card.querySelector('.tnc-mc-input');
    if (input) input.value = String(amount);
    updatePayoutInPlace(card);
}

async function handlePlace(card) {
    const key = card.dataset.key;
    const stake = Number(state.stakes[key]);
    if (!stake || stake <= 0) return;
    if (stake > state.balance) {
        toast('Insufficient balance', 'error');
        return;
    }

    const oldBalance = state.balance;
    setBalance(state.balance - stake);

    try {
        const r = await fetch('/api/place_bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payloadForKey(key, stake)),
        });
        const result = await r.json();
        if (result.success) {
            setBalance(result.new_balance);
            delete state.picks[key];
            delete state.stakes[key];
            await loadBets();
            render();
            toast('Bet placed!');
        } else {
            setBalance(oldBalance);
            toast(result.error || 'Failed to place bet', 'error');
        }
    } catch (e) {
        console.error('Error placing bet', e);
        setBalance(oldBalance);
        toast('Failed to place bet', 'error');
    }
}

async function handleCancel(betId) {
    const bet = state.bets.find(b => b.id === betId);
    if (!bet) return;

    const oldBalance = state.balance;
    setBalance(state.balance + bet.amount);

    try {
        const r = await fetch(`/api/remove_bet/${betId}`, { method: 'DELETE' });
        const result = await r.json();
        if (result.success) {
            setBalance(result.new_balance);
            await loadBets();
            render();
            toast('Bet removed');
        } else {
            setBalance(oldBalance);
            toast(result.error || 'Failed to remove bet', 'error');
        }
    } catch (e) {
        console.error('Error removing bet', e);
        setBalance(oldBalance);
        toast('Failed to remove bet', 'error');
    }
}

async function handleShow(card) {
    const key = card.dataset.key;
    state.opens[key] = !state.opens[key];

    if (state.opens[key]) {
        const owners = ownersForKey(key);
        const missing = owners.filter(o => !state.lineupCache[o]);
        if (missing.length) {
            renderGrid();
            try {
                await Promise.all(missing.map(loadLineup));
            } catch (e) {
                console.error('Error loading lineup', e);
            }
        }
    }
    renderGrid();
}

function handleTab(tab) {
    state.tab = tab;
    document.querySelectorAll('.tnc-tab').forEach(t => {
        t.classList.toggle('is-on', t.dataset.tab === tab);
    });
    renderGrid();
}

function bindEvents() {
    document.getElementById('tabs').addEventListener('click', e => {
        const tab = e.target.closest('.tnc-tab');
        if (tab) handleTab(tab.dataset.tab);
    });

    document.body.addEventListener('click', e => {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        const action = target.dataset.action;
        if (action === 'cancel') {
            handleCancel(parseInt(target.dataset.betId, 10));
            return;
        }
        const card = target.closest('.tnc-mc');
        if (!card) return;
        if (target.disabled) return;
        if (action === 'pick') handlePick(card, target);
        else if (action === 'quick') handleQuick(card, parseInt(target.dataset.amount, 10));
        else if (action === 'place') handlePlace(card);
        else if (action === 'show') handleShow(card);
    });

    document.body.addEventListener('input', e => {
        if (e.target.dataset.action !== 'stake') return;
        const card = e.target.closest('.tnc-mc');
        if (card) handleStakeInput(card, e.target);
    });
}

async function init() {
    bindEvents();
    await Promise.all([loadMatchups(), loadOus(), loadHi(), loadLo()]);
    if (isAuth) await loadBets();
    render();
}

init();
