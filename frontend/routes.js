import {mount} from './base.js'
import {render as rings} from './rings.js'
import {render as walk} from './walk.js'
import {render as cutoff} from './cutoff.js'
import {render as lessons} from './lessons.js'

const pages = {
  rings: '围场牌',
  walk: '巡场记录',
  cutoff: '停用判别',
  lessons: '课时移场'
}
const renderers = {rings, walk, cutoff, lessons}
mount({title: '踏线 · 马术学校课前场地停用预估', kicker: '牧岸马术学校 · 课前巡场牌', pages, render: (key, root, session) => renderers[key](root, session)})
