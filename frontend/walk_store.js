import {api} from './base.js'
export const walks=()=>api('/api/walks')
export const record=value=>api('/api/walks','POST',{...value,puddle:Number(value.puddle),rut:Number(value.rut),moisture:Number(value.moisture)})
