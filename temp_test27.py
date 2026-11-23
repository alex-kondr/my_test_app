# -*- coding: utf-8 -*-
import re

val = u"5 баллов из 5"
m = re.search(r'(\d+)\s*балл\w*\s*из\s*(\d+)', val)
print "Match 1:", bool(m)

m2 = re.search(ur'(\d+)\s*балл\w*\s*из\s*(\d+)', val)
print "Match 2 (with ur):", bool(m2)
