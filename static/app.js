const formatNumber = new Intl.NumberFormat('th-TH');
const evidenceDate = new Intl.DateTimeFormat('th-TH-u-ca-gregory', { day: 'numeric', month: 'short', year: 'numeric' });
const shortMonth = new Intl.DateTimeFormat('th-TH-u-ca-gregory', { month: 'short' });
const percent = (value) => value == null ? 'รอข้อมูล' : `${Math.round(value * 100)}%`;
const rate = (value) => value == null ? 'รอข้อมูล' : `${(Number(value) * 100).toFixed(2)}%`;
const formatDate = (value) => value ? evidenceDate.format(new Date(`${value}T00:00:00`)) : '—';
const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
let previewedFile = null;
let loadedTechnicianId = null;

const routes = {
  dashboard: {
    eyebrow: 'PERFORMANCE DASHBOARD',
    title: 'ผลการดำเนินงานสะสม',
    description: 'ติดตามคุณภาพงานจากข้อมูลสะสม โดยแยกแหล่งข้อมูลของแต่ละตัวชี้วัดชัดเจน',
  },
  overview: {
    eyebrow: 'OPERATIONAL OVERVIEW',
    title: 'ภาพรวมการติดตามช่าง',
    description: 'ตรวจสอบ Action และหลักฐานที่ยังต้องติดตามก่อนปิดเคส',
  },
  watchlist: {
    eyebrow: 'WATCHLIST',
    title: 'ทีมที่ต้องติดตาม · สิงหาคม 2026',
    description: 'รอบทดสอบรายเดือนตามเกณฑ์ Combined Rate และจำนวน Order ที่ได้รับเรื่อง',
  },
  import: {
    eyebrow: 'EVIDENCE-FIRST IMPORT',
    title: 'นำเข้าข้อมูล',
    description: 'ตรวจ Preview และหลักฐานก่อนบันทึกทุกครั้ง',
  },
  technician: {
    eyebrow: 'TECHNICIAN PROFILE',
    title: 'ข้อมูลรายช่าง',
    description: 'สรุปผลงานและตรวจสอบประวัติงานรายช่างจากหลักฐานต้นทาง',
  },
};

function setRoute() {
  const requestedRoute = window.location.hash.slice(1);
  const technicianMatch = requestedRoute.match(/^technician\/([^/]+)$/);
  const route = technicianMatch ? 'technician' : (routes[requestedRoute] ? requestedRoute : 'dashboard');
  if (!requestedRoute || (route !== 'technician' && route !== requestedRoute)) history.replaceState(null, '', `#${route}`);
  const meta = routes[route];
  document.querySelector('#pageEyebrow').textContent = meta.eyebrow;
  document.querySelector('#pageTitle').textContent = meta.title;
  document.querySelector('#pageDescription').textContent = meta.description;
  document.querySelectorAll('[data-route-section]').forEach((section) => {
    section.hidden = section.dataset.routeSection !== route;
  });
  document.querySelectorAll('nav a[data-route]').forEach((link) => {
    link.classList.toggle('active', link.dataset.route === (route === 'technician' ? 'watchlist' : route));
  });
  if (technicianMatch) {
    const technicianId = decodeURIComponent(technicianMatch[1]);
    if (technicianId !== loadedTechnicianId) loadTechnicianProfile(technicianId).catch(showProfileError);
  }
}

async function loadDashboard() {
  const response = await fetch('/api/dashboard');
  if (!response.ok) throw new Error('ไม่สามารถโหลดข้อมูลได้');
  const data = await response.json();
  document.querySelector('#mode').textContent = data.mode === 'demo' ? 'โหมดตัวอย่าง' : 'ข้อมูลจากฐานจริง';
  document.querySelector('#ytdTitle').textContent = `ผลการดำเนินงานสะสมปี ${data.summary.reporting_year || 'ปัจจุบัน'}`;
  const monthly = data.monthly || [];
  const last = monthly.at(-1), previous = monthly.at(-2);
  const cards = [
    ['Jobs', 'jobs', data.summary.jobs, 'Job Data', data.coverage?.jobs_through, true],
    ['Complaints', 'complaint_cases', data.summary.complaint_cases, 'Complaint Log', data.coverage?.complaints_through, false],
    ['Reworks', 'rework_cases', data.summary.rework_cases, 'Complaint Log', data.coverage?.complaints_through, false],
    ['QC Fails', 'qc_fail_cases', data.summary.qc_fail_cases, 'Job Data', data.coverage?.jobs_through, false],
  ];
  const operationalCards = [
    ['Action ที่ยังไม่ปิด', formatNumber.format(data.summary.open_actions), 'ต้องกำหนดหรือดำเนินการติดตาม', 'warning'],
    ['Evidence รอตรวจ', formatNumber.format(data.summary.pending_evidence), 'ยังไม่สรุปว่าเคสปิดหรือไม่มีปัญหา', 'alert'],
  ];
  document.querySelector('#ytdMetrics').innerHTML = cards.map(([label, key, total, source, through, higherIsBetter]) => {
    let trend = 'รายเดือนยังไม่มีข้อมูล', tone = 'neutral';
    if (last && previous && previous[key] > 0 && through?.slice(0, 7) === last.month.slice(0, 7)) {
      const delta = (last[key] - previous[key]) / previous[key] * 100;
      const monthStart = new Date(`${last.month}T00:00:00`);
      const lastDay = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
      const completeMonth = Number(through.slice(-2)) === lastDay;
      tone = completeMonth && delta !== 0 ? ((delta > 0) === higherIsBetter ? 'good' : 'bad') : 'neutral';
      trend = `${delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} ${Math.abs(delta).toFixed(1)}% ${shortMonth.format(monthStart)} เทียบเดือนก่อน${completeMonth ? '' : ' · อาจไม่ครบเดือน'}`;
    }
    return `<article class="metric dashboard-kpi"><p>${label}</p><strong>${formatNumber.format(total ?? 0)}</strong><div class="kpi-bottom"><span class="kpi-trend ${tone}">${escapeHtml(trend)}</span><small>${source}</small></div></article>`;
  }).join('');
  document.querySelector('#dashboardRates').innerHTML = [
    ['Complaint Rate', data.summary.complaint_rate],
    ['Rework Rate', data.summary.rework_rate],
    ['QC Fail Rate', data.summary.qc_fail_rate],
  ].map(([label, value]) => `<span>${label} <strong>${rate(value)}</strong></span>`).join('');
  document.querySelector('#operationalMetrics').innerHTML = operationalCards.map(([label, value, detail, tone]) => `<article class="metric ${tone}"><p>${label}</p><strong>${value}</strong><small>${detail}</small></article>`).join('');
  renderDashboardChart(monthly, data.coverage || {}, data.mode);
}

function renderDashboardChart(monthly, coverage, mode) {
  const target = document.querySelector('#dashboardChart');
  const description = document.querySelector('#dashboardCoverage');
  const rows = document.querySelector('#dashboardChartData tbody');
  if (!monthly.length) {
    target.innerHTML = '<div class="chart-empty">ยังไม่มีข้อมูลรายเดือนจากฐานจริงสำหรับแสดงกราฟ</div>';
    rows.innerHTML = '';
    description.textContent = mode === 'demo' ? 'โหมดตัวอย่างไม่มีกราฟรายเดือน: ไม่สร้างแนวโน้มจากข้อมูลสมมติ' : 'กราฟจะแสดงเมื่อมี Job Data หรือ Complaint Log ของปีนี้';
    return;
  }
  const width = 840, height = 325, left = 55, right = 55, top = 38, bottom = 49;
  const plotWidth = width - left - right, plotHeight = height - top - bottom, band = plotWidth / monthly.length;
  const niceScale = values => {
    const highest = Math.max(1, ...values), base = Math.max(1, 10 ** Math.floor(Math.log10(highest / 4)));
    return Math.ceil(highest / 4 / base) * base * 4;
  };
  const maxJobs = niceScale(monthly.map(item => item.jobs));
  const maxRework = niceScale(monthly.map(item => item.rework_cases));
  const lastReworkMonth = coverage.complaints_through?.slice(0, 7);
  const x = index => left + band * (index + .5);
  const yJobs = value => top + plotHeight * (1 - value / maxJobs);
  const yRework = value => top + plotHeight * (1 - value / maxRework);
  const grid = Array.from({length:5}, (_, i) => {
    const jobs = maxJobs / 4 * i, reworks = maxRework / 4 * i;
    return `<line x1="${left}" x2="${width-right}" y1="${yJobs(jobs)}" y2="${yJobs(jobs)}" stroke="#e2e8f0"/><text x="${left-12}" y="${yJobs(jobs)+4}" text-anchor="end" fill="#64748b" font-size="10" font-family="Arial Rounded MT, Arial, sans-serif">${formatNumber.format(jobs)}</text><text x="${width-right+12}" y="${yRework(reworks)+4}" fill="#926000" font-size="10" font-family="Arial Rounded MT, Arial, sans-serif">${formatNumber.format(reworks)}</text>`;
  }).join('');
  const bars = monthly.map((item, i) => {
    const barWidth = Math.min(46, band * .52);
    const label = shortMonth.format(new Date(`${item.month}T00:00:00`));
    return `<rect x="${x(i)-barWidth/2}" y="${yJobs(item.jobs)}" width="${barWidth}" height="${top+plotHeight-yJobs(item.jobs)}" rx="5" fill="${i === monthly.length-1 ? '#2149d9' : '#2d5cf6'}"><title>${escapeHtml(label)}: ${formatNumber.format(item.jobs)} Jobs</title></rect><text x="${x(i)}" y="${height-14}" text-anchor="middle" fill="#64748b" font-size="11" font-family="Thonburi, Sarabun, sans-serif">${escapeHtml(label)}</text>`;
  }).join('');
  const points = monthly.map((item,i) => item.month.slice(0,7) <= (lastReworkMonth || '') ? {x:x(i),y:yRework(item.rework_cases),count:item.rework_cases} : null);
  const valid = points.filter(Boolean);
  const path = valid.slice(1).reduce((acc,point,i) => {
    const previous = valid[i], midpoint = (previous.x + point.x) / 2;
    return `${acc} C ${midpoint} ${previous.y}, ${midpoint} ${point.y}, ${point.x} ${point.y}`;
  }, valid.length ? `M ${valid[0].x} ${valid[0].y}` : '');
  const line = valid.length > 1 ? `<path d="${path}" fill="none" stroke="#b77900" stroke-width="3.5" stroke-linecap="round"/>` : '';
  const dots = valid.map(point => `<circle cx="${point.x}" cy="${point.y}" r="6" fill="#eab308" stroke="#fff" stroke-width="2.5"><title>${formatNumber.format(point.count)} Rework cases</title></circle>`).join('');
  const titles = `<text x="${left}" y="16" fill="#64748b" font-size="10" font-family="Thonburi, Sarabun, sans-serif">Jobs (งาน)</text><text x="${width-right}" y="16" text-anchor="end" fill="#926000" font-size="10" font-family="Thonburi, Sarabun, sans-serif">Rework (เคส)</text>`;
  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${grid}${titles}${bars}${line}${dots}<line id="comboHoverLine" y1="${top}" y2="${top+plotHeight}" stroke="#94a3b8" stroke-dasharray="3 4" visibility="hidden"/></svg><div class="combo-tooltip" id="comboTooltip" hidden></div>`;
  rows.innerHTML = monthly.map(item => `<tr><td>${escapeHtml(item.month)}</td><td>${formatNumber.format(item.jobs)}</td><td>${item.month.slice(0,7) <= (lastReworkMonth || '') ? formatNumber.format(item.rework_cases) : 'ยังไม่มีข้อมูล'}</td></tr>`).join('');
  description.textContent = `Job Data ล่าสุด ${formatDate(coverage.jobs_through)} · Complaint Log ล่าสุด ${formatDate(coverage.complaints_through)} · เดือนที่ข้อมูลยังไม่ครบแสดงแนวโน้มเบื้องต้น`;
  const svg = target.querySelector('svg'), tooltip = target.querySelector('#comboTooltip'), hover = target.querySelector('#comboHoverLine');
  svg.addEventListener('pointermove', event => {
    const bounds = svg.getBoundingClientRect(), cursor = (event.clientX - bounds.left) / bounds.width * width;
    if (cursor < left || cursor > width-right) { tooltip.hidden = true; hover.setAttribute('visibility','hidden'); return; }
    const i = Math.min(monthly.length-1, Math.floor((cursor-left)/band)), item = monthly[i];
    const rework = points[i] ? `${formatNumber.format(item.rework_cases)} เคส` : 'ยังไม่มีข้อมูล';
    tooltip.innerHTML = `<strong>${escapeHtml(shortMonth.format(new Date(`${item.month}T00:00:00`)))} ${item.month.slice(0,4)}</strong><span>Jobs: ${formatNumber.format(item.jobs)} งาน</span><span>Rework: ${rework}</span>`;
    tooltip.style.left = `${Math.max(6, Math.min(bounds.width-153, x(i)/width*bounds.width-70))}px`;
    tooltip.style.top = `${Math.max(32, (points[i]?.y || top+40)/height*bounds.height-86)}px`;
    tooltip.hidden = false;
    hover.setAttribute('x1',x(i)); hover.setAttribute('x2',x(i)); hover.setAttribute('visibility','visible');
  });
  svg.addEventListener('pointerleave', () => { tooltip.hidden = true; hover.setAttribute('visibility','hidden'); });
}

async function loadWatchlist() {
  const response = await fetch('/api/watchlist?month=2026-08');
  if (!response.ok) throw new Error('ไม่สามารถโหลด Watchlist เดือนสิงหาคมได้');
  const data = await response.json();
  const flagged = data.technicians.filter((tech) => ['CRITICAL', 'WATCHLIST'].includes(tech.status));
  const critical = flagged.filter((tech) => tech.status === 'CRITICAL').length;
  const watchlist = flagged.filter((tech) => tech.status === 'WATCHLIST').length;
  const flagCards = [
    ['T3 CRITICAL · RATE &gt; 10%', critical, 'critical', '!'],
    ['T2 WATCHLIST · ≥ 3 ORDERS', watchlist, 'watch', '!'],
    ['รวมทีมที่ต้องติดตาม', flagged.length, 'total', '●'],
  ];
  document.querySelector('#watchlistFlags').innerHTML = flagCards.map(([label, count, tone, icon]) => `
    <article class="watchlist-flag ${tone}"><div><p>${label}</p><strong>${data.mode === 'demo' ? '—' : formatNumber.format(count)} <small>ทีม</small></strong></div><span class="watchlist-flag__icon" aria-hidden="true">${icon}</span></article>`).join('');
  document.querySelector('#watchlistSummary').textContent = data.mode === 'demo'
    ? 'โหมดตัวอย่างยังไม่มีข้อมูลรายเดือนจากฐานจริง'
    : 'นับจากข้อมูลเดือนสิงหาคม 2026 · หนึ่งทีมอยู่ได้เพียงระดับเดียว';
  document.querySelector('#technicianRows').innerHTML = flagged.map((tech) => `
    <tr><td><a class="tech-link" href="#technician/${encodeURIComponent(tech.technician_id)}">${escapeHtml(tech.technician_id)}</a></td>
    <td><strong>${escapeHtml(tech.technician_name || '—')}</strong><br><small>${escapeHtml(tech.team || tech.vendor_name || '—')}</small></td>
    <td>${formatNumber.format(tech.jobs)}</td><td>${formatNumber.format(tech.affected_orders)}</td>
    <td>${formatNumber.format(tech.complaints)}</td><td>${formatNumber.format(tech.rework)}</td><td>${formatNumber.format(tech.qc_fail)}</td>
    <td>${tech.combined_rate == null ? 'N/A' : rate(tech.combined_rate)}</td>
    <td><span class="pill ${escapeHtml(tech.status)}">${tech.status === 'CRITICAL' ? 'T3 Critical' : 'T2 Watchlist'}</span></td>
    <td class="reason">${escapeHtml(tech.reason)}</td></tr>`).join('') || `<tr><td colspan="10">${data.mode === 'demo' ? 'ยังไม่มีข้อมูล Watchlist รายเดือนในโหมดตัวอย่าง' : 'ไม่มีทีมที่เข้าเกณฑ์ในเดือนนี้'}</td></tr>`;
}

function countCard(label, value, unit, detail, tone = '') {
  return `<article class="issue-count-card ${tone}">
    <p>${escapeHtml(label)}</p>
    <div><strong>${value == null ? '—' : formatNumber.format(value)}</strong><span>${escapeHtml(unit)}</span></div>
    <small>${escapeHtml(detail)}</small>
  </article>`;
}

function rankedInsightCard(title, items, badge, tone = '') {
  const rows = (items || []).slice(0, 3).map((item) => {
    const width = Math.max(Number(item.share || 0) * 100, 4);
    const classification = item.classification
      ? `<span class="cause-class ${escapeHtml(item.classification)}">${item.classification === 'TECHNICIAN' ? 'จากช่าง' : item.classification === 'NON_TECHNICIAN' ? 'ปัจจัยอื่น' : 'รอตรวจ'}</span>`
      : '';
    return `<li><div><span>${escapeHtml(item.label)}</span>${classification}<strong>${formatNumber.format(item.count)}</strong></div><span class="insight-bar"><i style="width:${width}%"></i></span></li>`;
  }).join('');
  return `<article class="ranked-insight-card ${tone}">
    <header><p>${escapeHtml(title)}</p><span>${escapeHtml(badge)}</span></header>
    ${rows ? `<ol>${rows}</ol>` : '<div class="insight-empty">ยังไม่มีข้อมูลที่ยืนยันแล้ว</div>'}
  </article>`;
}

function actionLevelCard(actionLevel) {
  const hasLevel = actionLevel?.level != null;
  const level = hasLevel ? Number(actionLevel.level) : 0;
  return `<article class="action-level-card level-${level}">
    <header><p>ACTION LEVEL</p><span>${hasLevel ? `LEVEL ${level}` : 'NO ACTION'}</span></header>
    <strong>${escapeHtml(actionLevel?.condition || 'หลักฐานยังไม่ครบ')}</strong>
    <p>${escapeHtml(actionLevel?.measure || 'ติดตามหลักฐานก่อนกำหนดมาตรการ')}</p>
    <small>${escapeHtml(actionLevel?.reason || 'ยังไม่มีข้อมูลเพียงพอ')}</small>
  </article>`;
}

function combinedSignalCard(profile) {
  const segments = [
    { label: 'Complaint', count: profile.complaint_cases, className: 'complaint' },
    { label: 'Rework', count: profile.rework_cases, className: 'rework' },
    { label: 'QC Fail', count: profile.qc_fail_cases, className: 'qc-fail' },
  ];
  const available = segments.every(item => item.count != null);
  const total = available ? segments.reduce((sum,item) => sum + Number(item.count),0) : null;
  const largest = Math.max(1, ...segments.map(item => Number(item.count || 0)));
  const bars = segments.map(item => `<div class="signal-row ${item.className}"><span>${item.label}</span><span class="signal-track"><span style="width:${available ? Number(item.count)/largest*100 : 0}%"></span></span><strong>${available ? formatNumber.format(item.count) + ' เคส' : '—'}</strong></div>`).join('');
  return `<article class="combined-signal-card">
    <div class="combined-signal-card__heading"><div><p>ISSUE SIGNALS · สะสม</p><h3>สัญญาณปัญหารวม</h3></div><div class="signal-total"><strong>${total == null ? '—' : formatNumber.format(total)}</strong><span>สัญญาณ</span></div></div>
    <div class="signal-rows">${bars}</div>
    <small>Complaint, Rework และ QC Fail ในโปรไฟล์อ้างอิง Complaint Log · เคสเดียวอาจเกิดมากกว่า 1 สัญญาณ ผลรวมไม่ใช่จำนวนเคสไม่ซ้ำ</small>
  </article>`;
}

function renderJobHistoryRows(jobs) {
  if (!jobs.length) return '<tr><td colspan="6" class="table-empty">ไม่พบ Order No. ที่ค้นหา</td></tr>';
  return jobs.map((job) => `
    <tr><td><strong>${escapeHtml(job.job_no)}</strong></td><td>${formatDate(job.install_date)}</td>
    <td>${escapeHtml(job.product_model || '—')}</td><td>${escapeHtml(job.project_name || '—')}</td>
    <td>${escapeHtml(job.qc_result || '—')}</td><td>${escapeHtml(job.job_status || '—')}</td></tr>`).join('');
}

function bindJobHistorySearch(jobs) {
  const input = document.querySelector('#jobHistorySearch');
  const rows = document.querySelector('#jobHistoryRows');
  const count = document.querySelector('#jobHistoryCount');
  if (!input || !rows || !count) return;

  const update = () => {
    const query = input.value.trim().toLocaleLowerCase('th-TH');
    const matches = query
      ? jobs.filter((job) => String(job.job_no || '').toLocaleLowerCase('th-TH').includes(query))
      : jobs;
    rows.innerHTML = renderJobHistoryRows(matches);
    count.textContent = query
      ? `${formatNumber.format(matches.length)} / ${formatNumber.format(jobs.length)} รายการ`
      : `${formatNumber.format(jobs.length)} รายการ`;
  };

  input.addEventListener('input', update);
}

function renderTechnicianProfile(data) {
  const profile = data.profile;
  const insights = data.case_insights || {};
  const reasons = (profile.status_reason || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join('');
  const jobs = data.jobs || [];
  const caseRows = (data.cases || []).map((item) => `
    <tr><td class="job-cell"><strong>${escapeHtml(item.job_no)}</strong></td><td><span class="project-chip">${escapeHtml(item.project_name || 'ไม่พบ Project')}</span></td>
    <td class="date-cell">${formatDate(item.complaint_date)}</td><td class="date-cell">${formatDate(item.close_date)}</td>
    <td><span class="issue-chip">${escapeHtml(item.issue_category || 'ไม่ระบุ')}</span></td><td class="issue-detail">${escapeHtml(item.issue_detail || '—')}</td>
    <td>${item.rework === true ? 'Yes' : item.rework === false ? 'No' : '—'}</td>
    <td>${escapeHtml(item.root_cause_type || item.root_cause_status || 'รอตรวจสอบ')}</td>
    <td><span class="case-status">${escapeHtml(item.case_status || 'รอตรวจ')}</span></td><td class="case-action">${escapeHtml(item.immediate_action || '—')}</td></tr>`).join('');
  const reviewRows = (data.review_cases || []).map((item) => `
    <tr><td><strong>${escapeHtml(item.job_no)}</strong></td><td>${formatDate(item.complaint_date)}</td>
    <td>${escapeHtml(item.issue_category || '—')}</td><td>${escapeHtml(item.link_status)}</td>
    <td>${escapeHtml(item.case_status || '—')}</td></tr>`).join('');

  document.querySelector('#pageTitle').textContent = profile.technician_name || profile.technician_id;
  document.querySelector('#pageDescription').textContent = `${profile.technician_id} · ${profile.team || 'ยังไม่มี Team'} · ${profile.vendor_name || 'ยังไม่มี Vendor'}`;
  document.querySelector('#technicianProfile').innerHTML = `
    <a class="back-link" href="#watchlist">← กลับไป Watchlist</a>
    <section class="panel profile-identity">
      <div><p class="eyebrow">TECHNICIAN</p><h2>${escapeHtml(profile.technician_name || 'ไม่พบชื่อช่าง')}</h2><p class="muted">Tech ID ${escapeHtml(profile.technician_id)} · ${escapeHtml(profile.area || 'ไม่ระบุพื้นที่')}</p></div>
      <div class="profile-tags"><span>${escapeHtml(profile.team || 'ไม่มี Team')}</span><span>${escapeHtml(profile.vendor_name || 'ไม่มี Vendor')}</span><span>${profile.active ? 'Active' : 'Inactive'}</span></div>
    </section>
    <section class="profile-section">
      <div class="section-title"><div><p class="eyebrow">PERFORMANCE SUMMARY · สะสม</p><h2>ผลการดำเนินงานรายช่าง</h2></div><span class="pill ${escapeHtml(profile.watchlist_status || 'INSUFFICIENT_DATA')}">${escapeHtml(profile.watchlist_status || 'รอข้อมูล')} · สะสม</span></div>
      <div class="profile-scoreboard">
        ${combinedSignalCard(profile)}
        <div class="issue-counts">
          ${countCard('Jobs ทั้งหมด', profile.total_jobs, 'งาน', profile.volume_context || 'รอข้อมูล', 'jobs')}
          ${countCard('Complaint', profile.complaint_cases, 'เคส', 'Complaint Log', 'complaint')}
          ${countCard('Rework', profile.rework_cases, 'เคส', 'Complaint Log', 'rework')}
          ${rankedInsightCard('ISSUE CATEGORY', insights.issue_categories, `${formatNumber.format(insights.distinct_issue_categories || 0)} หมวด`, 'issue-analysis')}
          ${rankedInsightCard('ROOT CAUSE', insights.root_causes, `ยืนยัน ${formatNumber.format(insights.confirmed_root_cause_cases || 0)} · รอตรวจ ${formatNumber.format(insights.pending_root_cause_cases || 0)}`, 'root-analysis')}
          ${actionLevelCard(insights.action_level)}
        </div>
      </div>
      <p class="action-level-note">Action Level ใช้เฉพาะเคสที่ Root Cause ยืนยันแล้วและอยู่ในกลุ่มสาเหตุจากช่าง ส่วน Product / Customer / Site และรายการรอตรวจจะไม่ถูกใช้ยกระดับมาตรการอัตโนมัติ</p>
      ${reasons ? `<ul class="profile-reasons">${reasons}</ul>` : ''}
    </section>
    <section class="panel">
      <div class="section-title history-heading">
        <div><p class="eyebrow">JOB HISTORY</p><h2>ประวัติงานย้อนหลัง</h2></div>
        <div class="history-tools"><label class="order-search"><span>ค้นหา</span><input id="jobHistorySearch" type="search" placeholder="ค้นหา Order No." autocomplete="off" aria-label="ค้นหา Order No." /></label><span id="jobHistoryCount" class="count-label">${formatNumber.format(data.history_summary.job_records)} รายการ</span></div>
      </div>
      <div class="table-wrap profile-table"><table><thead><tr><th>Job No.</th><th>วันที่ติดตั้ง</th><th>สินค้า</th><th>Project</th><th>QC Result</th><th>Job Status</th></tr></thead><tbody id="jobHistoryRows">${renderJobHistoryRows(jobs)}</tbody></table></div>
    </section>
    <section class="panel case-history-panel">
      <div class="section-title"><div><p class="eyebrow">CASE HISTORY</p><h2>ประวัติเคสที่ผูกกับช่างแล้ว</h2></div><span class="count-label">${formatNumber.format(data.history_summary.case_records)} เคส</span></div>
      <div class="table-wrap profile-table"><table class="case-history-table"><thead><tr><th>Job No.</th><th>Project</th><th>วันที่รับเรื่อง</th><th>วันที่แก้ไข</th><th>ประเภทปัญหา</th><th>รายละเอียดปัญหา</th><th>Rework</th><th>Root Cause</th><th>สถานะ</th><th>Action</th></tr></thead><tbody>${caseRows || '<tr><td colspan="10">ไม่พบประวัติเคส</td></tr>'}</tbody></table></div>
    </section>
    <section class="panel review-panel">
      <div class="section-title"><div><p class="eyebrow">HUMAN REVIEW</p><h2>เคสที่ยังไม่นับเข้าคะแนน</h2></div><span class="count-label">${formatNumber.format(data.history_summary.review_cases)} เคส</span></div>
      <p class="muted">เคสที่ Tech ID ขัดกับ Job Data หรือยังหา Job No. ไม่พบ จะแสดงแยกไว้ทบทวน; Root Cause และ Action Level จะยังไม่สรุปจากเคสเหล่านี้</p>
      ${reviewRows ? `<div class="table-wrap profile-table"><table><thead><tr><th>Job No.</th><th>Complaint Date</th><th>ประเภทปัญหา</th><th>เหตุผลพักตรวจ</th><th>สถานะ</th></tr></thead><tbody>${reviewRows}</tbody></table></div>` : '<div class="empty-state">ไม่มีเคสที่ต้องพักตรวจสำหรับช่างรายนี้</div>'}
    </section>`;
  bindJobHistorySearch(jobs);
}

async function loadTechnicianProfile(technicianId) {
  const target = document.querySelector('#technicianProfile');
  target.className = 'profile-loading';
  target.textContent = 'กำลังโหลดข้อมูลช่าง…';
  const response = await fetch(`/api/technicians/${encodeURIComponent(technicianId)}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'ไม่สามารถโหลดข้อมูลช่างได้');
  loadedTechnicianId = technicianId;
  target.className = '';
  renderTechnicianProfile(data);
}

function showProfileError(error) {
  loadedTechnicianId = null;
  document.querySelector('#technicianProfile').innerHTML = `<a class="back-link" href="#watchlist">← กลับไป Watchlist</a><div class="panel empty-state">${escapeHtml(error.message)}</div>`;
}

function previewMarkup(data) {
  const jobs = data.summary.jobs;
  const cases = data.summary.complaints;
  const tech = data.summary.technicians;
  const identity = jobs.technician_identity;
  const links = cases.link_status;
  const complaintPeriod = cases.period_start && cases.period_end
    ? `${evidenceDate.format(new Date(`${cases.period_start}T00:00:00`))} – ${evidenceDate.format(new Date(`${cases.period_end}T00:00:00`))}`
    : 'ไม่มี Complaint Date';
  const warnings = data.warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  return `
    <div class="preview-head"><div><strong>${escapeHtml(data.filename)}</strong><small>Preview เท่านั้น — ยังไม่ได้เขียนฐานข้อมูล</small></div><span class="ready">พร้อมนำเข้า</span></div>
    <div class="preview-grid">
      <div><span>Job rows</span><strong>${formatNumber.format(jobs.rows)}</strong><small>${formatNumber.format(jobs.unique_job_numbers)} Order No.</small></div>
      <div><span>Complaint evidence</span><strong>${formatNumber.format(cases.rows)}</strong><small>${complaintPeriod} · ยึด Complaint Date</small></div>
      <div><span>Verified technicians</span><strong>${formatNumber.format(tech.unique_verified)}</strong><small>Tech ID ซ้ำ ${formatNumber.format(tech.duplicate_ids)}</small></div>
      <div><span>จับคู่ Job Data ตรงกัน</span><strong>${formatNumber.format(links.MATCHED || 0)}</strong><small>ติดตั้งก่อนช่วง Job Data ${formatNumber.format(links.REFERENCE_OUTSIDE_CURRENT_JOB_DATA || 0)} เคส แต่รับเรื่องปี 2026: นับรวมแล้ว · ตรวจ Order No. เพิ่ม ${formatNumber.format(links.JOB_REFERENCE_REQUIRES_REVIEW || 0)}</small></div>
      <div><span>Tech conflict</span><strong>${formatNumber.format(links.TECHNICIAN_CONFLICT || 0)}</strong><small>พักไว้ให้คนตรวจ</small></div>
      <div><span>ไม่สร้างโปรไฟล์</span><strong>${formatNumber.format(identity.UNVERIFIED_TECHNICIAN_IDENTITY || 0)}</strong><small>PWS1 / PWS51</small></div>
    </div>
    ${warnings ? `<ul class="import-warnings">${warnings}</ul>` : ''}
    <div class="evidence-note">รายการที่หายไปจากไฟล์รอบใหม่จะไม่ถูกลบ และช่องว่างจะไม่ถูกสรุปว่า Pass หรือไม่มีปัญหา</div>
    <button id="commitImport" type="button">ยืนยันบันทึกข้อมูล</button>
    <span id="commitStatus" class="commit-status"></span>`;
}

async function uploadFile(endpoint, file) {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch(endpoint, { method: 'POST', body: form });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'ดำเนินการไม่สำเร็จ');
  return data;
}

document.querySelector('#refresh').addEventListener('click', () => loadWatchlist().catch(showWatchlistError));
document.querySelector('#workbook').addEventListener('change', (event) => {
  document.querySelector('#fileLabel').textContent = event.target.files[0]?.name || 'เลือกไฟล์ Excel';
  previewedFile = null;
  document.querySelector('#importResult').textContent = '';
});
document.querySelector('#uploadForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = document.querySelector('#workbook').files[0];
  if (!file) return;
  const target = document.querySelector('#importResult');
  target.textContent = 'กำลังอ่านข้อมูลและตรวจหลักฐาน…';
  try {
    const data = await uploadFile('/api/import/preview', file);
    previewedFile = file;
    target.innerHTML = previewMarkup(data);
    document.querySelector('#commitImport').addEventListener('click', commitImport);
  } catch (error) {
    previewedFile = null;
    target.textContent = error.message;
  }
});

async function commitImport() {
  if (!previewedFile) return;
  const button = document.querySelector('#commitImport');
  const status = document.querySelector('#commitStatus');
  button.disabled = true;
  status.textContent = 'กำลังบันทึกแบบ transaction…';
  try {
    const data = await uploadFile('/api/import/commit', previewedFile);
    status.textContent = `บันทึกแล้ว: Jobs ใหม่ ${formatNumber.format(data.jobs_inserted)}, อัปเดต ${formatNumber.format(data.jobs_updated)} · Cases ใหม่ ${formatNumber.format(data.cases_inserted)}, อัปเดต ${formatNumber.format(data.cases_updated)}`;
    await loadDashboard();
    await loadWatchlist();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

function showWatchlistError(error) {
  document.querySelector('#technicianRows').innerHTML = `<tr><td colspan="10">${escapeHtml(error.message)}</td></tr>`;
}

window.addEventListener('hashchange', setRoute);
setRoute();
loadDashboard().catch((error) => { document.querySelector('#ytdMetrics').textContent = error.message; });
loadWatchlist().catch(showWatchlistError);
