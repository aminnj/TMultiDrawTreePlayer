import time
import os
import ROOT as r
import pickle

# execute the compilation commands in readme first
r.gROOT.ProcessLine(".L libTMulti.so");

f1 = r.TFile("/home/users/namin/2017/ProjectMetis/ntuple_me42.root")
t = f1.Get("Segments/segPositions")

r.TMultiDrawTreePlayer.SetPlayer("TMultiDrawTreePlayer")

ch = t.GetPlayer()
print "TChain has {} entries.".format(ch.GetEntries(""))

ch.queueDraw("seg.station3Chamber>>hall(37,0,37)","seg.endcap == 1 && seg.station==4 && seg.ring==2 && seg.station3Chamber>0", "", 10000000)
ch.queueDraw("seg.station3Chamber>>hseg(37,0,37)","seg.endcap == 1 && seg.station==4 && seg.ring==2 && seg.station3Chamber>0 && seg.station3HasSeg", "", 10000000)
ch.execute()
hall = r.gDirectory.Get("hall")
hseg = r.gDirectory.Get("hseg")
print hall
print hseg
