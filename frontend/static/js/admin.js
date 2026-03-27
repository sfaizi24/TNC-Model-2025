    let currentWeek = null;
    let currentPeriodData = null;

    async function getCurrentWeek() {
        try {
            const periodsResponse = await fetch('/api/admin/betting_periods');
            const periods = await periodsResponse.json();

            const unsettledPeriods = periods.filter(p => !p.is_settled);
            if (unsettledPeriods.length > 0) {
                currentPeriodData = unsettledPeriods[0];
                return unsettledPeriods[0].week;
            }

            return 10;
        } catch (error) {
            console.error('Error getting current week:', error);
            return 10;
        }
    }

    function updateActiveWeekBanner(periods) {
        const unsettledPeriod = periods.find(p => !p.is_settled);

        if (!unsettledPeriod) {
            document.getElementById('activeWeekNum').textContent = '--';
            document.getElementById('activeWeekStatus').innerHTML = `
                <span class="status-dot settled"></span>
                <span>No Active Period</span>
            `;
            document.getElementById('activeWeekStatus').className = 'status-badge settled';
            document.getElementById('lockCountdown').textContent = 'Create a new betting period to enable betting';
            document.getElementById('quickActions').innerHTML = `
                <button class="btn btn-success btn-sm" onclick="suggestNextWeek()">Create Next Week</button>
            `;
            return;
        }

        currentPeriodData = unsettledPeriod;
        const week = unsettledPeriod.week;
        const isLocked = unsettledPeriod.is_locked;
        const lockTime = new Date(unsettledPeriod.lock_time);
        const now = new Date();

        document.getElementById('activeWeekNum').textContent = week;

        if (isLocked) {
            document.getElementById('activeWeekStatus').innerHTML = `
                <span class="status-dot locked"></span>
                <span>Locked</span>
            `;
            document.getElementById('activeWeekStatus').className = 'status-badge locked';
            document.getElementById('lockCountdown').textContent = 'Bets are locked - waiting for settlement';
            document.getElementById('quickActions').innerHTML = `
                <button class="btn btn-warning btn-sm" onclick="unlockPeriod(${week})">Unlock Betting</button>
                <button class="btn btn-outline btn-sm" onclick="document.getElementById('settleWeekNumber').focus()">Settle Week</button>
            `;
        } else {
            document.getElementById('activeWeekStatus').innerHTML = `
                <span class="status-dot open"></span>
                <span>Open for Betting</span>
            `;
            document.getElementById('activeWeekStatus').className = 'status-badge open';

            // Calculate time remaining
            const timeDiff = lockTime - now;
            if (timeDiff > 0) {
                const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
                const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const mins = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));

                let countdown = 'Locks in ';
                if (days > 0) countdown += `${days}d `;
                if (hours > 0) countdown += `${hours}h `;
                countdown += `${mins}m`;

                document.getElementById('lockCountdown').textContent = countdown;
            } else {
                document.getElementById('lockCountdown').textContent = 'Lock time passed - will lock on next action';
            }

            document.getElementById('quickActions').innerHTML = `
                <button class="btn btn-outline btn-sm" onclick="suggestNextWeek()">Setup Week ${week + 1}</button>
            `;
        }
    }

    function suggestNextWeek() {
        const nextWeek = currentPeriodData ? currentPeriodData.week + 1 : 14;
        document.getElementById('periodWeek').value = nextWeek;
        document.getElementById('periodWeek').focus();
    }

    async function loadBettingPeriods() {
        try {
            const response = await fetch('/api/admin/betting_periods');
            const periods = await response.json();

            // Update the active week banner
            updateActiveWeekBanner(periods);

            if (periods.length === 0) {
                document.getElementById('periodsTable').innerHTML = '<p style="color: var(--text-secondary);">No betting periods set</p>';
                return;
            }

            let html = '<table><thead><tr><th>Week</th><th>Lock Time</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
            periods.forEach(period => {
                const isActive = !period.is_settled && !periods.some(p => !p.is_settled && p.week > period.week);
                let statusClass = period.is_settled ? 'settled' : (period.is_locked ? 'locked' : 'open');
                let statusLabel = period.is_settled ? 'Settled' : (period.is_locked ? 'Locked' : 'Open');
                let unlockBtn = period.is_locked && !period.is_settled ?
                    `<button class="btn btn-warning btn-sm" onclick="unlockPeriod(${period.week})">Unlock</button>` :
                    '';
                let activeIndicator = isActive ? ' (Active)' : '';
                html += `<tr class="${isActive ? 'active-row' : ''}">
                    <td>Week ${period.week}${activeIndicator}</td>
                    <td>${period.lock_time}</td>
                    <td><span class="status-badge ${statusClass}"><span class="status-dot ${statusClass}"></span>${statusLabel}</span></td>
                    <td>${unlockBtn}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('periodsTable').innerHTML = html;
        } catch (error) {
            console.error('Error loading betting periods:', error);
            document.getElementById('periodsTable').innerHTML = '<p style="color: #ff4444;">Error loading periods</p>';
        }
    }

    async function loadPendingBets() {
        try {
            const response = await fetch(`/api/admin/pending_bets?week=${currentWeek}`);
            const bets = await response.json();

            if (bets.length === 0) {
                document.getElementById('pendingBetsTable').innerHTML = '<p style="color: var(--text-secondary);">No pending bets for this week</p>';
                return;
            }

            let html = '<table><thead><tr><th>User</th><th>Description</th><th>Amount</th><th>Odds</th><th>Actions</th></tr></thead><tbody>';
            bets.forEach(bet => {
                html += `<tr>
                    <td>${bet.user_id.substring(0, 8)}...</td>
                    <td>${bet.description}</td>
                    <td>$${bet.amount.toFixed(2)}</td>
                    <td>${bet.odds}</td>
                    <td>
                        <button class="btn btn-success btn-sm" onclick="settleBet(${bet.id}, true)">Win</button>
                        <button class="btn btn-danger btn-sm" onclick="settleBet(${bet.id}, false)">Loss</button>
                    </td>
                </tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('pendingBetsTable').innerHTML = html;
        } catch (error) {
            console.error('Error loading pending bets:', error);
            document.getElementById('pendingBetsTable').innerHTML = '<p style="color: #ff4444;">Error loading bets</p>';
        }
    }

    document.getElementById('setPeriodForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const week = document.getElementById('periodWeek').value;
        const lockTime = document.getElementById('periodLockTime').value;

        try {
            const response = await fetch('/api/admin/set_betting_period', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week, lock_time: lockTime })
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('setPeriodMessage').innerHTML = '<div class="message message-success">Betting period set successfully!</div>';
                loadBettingPeriods();
            } else {
                document.getElementById('setPeriodMessage').innerHTML = `<div class="message message-error">${result.error}</div>`;
            }
        } catch (error) {
            console.error('Error setting betting period:', error);
            document.getElementById('setPeriodMessage').innerHTML = '<div class="message message-error">Error setting betting period</div>';
        }
    });

    async function settleBet(betId, won) {
        try {
            const response = await fetch('/api/admin/settle_bet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bet_id: betId, won: won })
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('settleMessage').innerHTML = `<div class="message message-success">Bet settled as ${won ? 'WON' : 'LOST'}!</div>`;
                loadPendingBets();
            } else {
                document.getElementById('settleMessage').innerHTML = `<div class="message message-error">${result.error}</div>`;
            }
        } catch (error) {
            console.error('Error settling bet:', error);
            document.getElementById('settleMessage').innerHTML = '<div class="message message-error">Error settling bet</div>';
        }
    }

    document.getElementById('settleWeekForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const week = document.getElementById('settleWeekNumber').value;

        try {
            const response = await fetch('/api/admin/settle_week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week: parseInt(week) })
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('settleWeekMessage').innerHTML = '<div class="message message-success">Week marked as settled!</div>';
                loadBettingPeriods();
            } else {
                document.getElementById('settleWeekMessage').innerHTML = `<div class="message message-error">${result.error}</div>`;
            }
        } catch (error) {
            console.error('Error settling week:', error);
            document.getElementById('settleWeekMessage').innerHTML = '<div class="message message-error">Error settling week</div>';
        }
    });

    async function unlockPeriod(week) {
        console.log('Unlock period called for week:', week);

        if (!confirm(`Are you sure you want to unlock Week ${week}? Users will be able to place and remove bets again.`)) {
            console.log('User cancelled unlock');
            return;
        }

        console.log('Sending unlock request...');

        try {
            const response = await fetch('/api/admin/unlock_period', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week: week })
            });

            console.log('Response status:', response.status);

            const result = await response.json();
            console.log('Response data:', result);

            if (result.success) {
                alert(`Week ${week} unlocked successfully!`);
                loadBettingPeriods();
            } else {
                alert('Error unlocking period: ' + result.error);
            }
        } catch (error) {
            console.error('Error unlocking period:', error);
            alert('Error unlocking period: ' + error.message);
        }
    }

    async function initializeAdmin() {
        currentWeek = await getCurrentWeek();
        document.getElementById('currentWeek').textContent = currentWeek;
        document.getElementById('periodWeek').value = currentWeek;
        document.getElementById('settleWeekNumber').value = currentWeek;

        loadBettingPeriods();
        loadPendingBets();
    }

    initializeAdmin();