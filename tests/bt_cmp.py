import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
print('BEFORE', a['m']); print('AFTER ', b['m'])
A = [tuple(x) for x in a['trades']]; B = [tuple(x) for x in b['trades']]
print('trades identical:', A == B, len(A), len(B))
sa, sb = set(A), set(B)
for x in sorted(sa - sb)[:30]: print('  only BEFORE', x)
for x in sorted(sb - sa)[:30]: print('  only AFTER ', x)
