import {h,badge} from './base.js'
import {barrier} from './surface_labels.js'
export const signal=row=>badge(row.close_recommended?'建议停用':barrier[row.barrier]||'待巡场',row.close_recommended?'held':'')
export const dateStamp=row=>`<small>${h(row.observed||'')} · ${h(row.walk||'待巡场')}</small>`
