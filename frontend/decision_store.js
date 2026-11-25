import {api,waitJob} from './base.js'
export const calls=()=>api('/api/cutoff')
export async function calculate(code) {
 const {job_id}=await api('/api/cutoff/'+encodeURIComponent(code),'POST',{})
 return waitJob(job_id)
}
