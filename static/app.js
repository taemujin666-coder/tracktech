const formatNumber = new Intl.NumberFormat('th-TH');
const percent = (value) => value == null ? 'รอข้อมูล' : `${Math.round(value * 100)}%`;

async function loadDashboard() {
  const response = await fetch('/api/dashboard');
  if (!response.ok) throw new Error('ไม่สามารถโหลดข้อมูลได้');
  const data = await response.json();
  document.querySelector('#mode').textContent = data.mode === 'demo' ? 'โหมดตัวอย่าง' : 'ข้อมูลจากฐานจริง';
  const cards = [
    ['Jobs', data.summary.jobs, ''], ['Complaint cases', data.summary.complaint_cases, ''],
    ['Action ค้าง', data.summary.open_actions, 'warning'], ['Evidence รอตรวจ', data.summary.pending_evidence, 'alert'],
  ];
  document.querySelector('#overview').innerHTML = cards.map(([label, value, tone]) => `<article class="metric ${tone}"><p>${label}</p><strong>${formatNumber.format(value)}</strong></article>`).join('');
  document.querySelector('#technicianRows').innerHTML = data.technicians.map((tech) => `
    <tr><td><strong>${tech.technician_id}</strong></td><td>${tech.vendor || '—'}</td>
    <td><span class="pill ${tech.status}">${tech.status}</span></td>
    <td>${tech.risk_score == null ? 'รอข้อมูล' : tech.risk_score}</td><td>${percent(tech.qc_coverage)}</td>
    <td class="reason">${(tech.reasons || []).join(' · ')}</td></tr>`).join('');
}

document.querySelector('#refresh').addEventListener('click', () => loadDashboard().catch(showError));
document.querySelector('#uploadForm').addEventListener('submit', async (event) => {
  event.preventDefault(); const file = document.querySelector('#workbook').files[0]; if (!file) return;
  const form = new FormData(); form.append('file', file); const target = document.querySelector('#importResult'); target.textContent = 'กำลังตรวจโครงสร้างไฟล์…';
  try { const response = await fetch('/api/import/validate', { method:'POST', body:form }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'ตรวจไฟล์ไม่สำเร็จ');
    target.innerHTML = `<div class="validation">${data.sheets.map(sheet => `<span class="${sheet.is_valid ? '' : 'invalid'}">${sheet.sheet_name}: ${sheet.is_valid ? `พร้อม (${formatNumber.format(sheet.row_count)} แถว)` : `ต้องแก้ ${sheet.missing_columns.join(', ') || 'คีย์ว่าง'}`}</span>`).join('')}</div>`;
  } catch (error) { target.textContent = error.message; }
});
function showError(error) { document.querySelector('#technicianRows').innerHTML = `<tr><td colspan="6">${error.message}</td></tr>`; }
loadDashboard().catch(showError);

