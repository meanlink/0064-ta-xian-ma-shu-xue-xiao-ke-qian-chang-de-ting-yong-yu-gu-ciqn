import {h} from './base.js'
import {heading} from './view.js'
import {rings} from './ring_store.js'
import {surface} from './surface_labels.js'
import {signal,dateStamp} from './ring_beacon.js'
export async function render(root) {
 const rows=await rings()
 root.innerHTML=heading('围场牌','开课前查看清场状态、最近巡场记录和同课时核定人数。')+`<div class="ring-paddock">${rows.map(r=>`<section class="ring-lane" data-shelter="${r.sheltered}"><div><h2>${h(r.title)}</h2>${signal(r)}</div><strong class="ring-cap">${r.max_riders}<small> 位</small></strong><p>${h(surface[r.surface])} · ${r.sheltered?'有顶':'露天'}</p>${dateStamp(r)}<div class="ring-link"><a href="#walk">登记巡场</a></div></section>`).join('')}</div>`
}
