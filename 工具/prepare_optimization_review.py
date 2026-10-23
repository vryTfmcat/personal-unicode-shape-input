"""Attach quality annotations to the review UI without changing primary assignments."""
import gzip,json,re,html
from pathlib import Path
from shape_quality_v2 import ROOT
from shape_strategy_lab import save


def main():
    run=Path(json.loads((ROOT/'最新优化.json').read_text(encoding='utf-8'))['run'])
    summary=json.loads((run/'摘要.json').read_text(encoding='utf-8'));model=json.loads((run/'模型.json').read_text(encoding='utf-8'))
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as stream:qa={r['cp']:r for r in map(json.loads,stream)}
    names={'alternate-font-disagreement':'第二字体字形分歧','alternate-font-render-failed':'第二字体渲染失败',
        'native-size-fallback':'采用原生字号回退','few-ink-pixels':'墨迹过少，待核对','weak-ink-intensity':'弱墨迹，待核对'}
    save(run/'样本质量待核对.json',{'characters':[dict(r,reviewMeanings=[names[k] for k in r['reviewFlags']]) for r in qa.values() if r['reviewFlags']]})
    page=run/'单层分桶核对.html';content=page.read_text(encoding='utf-8');match=re.search(r'const data=(.*?);const \$=',content,re.S);data=json.loads(match.group(1))
    for r in data['rows']:
        q=qa.get(r['cp'])
        if q:r['qualityNote']='；'.join(names[k] for k in q['reviewFlags']) or ('两字体一致视图' if q['acceptedViews']==2 else '单一参考视图')
    payload=json.dumps(data,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    content=re.sub(r'const data=.*?;const \$=',lambda m:'const data='+payload+';const $=',content,count=1,flags=re.S)
    content=content.replace("esc(r.status)+'<br><small>'", "esc(r.status)+'<br>'+esc(r.qualityNote||'特殊收纳')+'<br><small>'")
    content=content.replace('状态／参考字体','状态／样本质量／参考字体');page.write_text(content,encoding='utf-8')
    rows=[]
    for r in summary['comparisons']:
        m=r['metrics'];selected=' ✓ 当前候选' if r['id']==summary['winner'] else ''
        rows.append('<tr><td>'+html.escape(r['id']+selected)+'</td><td>'+f'{m["commonFeatureMSE"]:.5f}'+'</td><td>'+f'{m["sampleNeighborSamePrimary"]:.2%}'+'</td><td>'+str(m['minBucket'])+'～'+str(m['maxBucket'])+'</td></tr>')
    review='''<!doctype html><meta charset="utf-8"><title>第一次优化对照</title><style>body{font:16px system-ui;max-width:1100px;margin:28px auto;padding:0 20px;background:#f4f6f9;color:#203348}table{width:100%;border-collapse:collapse;background:white}th,td{padding:12px;border-bottom:1px solid #dbe3ec;text-align:left}a{color:#2164a0}</style><h1>第一次优化 · 算法对照</h1><p>同一字符集、同一新特征空间评价；随机抽取512字，每字5个近邻。该指标不是真人视觉正确率。当前候选选自新特征＋最小费用流四个种子；旧版与其他对照全部保留。</p><p><a href="单层分桶核对.html">分桶核对</a> · <a href="第一次优化报告.md">详细报告</a> · <a href="字符迁移.json">迁移清单</a> · <a href="样本质量待核对.json">样本质量标记</a></p><table><thead><tr><th>方案</th><th>共有特征均方距离（低较好）</th><th>近邻同主桶率</th><th>桶大小</th></tr></thead><tbody>ROWS</tbody></table><p>固定中心下，最小费用流的整数分配代价最优；不同的中心迭代路径仍会落入不同局部结果，因此不能保证它在所有种子下都胜过贪心。机器指标显示新特征方案有改善，最终取舍仍等待人工相似对。</p>'''.replace('ROWS',''.join(rows))
    (run/'优化对照.html').write_text(review,encoding='utf-8')
    (run/Path(__file__).name).write_bytes(Path(__file__).read_bytes());print(run/'优化对照.html')


if __name__=='__main__':main()
