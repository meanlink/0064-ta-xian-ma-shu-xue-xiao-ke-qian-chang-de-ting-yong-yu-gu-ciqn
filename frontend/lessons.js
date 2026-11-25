import {h,badge} from './base.js'
import {heading,feedback} from './view.js'
import {wire} from './forms.js'
import {slots,barrier} from './surface_labels.js'
import {signal} from './ring_beacon.js'
import {rings} from './ring_store.js'
import {lessons,shift} from './lesson_store.js'

const dateTime = value => {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return ''
  return date.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})
}

export async function render(root,session) {
 const [rows,places]=await Promise.all([lessons(),rings()])
 const placeByCode=Object.fromEntries(places.map(place=>[place.code,place]))

 const targetOptions=(row,review)=>{
   const excluded=review ? row.origin : row.ring
   return places.filter(place=>place.code!==excluded).map(place=>{
     const basis=place.walk || ''
     const selected=place.code===row.ring ? 'selected' : ''
     const detail=basis ? ` · 依据 ${basis}${place.barrier?` · ${barrier[place.barrier]||place.barrier}`:''}` : ''
     return `<option value="${h(place.code)}" data-basis="${h(basis)}" ${selected}>${h(place.title)}${h(detail)}</option>`
   }).join('')
 }

 const initialBasis=(row,review)=>{
   if (review) return row.current_basis || row.target_walk || placeByCode[row.ring]?.walk || ''
   const first=places.find(place=>place.code!==row.ring)
   return first?.walk || ''
 }

 root.innerHTML=heading('课时移场','复核员确认原场停用、目标场同日畅通且不超人数后提交；迟到封栏会把移场单转为待复核，名额仍保留。')+`<ol class="lesson-timing">${rows.map(row=>{
  const currentPlace=placeByCode[row.ring]
  const reviewStates=['review','pending_review','stale']
  const review=reviewStates.includes(row.state)||reviewStates.includes(row.move_status)||row.review_required===true
  const triggerObject = row.trigger_record || (row.trigger && typeof row.trigger === 'object' ? row.trigger : null)
  const trigger=row.trigger_walk || row.trigger_code
    || (typeof row.trigger === 'object' ? row.trigger?.code : row.trigger)
    || triggerObject?.code || ''
  const triggerBarrier=triggerObject?.barrier || row.trigger_barrier
  const triggerSource=row.trigger_source || triggerObject?.source
  const original=row.original_signoff || {
    actor:row.reviewed_by,created_at:row.changed_on,origin_walk:row.walk,
    target_walk:row.target_walk,reasoning:row.reasoning
  }
  return `
 <li class="${review?'lesson-review':row.origin?'lesson-moved':''}" data-lesson-code="${h(row.code)}" data-lesson-state="${h(row.state)}" data-review="${review?'true':'false'}" data-trigger-walk="${h(trigger)}">
  <time>${slots.format(new Date(row.starts_at))}</time>
  <div>
    <h2>${h(row.group_name)}</h2>
    <p>${row.riders} 人 · ${h(currentPlace?.title || row.ring)}</p>
    <div class="lesson-state-line">
      ${review?badge('待复核','held'):(row.origin?badge('已移场','ready'):signal(currentPlace))}
    </div>
    ${review?`<p class="review-reason"><strong>待复核课次</strong>：${h(row.review_reason || '目标场巡场依据已更新，请核对最新可用巡场后重新签核。')}</p>
      <p class="trigger-record" data-testid="trigger-record" data-trigger-code="${h(trigger)}">触发记录：${trigger?`<code>${h(trigger)}</code>`: '未关联记录'}${triggerBarrier?` · ${h(barrier[triggerBarrier]||triggerBarrier)}`:''}${triggerSource?` · ${h(triggerSource)}`:''}</p>
      <p class="occupancy-note"><small>名额仍保留在目标场${row.ring_load!=null&&row.ring_capacity!=null?`（同课时占额 ${row.ring_load}/${row.ring_capacity}）`:''}，重新签核不会重复占位。</small></p>`:''}
    ${row.reasoning?`<p class="move-reasoning">${h(row.reasoning)}</p>`:''}
    ${row.origin?`<p class="move-audit"><small>当前签核：${h(row.reviewed_by || '复核员')}${row.changed_on?` · ${h(dateTime(row.changed_on))}`:''} · 原场依据 <code>${h(row.walk || '')}</code>${row.target_walk?` · 目标依据 <code>${h(row.target_walk)}</code>`:''}</small></p>`:''}
    ${row.origin?`<details class="original-signoff"><summary>原签核可查</summary><p><small>首次签核：${h(original.actor || '')} · ${h(dateTime(original.created_at))} · 原场依据 <code>${h(original.origin_walk || row.walk || '')}</code> · 目标依据 <code>${h(original.target_walk || row.target_walk || '')}</code></small></p>${original.reasoning?`<p>${h(original.reasoning)}</p>`:''}</details>`:''}
  </div>
  ${session.role==='reviewer'&&(row.state==='scheduled'||review)?`<details ${review?'open':''}><summary>${review?'重新签核':'移场审签'}</summary><form class="compact-form">
    <input type="hidden" name="code" value="${h(row.code)}">
    <input type="hidden" name="basis" value="${h(initialBasis(row,review))}">
    <label>目标围场<select name="target" data-basis-select>${targetOptions(row,review)}</select></label>
    <label>备注<input name="reasoning" minlength="4" required value="${review?h(row.reasoning || ''):''}"></label>
    <button type="submit">${review?'重新签核':'签核通知教务'}</button>
    ${feedback}
  </form></details>`:''}
 </li>`}).join('')}</ol>`

 for (const select of root.querySelectorAll('select[data-basis-select]')) {
   const form=select.closest('form')
   const basis=form.querySelector('input[name=basis]')
   const sync=()=>{ basis.value=select.selectedOptions[0]?.dataset.basis || '' }
   select.addEventListener('change',sync)
   sync()
 }
 for (const form of root.querySelectorAll('form')) {
   wire(form,shift,()=>render(root,session),async error=>{
     if (error.status===409) await render(root,session)
   })
 }
}
