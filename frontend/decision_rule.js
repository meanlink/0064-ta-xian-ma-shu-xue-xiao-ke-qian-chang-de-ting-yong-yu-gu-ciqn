import {h,badge} from './base.js'
import {features} from './surface_labels.js'
export function advice(row) {
 return `<article class="decision-rule"><h2>${h(row.title)}</h2>${badge(row.close_recommended?'建议停课或移场':'模型建议可用',row.close_recommended?'held':'ready')}
 <dl><dt>断点</dt><dd>${h(features[row.feature])} &gt; ${row.cutoff}</dd><dt>停用概率</dt><dd><meter min="0" max="1" low=".25" high=".75" optimum="0" value="${row.probability}"></meter> ${Math.round(row.probability*100)}%</dd>
 <dt>保留样本准确率</dt><dd>${Math.round(row.calibration.accuracy*100)}%（${row.calibration.holdout} 条）</dd></dl></article>`
}
