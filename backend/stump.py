FEATURES=("puddle","rut","moisture")

def impurities(groups):
    total=sum(map(len,groups))
    return sum(2 * sum(rows) * (len(rows)-sum(rows))/len(rows) for rows in groups)/total

def fit(rows):
    candidates=[]
    for feature in FEATURES:
        values=sorted({r[feature] for r in rows})
        for a,b in zip(values, values[1:]):
            pivot=(a+b)/2
            groups=[[r["outcome"] for r in rows if (r[feature]<=pivot)==side] for side in (True,False)]
            if min(map(len,groups))>=2:
                candidates.append((impurities(groups),feature,pivot,groups))
    if not candidates:
        raise ValueError("历史记录不足以形成两个稳定分组")
    impurity,feature,cutoff,groups=sorted(candidates,key=lambda x:x[:3])[0]
    return feature,cutoff,[sum(x)/len(x) for x in groups],impurity
