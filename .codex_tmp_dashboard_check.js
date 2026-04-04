
    const HINDI = document.documentElement.lang === 'hi';

    async function runVerification() {
      const btn = document.getElementById('verify-btn');
      const text = document.getElementById('btn-text');
      btn.disabled = true;
      text.textContent = HINDI ? '??????? ????...' : 'Verifying...';

      document.getElementById('empty-state').style.display = 'none';
      document.getElementById('loading-state').style.display = 'block';
      document.getElementById('chain-table').style.display = 'none';

      try {
        const response = await fetch('/api/verify');
        const data = await response.json();
        renderResults(data);
      } catch (error) {
        renderError(error.message);
      } finally {
        btn.disabled = false;
        text.textContent = HINDI ? '??????? ?????' : 'Run Verification';
      }
    }

    function renderResults(data) {
      const banner = document.getElementById('status-banner');
      const statusIcon = document.getElementById('status-icon');
      const statusTitle = document.getElementById('status-title');
      const statusSub = document.getElementById('status-sub');

      const iconMarkup = {
        intact: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 4v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V7l7-4z"></path><path d="M9.5 12.5l1.8 1.8 3.8-4.3"></path></svg>',
        tampered: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 9v4"></path><path d="M12 17h.01"></path><path d="M10.29 3.86L1.82 18A2 2 0 0 0 3.53 21h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path></svg>',
        empty: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16"></path><path d="M6 11h12"></path><path d="M9 15h6"></path><rect x="3" y="4" width="18" height="16" rx="2"></rect></svg>',
        error: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 8v5"></path><path d="M12 16h.01"></path></svg>'
      };

      const configs = {
        INTACT: {
          cls: 'intact',
          icon: iconMarkup.intact,
          title: HINDI ? '???????? ???????? ??' : 'Chain Intact',
          sub: HINDI ? '??? ??????? ???????? ???, ??? ???????? ???? ?????' : 'All records verified, no tampering detected.'
        },
        TAMPERED: {
          cls: 'tampered',
          icon: iconMarkup.tampered,
          title: HINDI ? '???????? ??? ?????? ????' : 'Chain Issues Detected',
          sub: HINDI ? `${data.tampered} ??????? ?? ??????? ?????? ???` : `${data.tampered} record(s) need review.`
        },
        EMPTY: {
          cls: 'empty',
          icon: iconMarkup.empty,
          title: HINDI ? '??????? ?????? ????' : 'No Records Yet',
          sub: HINDI ? '???????? ???? ???? ?? ??? ??????? ????? ?????' : 'Upload records to begin the chain.'
        },
        ERROR: {
          cls: 'error',
          icon: iconMarkup.error,
          title: HINDI ? '??????? ??????' : 'Verification Error',
          sub: data.error || (HINDI ? '??????? ?? ?????? ???? ?? ????' : 'Could not connect to the database.')
        }
      };

      const cfg = configs[data.status] || configs.ERROR;
      banner.className = `status-banner ${cfg.cls}`;
      statusIcon.innerHTML = cfg.icon;
      statusTitle.textContent = cfg.title;
      statusSub.textContent = cfg.sub;

      document.getElementById('stat-total').textContent = data.total ?? '—';
      document.getElementById('stat-verified').textContent = data.verified ?? '—';
      document.getElementById('stat-tampered').textContent = data.tampered ?? '—';

      const pct = data.total > 0 ? Math.round((data.verified / data.total) * 100) : '—';
      const integrityEl = document.getElementById('stat-integrity');
      integrityEl.textContent = pct === '—' ? '—' : `${pct}%`;
      integrityEl.className = `stat-num ${pct === 100 ? 'green' : pct === '—' ? '' : 'red'}`;

      document.getElementById('meta-status').value = cfg.title;
      document.getElementById('meta-verified').value = `${data.verified ?? 0} / ${data.total ?? 0}`;
      const firstIssue = (data.chain || []).find(entry => entry.status !== 'OK');
      document.getElementById('meta-issue').value = firstIssue ? (firstIssue.reason || firstIssue.status) : (HINDI ? '??? ?????? ????' : 'No active issues');
      document.getElementById('meta-note').textContent = firstIssue
        ? (firstIssue.reason || firstIssue.status)
        : (HINDI ? '??? ????? ?? ???? ???????? ????' : 'All blocks and links are verified.');
      document.getElementById('integrity-summary').textContent = cfg.sub;
      document.getElementById('integrity-badge').textContent = data.status === 'INTACT' ? '✓' : '!';

      const latestEntry = (data.chain || []).slice(-1)[0];
      const latestIssue = firstIssue || latestEntry;
      document.getElementById('snapshot-record').textContent = latestEntry ? `${latestEntry.record_id.slice(0, 8)}…` : 'Awaiting verification';
      document.getElementById('snapshot-record-note').textContent = latestEntry
        ? `Updated ${new Date(latestEntry.timestamp).toLocaleString('en-IN')}`
        : 'The most recent ledger block will appear here after verification.';
      document.getElementById('snapshot-ulpin').textContent = latestEntry?.ulpin || '—';
      document.getElementById('snapshot-ulpin-note').textContent = latestEntry
        ? `Owner token ${latestEntry.owner_token || '—'}`
        : 'Current focus record from the chain.';
      document.getElementById('snapshot-link').textContent = firstIssue?.status === 'BROKEN_LINK' ? 'Attention Needed' : 'Verified';
      document.getElementById('snapshot-link-note').textContent = firstIssue?.status === 'BROKEN_LINK'
        ? (firstIssue.reason || 'A previous hash link needs review.')
        : 'Each block points to the expected prior ledger entry.';
      document.getElementById('snapshot-hash').textContent = firstIssue?.status === 'HASH_MISMATCH' ? 'Mismatch Found' : 'Verified';
      document.getElementById('snapshot-hash-note').textContent = firstIssue?.status === 'HASH_MISMATCH'
        ? (firstIssue.reason || 'Stored hash differs from live record payload.')
        : (latestIssue?.reason || 'Stored hashes match the current record payloads.');

      const tbody = document.getElementById('chain-body');
      tbody.innerHTML = '';
      (data.chain || []).forEach((entry, index) => {
        const isOk = entry.status === 'OK';
        const isMissing = entry.status === 'MISSING_RECORD';
        const isLink = entry.status === 'BROKEN_LINK';
        const badgeCls = isOk ? 'ok' : isMissing ? 'missing' : isLink ? 'link' : 'tampered';
        const badgeTxt = isOk
          ? (HINDI ? '???' : 'OK')
          : isMissing
            ? (HINDI ? '?????????' : 'Missing')
            : isLink
              ? (HINDI ? '???? ????' : 'Broken Link')
              : (HINDI ? '??? ??????' : 'Hash Mismatch');
        const storedCls = !isOk && !isMissing ? 'hash mismatch' : 'hash';
        const expectedCls = entry.status === 'HASH_MISMATCH' ? 'hash mismatch' : 'hash';
        const timestamp = entry.timestamp ? new Date(entry.timestamp).toLocaleString('en-IN') : '—';

        tbody.innerHTML += `
          <tr>
            <td class="mono">${index + 1}</td>
            <td title="${entry.reason || entry.status}"><span class="badge ${badgeCls}">${badgeTxt}</span></td>
            <td class="mono">${entry.ulpin || '—'}</td>
            <td><span class="hash">${entry.owner_token || '—'}</span></td>
            <td title="${entry.stored_hash || ''}"><span class="${storedCls}">${short(entry.stored_hash)}</span></td>
            <td title="${entry.reason || entry.expected_hash || ''}"><span class="${expectedCls}">${short(entry.expected_hash)}</span></td>
            <td>${timestamp}</td>
          </tr>`;
      });

      document.getElementById('loading-state').style.display = 'none';
      if ((data.chain || []).length > 0) {
        document.getElementById('chain-table').style.display = 'table';
      } else {
        document.getElementById('empty-state').style.display = 'block';
      }

      if (data.verified_at) {
        document.getElementById('verified-at').textContent = `${HINDI ? '????? ???????' : 'Last verified'}: ${new Date(data.verified_at).toLocaleString('en-IN')} UTC`;
      }
    }

    function renderError(message) {
      const banner = document.getElementById('status-banner');
      banner.className = 'status-banner error';
      document.getElementById('status-icon').innerHTML = iconMarkup.error;
      document.getElementById('status-title').textContent = HINDI ? '??????? ??????' : 'Verification Error';
      document.getElementById('status-sub').textContent = message;
      document.getElementById('loading-state').style.display = 'none';
      document.getElementById('empty-state').style.display = 'block';
    }

    function short(hash) {
      if (!hash || hash === 'N/A') return hash || '—';
      return `${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}`;
    }
  
