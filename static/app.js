const formatNumber = new Intl.NumberFormat('th-TH');
const evidenceDate = new Intl.DateTimeFormat('th-TH-u-ca-gregory', { day: 'numeric', month: 'short', year: 'numeric' });
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
    title: 'ทีมที่ต้องติดตาม',
    description: 'ใช้เหตุผลและหลักฐานประกอบการทบทวน ไม่สรุปจากสีสถานะเพียงอย่างเดียว',
  },
  import: {
    eyebrow: 'EVIDENCE-FIRST IMPORT',
    title: 'นำเข้าข้อมูล',
    description: 'ตรวจ Preview และหลักฐานก่อนบันทึกทุกครั้ง',
  },
  technician: {
    eyebrow: 'TECHNICIAN PROFILE',
    title: 'ข้อมูลรายช่าง',
    description: 'สรุปผลงาน เปรียบเทียบทีม และตรวจประวัติงานกับเคสจากหลักฐานต้นทาง',
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
  const ytdCards = [
    ['Jobs', formatNumber.format(data.summary.jobs), 'Job Data', ''],
    ['Complaints', formatNumber.format(data.summary.complaint_cases), 'Complaint Log', ''],
    ['Complaint Rate', rate(data.summary.complaint_rate), 'Complaints ÷ Jobs', ''],
    ['Rework Cases', formatNumber.format(data.summary.rework_cases), 'Complaint Log: Rework = Yes', ''],
    ['Rework Rate', rate(data.summary.rework_rate), 'Rework Cases ÷ Jobs', ''],
    ['QC Fail Cases', formatNumber.format(data.summary.qc_fail_cases), 'Job Data: QC Result = Fail', ''],
    ['QC Fail Rate', rate(data.summary.qc_fail_rate), 'QC Fail Cases ÷ Jobs', ''],
  ];
  const operationalCards = [
    ['Action ที่ยังไม่ปิด', formatNumber.format(data.summary.open_actions), 'ต้องกำหนดหรือดำเนินการติดตาม', 'warning'],
    ['Evidence รอตรวจ', formatNumber.format(data.summary.pending_evidence), 'ยังไม่สรุปว่าเคสปิดหรือไม่มีปัญหา', 'alert'],
  ];
  document.querySelector('#ytdMetrics').innerHTML = ytdCards.map(([label, value, detail, tone]) => `<article class="metric ${tone}"><p>${label}</p><strong>${value}</strong><small>${detail}</small></article>`).join('');
  document.querySelector('#operationalMetrics').innerHTML = operationalCards.map(([label, value, detail, tone]) => `<article class="metric ${tone}"><p>${label}</p><strong>${value}</strong><small>${detail}</small></article>`).join('');
  document.querySelector('#technicianRows').innerHTML = data.technicians.map((tech) => `
    <tr><td><a class="tech-link" href="#technician/${encodeURIComponent(tech.technician_id)}">${escapeHtml(tech.technician_id)}</a></td>
    <td>${escapeHtml(tech.technician_name || '—')}</td><td>${escapeHtml(tech.team || '—')}</td><td>${escapeHtml(tech.vendor || '—')}</td>
    <td><span class="pill ${escapeHtml(tech.status)}">${escapeHtml(tech.status)}</span></td>
    <td>${rate(tech.combined_rate)}</td><td>${percent(tech.qc_coverage)}</td>
    <td class="reason">${(tech.reasons || []).map(escapeHtml).join(' · ')}</td></tr>`).join('');
}

function profileMetric(label, value, detail = '', tone = '') {
  return `<article class="metric ${tone}"><p>${escapeHtml(label)}</p><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></article>`;
}

function renderTechnicianProfile(data) {
  const profile = data.profile;
  const team = data.team_summary;
  const reasons = (profile.status_reason || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join('');
  const memberRows = (data.team_members || []).map((member) => `
    <tr><td><a class="tech-link" href="#technician/${encodeURIComponent(member.technician_id)}">${escapeHtml(member.technician_id)}</a></td>
    <td>${escapeHtml(member.technician_name || '—')}</td><td>${formatNumber.format(member.total_jobs || 0)}</td>
    <td>${rate(member.combined_rate)}</td><td><span class="pill ${escapeHtml(member.watchlist_status || 'INSUFFICIENT_DATA')}">${escapeHtml(member.watchlist_status || 'รอข้อมูล')}</span></td>
    <td>${escapeHtml(member.volume_context || '—')}</td></tr>`).join('');
  const jobRows = (data.jobs || []).map((job) => `
    <tr><td><strong>${escapeHtml(job.job_no)}</strong></td><td>${formatDate(job.install_date)}</td>
    <td>${escapeHtml(job.product_model || '—')}</td><td>${escapeHtml(job.project_name || '—')}</td>
    <td>${escapeHtml(job.qc_result || '—')}</td><td>${escapeHtml(job.job_status || '—')}</td></tr>`).join('');
  const caseRows = (data.cases || []).map((item) => `
    <tr><td><strong>${escapeHtml(item.job_no)}</strong></td><td>${formatDate(item.complaint_date)}</td>
    <td>${escapeHtml(item.issue_category || '—')}</td><td>${item.rework === true ? 'Yes' : item.rework === false ? 'No' : '—'}</td>
    <td>${escapeHtml(item.root_cause_type || item.root_cause_status || 'รอตรวจสอบ')}</td>
    <td>${escapeHtml(item.case_status || '—')}</td><td>${escapeHtml(item.immediate_action || '—')}</td></tr>`).join('');
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
      <div class="section-title"><div><p class="eyebrow">PERFORMANCE SUMMARY</p><h2>ผลการดำเนินงานรายช่าง</h2></div><span class="pill ${escapeHtml(profile.watchlist_status || 'INSUFFICIENT_DATA')}">${escapeHtml(profile.watchlist_status || 'รอข้อมูล')}</span></div>
      <div class="metrics metrics--profile">
        ${profileMetric('Jobs', formatNumber.format(profile.total_jobs || 0), profile.volume_context || 'รอข้อมูล')}
        ${profileMetric('Complaints', formatNumber.format(profile.complaint_cases || 0), rate(profile.complaint_rate))}
        ${profileMetric('Rework Cases', formatNumber.format(profile.rework_cases || 0), rate(profile.rework_rate))}
        ${profileMetric('QC Fail Cases', formatNumber.format(profile.qc_fail_cases || 0), rate(profile.qc_fail_rate))}
        ${profileMetric('Combined Rate', rate(profile.combined_rate), 'Complaint + Rework + QC Fail', 'warning')}
        ${profileMetric('QC Coverage', percent(profile.qc_coverage), `${formatNumber.format(profile.qc_inspected_jobs || 0)} งานมีข้อมูล QC`)}
      </div>
      ${reasons ? `<ul class="profile-reasons">${reasons}</ul>` : ''}
    </section>
    <section class="panel">
      <div class="section-title"><div><p class="eyebrow">TEAM SUMMARY</p><h2>${escapeHtml(team?.team || profile.team || 'ยังไม่มีข้อมูล Team')}</h2></div><span class="muted">เปรียบเทียบด้วยนิยาม KPI ชุดเดียวกัน</span></div>
      ${team ? `<div class="metrics metrics--team">
        ${profileMetric('สมาชิกทีม', formatNumber.format(team.member_count), `Active ${formatNumber.format(team.active_member_count)}`)}
        ${profileMetric('Jobs รวม', formatNumber.format(team.total_jobs), 'Job Data')}
        ${profileMetric('Complaints', formatNumber.format(team.complaint_cases), rate(team.complaint_rate))}
        ${profileMetric('Rework', formatNumber.format(team.rework_cases), rate(team.rework_rate))}
        ${profileMetric('QC Fail', formatNumber.format(team.qc_fail_cases), rate(team.qc_fail_rate))}
        ${profileMetric('Combined Rate ทีม', rate(team.combined_rate), 'Complaint + Rework + QC Fail')}
      </div>
      <div class="table-wrap profile-table"><table><thead><tr><th>Tech ID</th><th>ชื่อช่าง</th><th>Jobs</th><th>Combined Rate</th><th>สถานะ</th><th>Volume</th></tr></thead><tbody>${memberRows || '<tr><td colspan="6">ยังไม่มีสมาชิกทีม</td></tr>'}</tbody></table></div>` : '<p class="muted">Technician Master ยังไม่ได้ระบุ Team สำหรับช่างรายนี้</p>'}
    </section>
    <section class="panel">
      <div class="section-title"><div><p class="eyebrow">JOB HISTORY</p><h2>ประวัติงานย้อนหลัง</h2></div><span class="count-label">${formatNumber.format(data.history_summary.job_records)} รายการ</span></div>
      <div class="table-wrap profile-table"><table><thead><tr><th>Job No.</th><th>วันที่ติดตั้ง</th><th>สินค้า</th><th>Project</th><th>QC Result</th><th>Job Status</th></tr></thead><tbody>${jobRows || '<tr><td colspan="6">ไม่พบประวัติงาน</td></tr>'}</tbody></table></div>
    </section>
    <section class="panel">
      <div class="section-title"><div><p class="eyebrow">CASE HISTORY</p><h2>ประวัติเคสที่ผูกกับช่างแล้ว</h2></div><span class="count-label">${formatNumber.format(data.history_summary.case_records)} เคส</span></div>
      <div class="table-wrap profile-table"><table><thead><tr><th>Job No.</th><th>Complaint Date</th><th>ประเภทปัญหา</th><th>Rework</th><th>Root Cause</th><th>สถานะ</th><th>Action</th></tr></thead><tbody>${caseRows || '<tr><td colspan="7">ไม่พบประวัติเคส</td></tr>'}</tbody></table></div>
    </section>
    <section class="panel review-panel">
      <div class="section-title"><div><p class="eyebrow">HUMAN REVIEW</p><h2>เคสที่ยังไม่นับเข้าคะแนน</h2></div><span class="count-label">${formatNumber.format(data.history_summary.review_cases)} เคส</span></div>
      <p class="muted">Tech ID ขัดกับ Job Data หรือยังหา Job No. ไม่พบ จึงแสดงเป็นหลักฐานแต่ไม่รวมใน Combined Rate</p>
      ${reviewRows ? `<div class="table-wrap profile-table"><table><thead><tr><th>Job No.</th><th>Complaint Date</th><th>ประเภทปัญหา</th><th>เหตุผลพักตรวจ</th><th>สถานะ</th></tr></thead><tbody>${reviewRows}</tbody></table></div>` : '<div class="empty-state">ไม่มีเคสที่ต้องพักตรวจสำหรับช่างรายนี้</div>'}
    </section>`;
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

document.querySelector('#refresh').addEventListener('click', () => loadDashboard().catch(showError));
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
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

function showError(error) {
  document.querySelector('#technicianRows').innerHTML = `<tr><td colspan="8">${escapeHtml(error.message)}</td></tr>`;
}

window.addEventListener('hashchange', setRoute);
setRoute();
loadDashboard().catch(showError);
