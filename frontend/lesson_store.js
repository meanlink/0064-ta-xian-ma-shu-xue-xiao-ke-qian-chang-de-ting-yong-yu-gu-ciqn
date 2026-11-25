import {api} from './base.js'
export const lessons=()=>api('/api/lessons')
export const shift=({code,target,reasoning})=>api('/api/lessons/'+encodeURIComponent(code)+'/move','POST',{target,reasoning})
