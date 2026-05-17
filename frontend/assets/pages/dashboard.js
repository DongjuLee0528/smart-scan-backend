// Generate status badge HTML based on tag status
function statusBadge(status, count) {
  if (status === 'LOST' || (count != null && count > 0 && status === 'lost')) {
    return `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>Missing</span>`;
  }
  if (status === 'FOUND') {
    return `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Normal</span>`;
  }
  return `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>Not detected</span>`;
}

// Load and display dashboard data including family info, stats, and member list
async function loadDashboard() {
  const esc = smartscanLayout.escapeHtml;
  try {
    const res = await smartscanApi.getDashboard();
    const d = res.data;
    document.getElementById('family-name').textContent = d.family_name || '-';
    document.getElementById('stat-total').textContent = d.summary.total_tags;
    document.getElementById('stat-found').textContent = d.summary.found_count;
    document.getElementById('stat-lost').textContent = d.summary.lost_count;
    document.getElementById('stat-members').textContent = d.summary.total_members;

    const missingCard = document.getElementById('missing-card');
    if (d.summary.lost_count > 0) {
      missingCard.classList.add('border-red-200');
      document.getElementById('system-status').textContent = `Missing ${d.summary.lost_count} items`;
      document.getElementById('system-status').className = 'px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-medium';
    }

    const tbody = document.getElementById('members-tbody');
    if (!d.members || d.members.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-slate-400">No registered members.</td></tr>`;
    } else {
      // Render member rows with dynamic status badges and item counts
      tbody.innerHTML = d.members.map((m) => {
        const initial = esc(m.name || '?').charAt(0);
        // Determine status badge based on member's item status
        const status = m.lost_count > 0
          ? `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>Missing ${m.lost_count} items</span>`
          : m.tag_count === 0
            ? `<span class="text-xs text-slate-400">No tags</span>`
            : `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Normal</span>`;
        return `
          <tr class="hover:bg-slate-50">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-[#034EA2]/10 text-[#034EA2] flex items-center justify-center font-semibold text-sm">${esc(initial)}</div>
                <div>
                  <div class="font-semibold text-slate-800">${esc(m.name)}</div>
                  <div class="text-xs text-slate-400">${esc(m.role || '')}</div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 text-slate-600">${m.tag_count} items (normal ${m.found_count} · missing ${m.lost_count} · undetected ${m.registered_count})</td>
            <td class="px-6 py-4">${status}</td>
          </tr>`;
      }).join('');
    }

    const me = smartscanApi.getUser();
    const sel = document.getElementById('notify-user');
    d.members
      .filter((m) => m.user_id && m.user_id !== (me && me.user_id))
      .forEach((m) => {
        const opt = document.createElement('option');
        opt.value = m.user_id;
        opt.textContent = `${m.name} (${m.email || '-'})`;
        sel.appendChild(opt);
      });
  } catch (err) {
    console.error(err);
    document.getElementById('members-tbody').innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-red-500">Dashboard query failed: ${esc(err.message)}</td></tr>`;
  }
}

// Load and display current user's tags with status and last seen info
async function loadMyTags() {
  const esc = smartscanLayout.escapeHtml;
  const fmt = smartscanLayout.formatDateTime;
  try {
    const res = await smartscanApi.getMyTags();
    const tbody = document.getElementById('mytags-tbody');
    const tags = (res.data && res.data.tags) || [];
    if (tags.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">No registered tags.</td></tr>`;
      return;
    }
    tbody.innerHTML = tags.map((t) => `
      <tr class="hover:bg-slate-50">
        <td class="px-6 py-3.5 text-slate-800 font-medium">${esc(t.name || t.tag_uid)}</td>
        <td class="px-6 py-3.5 text-slate-600">${esc(t.item_name || '-')}</td>
        <td class="px-6 py-3.5">${statusBadge(t.status)}</td>
        <td class="px-6 py-3.5 text-slate-500">${fmt(t.last_seen_at)}</td>
      </tr>`).join('');
  } catch (err) {
    console.error(err);
    document.getElementById('mytags-tbody').innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-red-500">Tag query failed: ${esc(err.message)}</td></tr>`;
  }
}

// Initialize dashboard page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  smartscanLayout.init({ active: 'dashboard' });
  const esc = smartscanLayout.escapeHtml;
  const fmt = smartscanLayout.formatDateTime;

  // Handle notification form submission to send alerts to family members
  document.getElementById('notify-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const userId = document.getElementById('notify-user').value;
    const channel = document.getElementById('notify-channel').value;
    const title = document.getElementById('notify-title').value.trim();
    const message = document.getElementById('notify-message').value.trim();
    if (!userId) return smartscanLayout.toast('Please select a member.', 'error');
    if (!title || !message) return smartscanLayout.toast('Please enter title and message.', 'error');

    const btn = document.getElementById('notify-submit');
    btn.disabled = true;
    try {
      await smartscanApi.sendNotification(userId, { channel, title, message });
      smartscanLayout.toast('Notification sent successfully.', 'success');
      document.getElementById('notify-title').value = '';
      document.getElementById('notify-message').value = '';
    } catch (err) {
      smartscanLayout.toast(err.message || 'Notification send failed', 'error');
    } finally {
      btn.disabled = false;
    }
  });

  loadDashboard();
  loadMyTags();
});