import {empty} from './base.js'
import {heading,choices,feedback} from './view.js'
import {canEdit,wire} from './forms.js'
import {rings} from './ring_store.js'
import {calls,calculate} from './decision_store.js'
import {advice} from './decision_rule.js'
export async function render(root,session) {
 const [rows,sites]=await Promise.all([calls(),rings()])
 root.innerHTML=heading('停用判别','小样本分类树只分一层，给出可核对断点。封栏记录优先于模型。')+`<div class="call-board">
 <div>${rows.map(advice).join('')||empty('还没有判别。选择有当班巡场的围场运行计算。')}</div>
 <aside class="panel"><h2>课前决策口径</h2><p>漏掉一次停用的代价设为一次误停的三倍，停用概率门槛取 25%。</p>
 ${canEdit(session)?`<form class="compact-form"><label>围场<select name="code" required>${choices(sites.filter(r=>r.walk),r=>r.title)}</select></label><button>判别停用</button>${feedback}</form>`:''}</aside></div>`
 wire(root.querySelector('form'),data=>calculate(data.code),()=>render(root,session))
}
