import json
from lupa import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
def load(fn,key):
    s=open(fn).read(); i=s.index(key+' = [['); return lua.execute(s[i+len(key)+5:s.index(']]',i)])
Q=load('fdb.lua','questData'); N=load('foreverNpcDB.lua','npcData'); O=load('foreverObjectDB.lua','objectData')
ZONES={"durotar":14,"mulgore":215,"tirisfal":85,"elwynn":12,"dunmorogh":1,"teldrassil":141,
 "barrens":17,"silverpine":130,"westfall":40,"lochmodan":38,"darkshore":148,"redridge":44,"stonetalon":406,
 "ashenvale":331,"duskwood":10,"wetlands":11,"hillsbrad":267,"thousandneedles":400}
CITIES={"orgrimmar":1637,"thunderbluff":1638,"undercity":1497,"stormwind":1519,"ironforge":1537,"darnassus":1657,"deeprun":2257}
DUNG={"ragefire":2437,"wailing":718,"deadmines":1581,"shadowfang":209,"blackfathom":719,"stockade":717,"gnomeregan":721,"razorfenkraul":491,"rfk_area":1717}
SUB={9,132,154,188,220,363,24,221}           # starting valley subzones
SORTS={-61,-81,-82,-141,-161,-162,-261,-262,-263,-101,-121,-181,-182,-201,-24,-264,-304,-324}  # classes and professions
MAXL=30
def zs(ent,sp,zi):
    z=set()
    if ent is None: return z
    if ent[zi]: z.add(ent[zi])
    if ent[sp]: z|=set(ent[sp].keys())
    return z
def starter(v):
    z=set(); sb=v[2]
    if sb:
        if sb[1]:
            for n in sb[1].values(): z|=zs(N[n],7,9)
        if sb[2]:
            for o in sb[2].values(): z|=zs(O[o],4,5)
    return z
out={k:[] for k in list(ZONES)+list(CITIES)+list(DUNG)}
geo={**ZONES,**CITIES}
for q,v in Q.items():
    zo=v[17] or 0; lvl=v[5] or 0; st=starter(v)
    for name,zid in ZONES.items():
        if zo==zid or (zo in SUB and zid in st) or (zo in SORTS and 0<lvl<=MAXL and zid in st): out[name].append(q)
    for name,zid in CITIES.items():
        if (zo==zid and lvl<=MAXL) or (zo in SORTS and 0<lvl<=MAXL and zid in st and not any(z in st for z in ZONES.values())): out[name].append(q)
    for name,zid in DUNG.items():
        if zo==zid and lvl<=MAXL+2: out[name].append(q)
old=json.load(open('old_full.json'))
for k,v in old.items(): out[k]=sorted(set(out.get(k,[]))|set(v))
out={k:sorted(set(v)) for k,v in out.items() if v}
json.dump(out,open('zones.json','w'))
allq=set().union(*out.values())
print({k:len(v) for k,v in out.items()}, "total unique:",len(allq))
