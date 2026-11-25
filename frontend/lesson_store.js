import {api} from './base.js'
export const lessons=()=>api('/api/lessons')
export const shift=({code,target,reasoning,basis,basis_walk})=>api('/api/lessons/'+encodeURIComponent(code)+'/move','POST',{
  target,
  reasoning,
  basis: basis || basis_walk || undefined,
})
export const resign=input=>shift(input)
