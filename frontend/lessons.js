import {h,badge} from './base.js'
import {heading,feedback,choices} from './view.js'
import {wire} from './forms.js'
import {slots} from './surface_labels.js'
import {signal} from './ring_beacon.js'
import {rings} from './ring_store.js'
import {lessons,shift} from './lesson_store.js'
export async function render(root,session) {
 const [rows,places]=await Promise.all([lessons(),rings()])
 root.innerHTML=heading('课时移场','复核员确认原场停用、目标场同日畅通且不超人数后提交。')+`<ol class="lesson-timing">${rows.map(row=>`
 <li><time>${slots.format(new Date(row.starts_at))}</time><div><h2>${h(row.group_name)}</h2><p>${row.riders} 人 · ${h(places.find(r=>r.code===row.ring)?.title)}</p>${row.origin?badge('已移场','ready'):signal(places.find(r=>r.code===row.ring))}${row.reasoning?`<p>${h(row.reasoning)}</p>`:''}</div>
 ${session.role==='reviewer'&&row.state==='scheduled'?`<details><summary>移场审签</summary><form class="compact-form"><input type="hidden" name="code" value="${h(row.code)}"><label>目标围场<select name="target">${choices(places.filter(r=>r.code!==row.ring),r=>r.title)}</select></label><label>备注<input name="reasoning" minlength="4" required></label><button>签核通知教务</button>${feedback}</form></details>`:''}</li>`).join('')}</ol>`
 for (const form of root.querySelectorAll('form'))wire(form,shift,()=>render(root,session))
}
