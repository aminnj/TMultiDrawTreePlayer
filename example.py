import ROOT as r
from api import ParallelMultiDrawer

# Make a chain like usual
chain = r.TChain("t")
chain.Add("/nfs-7/userdata/namin/tupler_babies/merged/FT/v1.05_v1/output/DY_high.root")

# Make a multidrawer object
md = ParallelMultiDrawer(chain)

# Queue up many draw statements -- expression, histogram, selector
# These are all done in a single loop through the chain
md.queue("lep2_p4.pt()","h1(50,0,250)","hyp_class==3")
md.queue("ht","h2(50,0,450)","hyp_class==4")
for i in range(3,10):
    md.queue("dilep_p4.M()","h{}(100,0,150)".format(i),"hyp_class==4")

# Use N threads - generally results in factor of N speedup
# Since we're limited by CPU for unpacking objects from the rootfile
hists = md.execute(N=8)
print "means:", map(lambda x: x.GetMean(), hists.values())
