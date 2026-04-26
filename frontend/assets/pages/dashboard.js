function statusBadge(status, count) {
  if (status === 'LOST' || (count != null && count > 0 && status === 'lost')) {
    return `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>누락</span>`;
  }
  if (status === 'FOUND') {
    return `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>정상</span>`;
  }
  return `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>미감지</span>`;
}

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
      document.getElementById('system-status').textContent = `누락 ${d.summary.lost_count}건`;
      document.getElementById('system-status').className = 'px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-medium';
    }

    const tbody = document.getElementById('members-tbody');
    if (!d.members || d.members.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-slate-400">등록된 구성원이 없습니다.</td></tr>`;
    } else {
      tbody.innerHTML = d.members.map((m) => {
        const initial = esc(m.name || '?').charAt(0);
        const status = m.lost_count > 0
          ? `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>누락 ${m.lost_count}건</span>`
          : m.tag_count === 0
            ? `<span class="text-xs text-slate-400">태그 없음</span>`
            : `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>정상</span>`;
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
            <td class="px-6 py-4 text-slate-600">${m.tag_count}개 (정상 ${m.found_count} · 누락 ${m.lost_count} · 미감지 ${m.registered_count})</td>
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
    document.getElementById('members-tbody').innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-red-500">대시보드 조회 실패: ${esc(err.message)}</td></tr>`;
  }
}

async function loadMyTags() {
  const esc = smartscanLayout.escapeHtml;
  const fmt = smartscanLayout.formatDateTime;
  try {
    const res = await smartscanApi.getMyTags();
    const tbody = document.getElementById('mytags-tbody');
    const tags = (res.data && res.data.tags) || [];
    if (tags.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">등록된 태그가 없습니다.</td></tr>`;
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
    document.getElementById('mytags-tbody').innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-red-500">태그 조회 실패: ${esc(err.message)}</td></tr>`;
  }
}

document.addEventListener('DOMContentLoaded', function() {
  smartscanLayout.init({ active: 'dashboard' });
  const esc = smartscanLayout.escapeHtml;
  const fmt = smartscanLayout.formatDateTime;

  document.getElementById('notify-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const userId = document.getElementById('notify-user').value;
    const channel = document.getElementById('notify-channel').value;
    const title = document.getElementById('notify-title').value.trim();
    const message = document.getElementById('notify-message').value.trim();
    if (!userId) return smartscanLayout.toast('구성원을 선택하세요.', 'error');
    if (!title || !message) return smartscanLayout.toast('제목과 메시지를 입력하세요.', 'error');

    const btn = document.getElementById('notify-submit');
    btn.disabled = true;
    try {
      await smartscanApi.sendNotification(userId, { channel, title, message });
      smartscanLayout.toast('알림을 전송했습니다.', 'success');
      document.getElementById('notify-title').value = '';
      document.getElementById('notify-message').value = '';
    } catch (err) {
      smartscanLayout.toast(err.message || '알림 전송 실패', 'error');
    } finally {
      btn.disabled = false;
    }
  });

  loadDashboard();
  loadMyTags();
});