import ROOT as r
r.gROOT.SetBatch()

from api import MultiDrawer

chain = r.TChain("t")
chain.Add("WW.root")
md = MultiDrawer(chain)
md.queue("lep1_p4.pt()","h1(1,0,50)","hyp_class==4")
md.queue("lep2_p4.pt()","h2(1,0,50)","hyp_class==4")
for i in range(3,10):
    md.queue("dilep_p4.M()","h{}".format(i),"hyp_class==4")
md.execute()
hists = md.get_hists()
print "means:", map(lambda x: x.GetMean(), hists.values())
