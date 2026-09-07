import { App } from '@modelcontextprotocol/ext-apps';

type Data = Record<string, any>;
declare global { interface Window { CANVAS_DASHBOARD: {mode: 'mcp' | 'browser'} } }
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const course = $('course') as HTMLSelectElement;
const student = $('student') as HTMLSelectElement;
const search = $('student-search') as HTMLInputElement;
const escape = (value: any) => String(value ?? 'Unavailable').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const readable = (s: string) => s.replaceAll('_', ' ');
const date = (s: any) => s ? new Date(s).toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'}) : 'Unavailable';
const percent = (n: any) => typeof n === 'number' ? `${n.toLocaleString(undefined, {maximumFractionDigits:2})}%` : 'Unavailable';
const href = (s: any) => { try { const u = new URL(s); return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password ? escape(u.href) : ''; } catch { return ''; } };
const link = (title: any, url: any) => href(url) ? `<a class="row-link" href="${href(url)}" target="_blank" rel="noreferrer">${escape(title)}</a>` : escape(title);
let app: App | undefined;
let bridgeTool = 'canvas_dashboard_data';
let sequence = 0, rosterSequence = 0;
let rosterCursor: string | null = null, reviewCursor: string | null = null;
let report: Data | undefined, jobs: Data[] = [];
let sections = ['overview', 'assignments', 'progress'];
let prefills: Data = Object.fromEntries(new URLSearchParams(location.search));

function error(message: string) { $('error').textContent = message; $('error').hidden = false; }
function clearError() { $('error').hidden = true; }
function status(message: string) { $('status').textContent = message; }
async function request(action: string, args: Data = {}): Promise<Data> {
  const payload = {action, ...args};
  if (app) {
    const result = await app.callServerTool({name: bridgeTool, arguments: {request: payload}});
    const text = result.content?.find((c: any) => c.type === 'text') as {text?:string} | undefined;
    const data = result.structuredContent ?? (text?.text ? JSON.parse(text.text) : {});
    if (result.isError || data.error) throw new Error(typeof data.error === 'string' ? data.error : data.error?.message ?? 'Dashboard request failed');
    return data;
  }
  const response = await fetch('/api', {method:'POST', credentials:'same-origin',
    headers:{'Content-Type':'application/json', 'X-Canvas-Dashboard':'1'}, body:JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error ?? 'Dashboard request failed');
  return data;
}
function selected() { return {course_id:course.value, student_id:student.value}; }
function empty() {
  $('student-report').innerHTML = '<div class="empty"><h2>Select a student to explore their progress.</h2><p>Only the selected student’s course record will appear here.</p></div>';
  $('reviews').hidden = true; report = undefined; jobs = []; reviewCursor = null;
}
async function loadCourses() {
  const data = await request('courses');
  course.innerHTML = '<option value="">Choose a course</option>' + data.items.map((c:Data) => `<option value="${escape(c.id)}">${escape(c.name ?? c.course_code)}${c.term?.name ? ` · ${escape(c.term.name)}` : ''}</option>`).join('');
  if (data.complete === false) error('The course list is incomplete. Check Canvas permissions or reconnect to retrieve remaining courses.');
  if (prefills.course_id) { course.value = String(prefills.course_id); await changeCourse(); }
  status('Choose a course and student to view their record.');
}
async function loadStudents(more = false) {
  const token = ++rosterSequence, courseId = course.value;
  if (!courseId) return;
  status('Retrieving students…');
  const data = await request('students', {course_id: courseId, search:search.value, cursor:more ? rosterCursor : null});
  if (token !== rosterSequence || courseId !== course.value) return;
  if (!more) student.innerHTML = '<option value="">Choose a student</option>';
  student.insertAdjacentHTML('beforeend', data.items.map((s:Data) => `<option value="${escape(s.id)}">${escape(s.name)}</option>`).join(''));
  rosterCursor = data.next_cursor ?? null; $('more-students').hidden = !rosterCursor;
  if (prefills.student_id) {
    const id = String(prefills.student_id); prefills.student_id = null;
    if (![...student.options].some(o=>o.value===id)) student.add(new Option(`Student ${id}`, id));
    student.value = id; await loadReport();
  } else status(data.items.length ? 'Choose a student.' : 'No students returned for this search.');
}
async function changeCourse() {
  sections=['overview','assignments','progress'];
  sequence++; rosterSequence++; empty(); clearError(); search.value = ''; rosterCursor = null;
  student.innerHTML = '<option value="">Choose a student</option>';
  $('more-students').hidden = true;
  if (course.value) await loadStudents();
}
async function loadReport(refresh = false) {
  const token = ++sequence, ids = selected();
  clearError(); empty();
  if (!ids.student_id || !ids.course_id) return;
  status('Retrieving the selected student’s record…');
  $('student-report').setAttribute('aria-busy', 'true');
  try {
    const data = await request('report', {...ids, sections, refresh});
    if (token !== sequence) return;
    report = data; renderReport(); $('reviews').hidden = false;
    status(`Showing ${data.student.name}. ${data.assignments.length} assignment records retrieved${data.counts_complete ? '' : ' · partial coverage'}.`);
    await loadJobs(false, token);
  } catch (e) { if (token === sequence) error((e as Error).message); }
  finally { if (token === sequence) $('student-report').removeAttribute('aria-busy'); }
}
function badges(row: Data) { return [...new Set([row.status, ...row.flags])].map((s:any) => `<span class="badge ${escape(s)}">${escape(readable(s))}</span>`).join(''); }
function metric(label:string, value:any, note:string, main=false) { return `<div class="metric${main ? ' main-metric':''}"><span class="label">${label}</span><strong>${escape(value)}</strong><small>${escape(note)}</small></div>`; }
function timeline(rows: Data[]) {
  const dates = rows.filter(r=>r.submitted_at).map(r=>String(r.submitted_at).slice(0,10)).sort();
  if (!dates.length) return '<p class="muted">No dated submissions were returned.</p>';
  const last = new Date(dates.at(-1)!+'T00:00:00Z');
  const end = Date.UTC(last.getUTCFullYear(), last.getUTCMonth(), last.getUTCDate()+1);
  const start = end - 8*7*86400000, counts = Array(8).fill(0);
  for (const d of dates) { const i = Math.floor((Date.parse(d+'T00:00:00Z')-start)/(7*86400000)); if (i>=0 && i<8) counts[i]++; }
  const max = Math.max(1,...counts);
  let svg = '<svg class="chart" viewBox="0 0 520 140" role="img" aria-label="Submission counts in the eight weeks ending with the latest recorded submission"><line x1="24" y1="105" x2="512" y2="105"/>';
  counts.forEach((n,i)=> { const x=32+i*61, height=75*n/max; svg += `<rect x="${x}" y="${105-height}" width="35" height="${height}" rx="2"/><text x="${x+17.5}" y="${99-height}" text-anchor="middle">${n}</text><text x="${x+17.5}" y="127" text-anchor="middle">${new Date(start+i*7*86400000).toLocaleDateString(undefined,{month:'short',day:'numeric', timeZone:'UTC'})}</text>`; });
  return svg+'</svg><p class="muted">Weekly counts · eight weeks ending at the latest recorded submission. Dates and scores are available in the table.</p>';
}
function renderReport() {
  if (!report) return;
  const r=report, partial=r.counts_complete ? 'Canvas status' : 'Partial count';
  $('student-report').innerHTML = `<div class="identity"><div><p class="eyebrow">Individual overview</p><h2>${escape(r.student.name)}</h2><p class="muted">${escape(r.course.name ?? r.course_id)}</p></div><div class="stamp">Retrieved ${escape(new Date(r.retrieved_at).toLocaleString())}<br>${r.cache?.hit ? 'Cached for up to 60 seconds' : 'Retrieved from Canvas'}<br><button id="refresh" class="secondary">Refresh record</button></div></div>
  ${r.warnings.length ? `<div class="notice"><strong>Some information is unavailable</strong>${r.warnings.map((w:Data)=>`<p>${escape(readable(w.section))}: ${escape(w.message)}</p>`).join('')}</div>` : ''}
  <div class="metrics">${metric('Canvas current grade',percent(r.grades.current_score),'Calculated by Canvas',true)}${metric('Missing',r.counts.missing,partial)}${metric('Late',r.counts.late,partial)}${metric('Awaiting grading',r.counts.awaiting_grading,partial)}${metric('Excused',r.counts.excused,partial)}</div>
  <div class="split"><section class="panel"><h3>Submission timeline</h3>${timeline(r.assignments)}</section><section class="panel"><h3>Grade and completion context</h3><dl class="grade-detail"><div><dt>Current grade</dt><dd>${percent(r.grades.current_score)}</dd></div><div><dt>Final grade</dt><dd>${percent(r.grades.final_score)}</dd></div><div><dt>Unposted current</dt><dd>${percent(r.grades.unposted_current_score)}</dd></div><div><dt>Module requirements</dt><dd>${r.progress.configured ? percent(r.progress.percent) : 'Not configured / unavailable'}</dd></div></dl><p class="muted">Current and final grades use different denominators. Assignment percentages are never averaged here.</p>${Object.keys(r.grades.periods).length ? `<details><summary>Grading periods</summary>${objectTable(r.grades.periods)}</details>` : ''}</section></div>
  <section class="panel"><div class="section-heading"><div><h2>Assignments & feedback</h2><p class="muted">Flags may overlap. Unsubmitted work is not automatically missing. Due dates below are student-specific when returned by Canvas.</p></div></div><div class="table-controls"><input id="assignment-search" type="search" aria-label="Filter assignments by title" placeholder="Find an assignment"><select id="assignment-filter" aria-label="Filter assignment status"><option value="all">All assignments</option>${['missing','late','awaiting_grading','excused','graded','not_submitted'].map(s=>`<option value="${s}">${readable(s)}</option>`).join('')}</select></div><div class="table-scroll"><table><caption class="muted" id="assignment-count"></caption><thead><tr><th scope="col">Assignment</th><th scope="col">Status</th><th scope="col">Score</th><th scope="col">Submitted</th><th scope="col">Student due date</th></tr></thead><tbody id="assignment-rows"></tbody></table></div></section>
  <section class="panel"><h2>A closer look</h2>${['progress','rubrics','outcomes','activity'].map(s=>`<details data-section="${s}"><summary>${({progress:'Module progress',rubrics:'Rubrics & instructor feedback',outcomes:'Learning outcomes',activity:'Recorded Canvas activity'} as Data)[s]}</summary><div class="detail-body" id="detail-${s}">${detail(s,r)}</div></details>`).join('')}</section>`;
  $('refresh').onclick=()=>void loadReport(true);
  $('assignment-search').oninput=renderAssignments; $('assignment-filter').onchange=renderAssignments;
  document.querySelectorAll<HTMLDetailsElement>('details[data-section]').forEach(d=>d.addEventListener('toggle',()=>{
    const section=d.dataset.section!;
    if(d.open && !sections.includes(section)) void loadSection(section, d);
  }));
  renderAssignments();
}
function renderAssignments() {
  if (!report) return;
  const q=($('assignment-search') as HTMLInputElement).value.toLowerCase(), filter=($('assignment-filter') as HTMLSelectElement).value;
  const rows=report.assignments.filter((r:Data)=>String(r.title).toLowerCase().includes(q) && (filter==='all'||r.status===filter||r.flags.includes(filter)));
  $('assignment-count').textContent=`${rows.length} of ${report.assignments.length} retrieved records${report.counts_complete ? '' : ' · incomplete inventory'}`;
  $('assignment-rows').innerHTML=rows.map((r:Data)=>`<tr><td>${link(r.title,r.url)}${r.is_new_quiz ? '<small>New Quizzes</small>' : r.quiz_id ? '<small>Classic Quiz</small>' : ''}</td><td>${badges(r)}</td><td>${r.score==null ? 'Ungraded / unavailable' : `${escape(r.score)} / ${escape(r.points_possible)}`}<small>${percent(r.percent)}</small></td><td>${date(r.submitted_at)}</td><td>${date(r.student_due_at)}${!r.student_due_at && r.general_due_at ? `<small>General date: ${date(r.general_due_at)}</small>`:''}</td></tr>`).join('') || '<tr><td colspan="5">No matching assignments.</td></tr>';
}
function objectTable(obj:Data) { return `<div class="table-scroll"><table><tbody>${Object.entries(obj).map(([k,v])=>`<tr><th scope="row">${escape(readable(k))}</th><td>${escape(typeof v==='object' ? JSON.stringify(v) : v)}</td></tr>`).join('')}</tbody></table></div>`; }
function detail(section:string,r:Data):string {
  if (!sections.includes(section)) return '<p class="muted">Retrieve this section when needed.</p>';
  if (section==='progress') return r.modules?.length ? r.modules.map((m:Data)=>`<h3>${escape(m.name)}</h3><p class="muted">${escape(m.state ?? 'No student completion state returned')}</p><ul class="inline-list">${(m.items ?? []).map((i:Data)=>`<li>${escape(i.title)} · ${i.completion_requirement ? `${escape(readable(i.completion_requirement.type))}: ${i.completion_requirement.completed===true?'Complete':i.completion_requirement.completed===false?'Not complete':'Unavailable'}`:'No completion rule returned'}</li>`).join('')}</ul>`).join('') : '<p>No modules returned. Completion rules may not be configured.</p>';
  if (section==='rubrics') return r.rubrics?.length ? r.rubrics.map((a:Data)=>`<h3>${link(a.title,a.url)}</h3><div class="table-scroll"><table><thead><tr><th scope="col">Criterion</th><th scope="col">Points</th><th scope="col">Feedback</th></tr></thead><tbody>${a.criteria.map((c:Data)=>`<tr><td>${escape(c.description)}</td><td>${escape(a.assessment[c.id]?.points)} / ${escape(c.points)}</td><td>${escape(a.assessment[c.id]?.comments ?? 'No criterion comment returned')}</td></tr>`).join('')}</tbody></table></div>${a.comments.map((c:Data)=>`<p>${escape(c.comment)} <small>${date(c.created_at)}</small></p>`).join('')}`).join('') : '<p>No rubric evidence returned. Check coverage notices.</p>';
  if (section==='activity') return r.activity.available ? `<p class="muted">${escape(r.activity.interpretation)}</p><p>Last recorded participation: ${date(r.activity.last_participation_at)}. Source updated: ${date(r.activity.source_updated_at)}.</p><div class="table-scroll"><table><thead><tr><th scope="col">Date</th><th scope="col">Page views</th><th scope="col">Participation events</th></tr></thead><tbody>${r.activity.days.map((d:Data)=>`<tr><td>${escape(d.date)}</td><td>${d.views}</td><td>${d.participations}</td></tr>`).join('')}</tbody></table></div>` : '<p>Activity data is unavailable. It has not been treated as zero.</p>';
  const definitions=new Map((r.outcome_definitions ?? []).map((o:Data)=>[String(o.id),o.title]));
  return r.outcomes?.length ? `<p class="muted">Scores and mastery below are returned by Canvas; unavailable outcomes are not inferred.</p><div class="table-scroll"><table><thead><tr><th scope="col">Outcome / alignment</th><th scope="col">Score</th><th scope="col">Mastery</th><th scope="col">Assessed</th></tr></thead><tbody>${r.outcomes.map((o:Data)=>`<tr><td>${escape(definitions.get(String(o.links?.learning_outcome)) ?? o.links?.learning_outcome ?? o.id)}</td><td>${escape(o.score)} / ${escape(o.possible)}</td><td>${o.mastery===true?'Met':o.mastery===false?'Not met':'Unavailable'}</td><td>${date(o.assessed_at)}</td></tr>`).join('')}</tbody></table></div>` : '<p>No outcome results returned. Outcomes may be unconfigured or unavailable.</p>';
}
async function loadSection(section:string, element:HTMLDetailsElement) {
  const token=sequence, ids=selected();
  element.querySelector('.detail-body')!.textContent='Retrieving details…';
  const requested=[...new Set([...sections,section])]; sections=requested;
  try {
    const data=await request('report',{...ids,sections:requested});
    if(token!==sequence) return;
    // Merge only this request's optional section; concurrent panels cannot erase one another.
    if(report) { for(const key of [section,section==='outcomes'?'outcome_definitions':'',section==='outcomes'?'outcome_rollups':'']) if(key) report[key]=data[key]; report.warnings=data.warnings; }
    const target=$(`detail-${section}`); if(target) target.innerHTML=detail(section,report!);
    if(data.warnings.length) error(data.warnings.map((w:Data)=>`${readable(w.section)}: ${w.message}`).join(' '));
  } catch(e) { if(token===sequence) { sections=sections.filter(s=>s!==section); element.querySelector('.detail-body')!.textContent='Could not retrieve this section. Close and reopen it to retry.'; error((e as Error).message); } }
}
async function loadJobs(more=false, token=sequence) {
  if(!student.value) return;
  const data=await request('list_reviews',{...selected(),cursor:more?reviewCursor:null});
  if(token!==sequence) return;
  jobs=more?[...jobs,...data.items]:data.items; reviewCursor=data.next_cursor;
  $('more-reviews').hidden=!reviewCursor; renderJobs();
}
function handoff(job:Data) { return `Complete faculty learning review ${job.id} for course ${job.course_id}, student ${job.student_id}. Read canvas://reports/templates/learning-review. Wait for collection, retrieve every canvas_get_learning_review_batch, save cited analysis with canvas_record_learning_review_analysis, inspect saved analyses, then canvas_render_learning_review. Report evidence gaps honestly. Do not modify grades or send messages.`; }
function renderJobs() {
  $('review-jobs').innerHTML=jobs.length ? jobs.map(j=>`<article class="job" data-job="${escape(j.id)}"><h3>${escape(readable(j.status))}</h3><p class="muted">Created ${date(j.created_at)} · ${j.collection_complete?'Collection finished':'Evidence collection is not complete'}</p><p>${j.coverage.reviewed} / ${j.coverage.evidence_chunks} evidence chunks reviewed · ${j.coverage.gaps} documented gaps</p><progress aria-label="Evidence review progress" max="${Math.max(1,j.coverage.evidence_chunks)}" value="${j.coverage.reviewed}"></progress>${j.progress?.stage ? `<p class="muted">${escape(readable(j.progress.stage))}${j.progress.total ? ` · ${j.progress.completed} / ${j.progress.total}`:''}</p>`:''}<div class="job-actions"><button class="secondary" data-action="status">Refresh status</button>${['queued','collection_interrupted','cancelled'].includes(j.status) ? '<button class="secondary" data-action="resume">Resume collection</button>':''}${['collecting','queued','reviewing','awaiting_ai'].includes(j.status) ? '<button class="secondary" data-action="cancel">Cancel review</button>':''}${app?.getHostCapabilities()?.message?.text ? '<button data-action="handoff">Ask AI to complete review</button>':''}<button class="secondary" data-action="instructions">Show AI instructions</button>${j.report_path?'<button data-action="export">Export HTML report</button>':''}<button class="secondary" data-action="delete">Delete local review</button></div><textarea class="handoff" readonly aria-label="Instructions for your AI client" hidden>${escape(handoff(j))}</textarea><p class="muted">Job <code>${escape(j.id)}</code></p></article>`).join(''):'<p class="muted">No learning reviews for this student yet.</p>';
  document.querySelectorAll<HTMLButtonElement>('.job button').forEach(b=>b.onclick=()=>void jobAction(b));
}
async function jobAction(button:HTMLButtonElement) {
  const article=button.closest<HTMLElement>('.job')!, job=jobs.find(j=>j.id===article.dataset.job)!, action=button.dataset.action!, token=sequence;
  if(action==='instructions') { const t=article.querySelector<HTMLTextAreaElement>('textarea')!; t.hidden=false; t.focus(); t.select(); return; }
  button.disabled=true; clearError();
  try {
    if(action==='handoff') {
      const response=await app!.sendMessage({role:'user',content:[{type:'text',text:handoff(job)}]});
      if(response.isError) throw new Error('The host did not accept the request. Use Show AI instructions and paste them into your AI client.');
      status('Request sent to your AI client. Analysis is not complete yet.');
    } else if(action==='export') {
      const data=await request('export_review',{job_id:job.id});
      if(app) {
        if(!app.getHostCapabilities()?.downloadFile) throw new Error('This host does not support app exports. Ask your AI client to open the report path or use the browser dashboard.');
        const response=await app.downloadFile({contents:[{type:'resource',resource:{uri:'file:///canvas-learning-review.html',mimeType:'text/html',text:data.html}}]});
        if(response.isError) throw new Error('Export was cancelled or rejected by the host.');
      } else {
        const url=URL.createObjectURL(new Blob([data.html],{type:'text/html'}));
        const a=document.createElement('a'); a.href=url; a.download=data.filename; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
      }
    } else {
      if(action==='delete' && !window.confirm('Delete this local review, its evidence and exported report?')) return;
      const data=await request(action==='status'?'review_status':`${action}_review`,{job_id:job.id});
      if(data.status==='deletion_pending') status(data.next_step);
      if(token===sequence) await loadJobs(false,token);
    }
  } catch(e) { if(token===sequence) error((e as Error).message); }
  finally { button.disabled=false; }
}
async function initialize() {
  if(window.CANVAS_DASHBOARD.mode==='mcp') {
    app=new App({name:'Canvas student reports',version:'0.1.0'});
    app.ontoolinput=input=>{prefills={...prefills,...input.arguments};};
    app.ontoolresult=result=>{
      const data=result.structuredContent as Data|undefined;
      if(data?.dashboard_tool) {
        prefills={...prefills,...data};
        const invoked=app?.getHostContext()?.toolInfo?.tool?.name;
        bridgeTool=invoked?.endsWith('canvas_open_student_dashboard') ? invoked.replace(/canvas_open_student_dashboard$/,'canvas_dashboard_data') : data.dashboard_tool;
        if(course.options.length>1 && data.course_id && !course.value) {
          course.value=String(data.course_id); void changeCourse().catch(e=>error(e.message));
        }
      }
    };
    await app.connect();
    // Hosts can namespace registered names. Derive the matching bridge name from the invoking tool.
    const invoked=app.getHostContext()?.toolInfo?.tool?.name;
    if(invoked?.endsWith('canvas_open_student_dashboard')) bridgeTool=invoked.replace(/canvas_open_student_dashboard$/,'canvas_dashboard_data');
    $('connection').textContent='Connected through your MCP host · Student selection does not invoke AI';
  } else {
    const secret=location.hash.slice(1); history.replaceState(null,'',location.pathname+location.search);
    if(secret) {
      const response=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json','X-Canvas-Dashboard':'1'},body:JSON.stringify({secret})});
      if(!response.ok) throw new Error('This dashboard link is invalid. Open a new one from your MCP client.');
    }
    $('connection').textContent='Connected to your local server · Student selection does not invoke AI';
  }
  await loadCourses();
}
course.onchange=()=>void changeCourse().catch(e=>error(e.message));
student.onchange=()=>{sections=['overview','assignments','progress']; void loadReport();};
let searchTimer:ReturnType<typeof setTimeout>;
search.oninput=()=>{ clearTimeout(searchTimer); sequence++; rosterSequence++; empty(); student.value=''; searchTimer=setTimeout(()=>void loadStudents().catch(e=>error(e.message)),300); };
$('more-students').onclick=()=>void loadStudents(true).catch(e=>error(e.message));
$('more-reviews').onclick=()=>void loadJobs(true).catch(e=>error(e.message));
$('print').onclick=()=>window.print();
$('start-review').onclick=async()=>{
  const button=$('start-review') as HTMLButtonElement, token=sequence; button.disabled=true; clearError();
  try { await request('start_review',selected()); if(token===sequence) {status('Review accepted. Evidence collection has started; AI analysis still needs to run.'); await loadJobs(false,token);} }
  catch(e){ if(token===sequence) error((e as Error).message); } finally{button.disabled=false;}
};
let polling=false;
setInterval(async()=>{
  if(polling||document.hidden||!jobs.some(j=>['queued','collecting'].includes(j.status))) return;
  polling=true;
  try{await loadJobs();}catch{/* Explicit refresh surfaces failures; avoid repeated background error banners. */}finally{polling=false;}
},3000);
void initialize().catch(e=>{status(''); error(e.message+' For a browser fallback, ask your AI client to open the student dashboard with mode=browser.');});
