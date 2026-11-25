import {h} from './base.js'
import {choices,heading,feedback,table} from './view.js'
import {canEdit,wire} from './forms.js'
import {walks,record} from './walk_store.js'
import {rings} from './ring_store.js'
import {barrier,features} from './surface_labels.js'
export async function render(root,session){
 const [rows,places]=await Promise.all([walks(),rings()])
 const current=rows.filter(r=>r.outcome===null)
 root.innerHTML=heading('巡场记录','留档观察的停用结果用于训练。当班记录用于课时调整。')+`<div class="walkbook"><section>
 ${table(['编号','围场','积水 %','车辙 mm','含水 %','栏位','来源'],current.map(r=>[r.code,r.ring,r.puddle,r.rut,r.moisture,barrier[r.barrier],r.source]))}
 <details><summary>查看 ${rows.length-current.length} 条历史观察</summary>${table(['编号','围场','日期','积水 %','最终处置'],rows.filter(r=>r.outcome!==null).map(r=>[r.code,r.ring,r.observed,r.puddle,r.outcome?'停用':'开课']))}</details></section>
 ${canEdit(session)?`<form class="panel compact-form"><h2>当班记录</h2><label>编号<input name="code" placeholder="W31" required pattern="W[0-9]{2,6}"></label><label>围场<select name="ring">${choices(places,r=>r.title)}</select></label><label>观察日<input name="observed" type="date" value="2026-11-24" required></label>
 <div class="field-readings">${Object.entries(features).map(([key,label])=>`<label>${h(label)}<input name="${h(key)}" type="number" min="0" max="100" required></label>`).join('')}</div>
 <label>栏位<select name="barrier">${Object.entries(barrier).map(([key,label])=>`<option value="${h(key)}">${h(label)}</option>`).join('')}</select></label>
 <label>来源<input name="source" required></label><button>登记巡场</button>${feedback}</form>`:''}</div>`
 wire(root.querySelector('form'),record,()=>render(root,session))
}
