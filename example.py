import ROOT as r
from api import ParallelMultiDrawer
import time

def make_example_tree(fname):
    """
    Make ~50MB example tree to show drawing capabilities
    """
    import os
    if os.path.exists(fname):
        print("Example tree already exists")
        return

    print("Making example tree")

    import random
    from tqdm import tqdm

    f = r.TFile(fname, "RECREATE")
    t = r.TTree("t","tree")

    v1 = r.std.vector("float")()
    v2 = r.std.vector("TLorentzVector")()
    v3 = r.std.vector("int")()
    t.Branch("v1",v1)
    t.Branch("v2",v2)
    t.Branch("v3",v3)

    for _ in tqdm(range(300000)):
        v1.clear()
        for _ in range(5):
            v1.push_back(random.random())
        v2.clear()
        for _ in range(3):
            v2.push_back(r.TLorentzVector(10.*random.random(),1.*random.random(),1.,15.))
        v3.clear()
        for _ in range(3):
            v3.push_back(random.randint(1,15))
        # Fill 5 times with the same values...things get compressed more
        for _ in range(5):
            t.Fill()
    t.Write()
    f.Write()
    t.Print()
    f.Close()

    print("Done making example tree")


if __name__ == "__main__":

    make_example_tree("test.root")

    ch = r.TChain("t")
    ch.Add("test.root")

    # Make a multidrawer object
    md = ParallelMultiDrawer(ch)

    # Queue up many draw statements -- expression, histogram, selector
    # These are all done in a single loop through the chain
    md.queue("v2.Eta()","h1(5,0,100)","v1<0.5")
    md.queue("v2.Pt()","h2(10,0,100)","v1<0.5")
    md.queue("v2.Eta()","h3(5,0,100)","v3>7")
    md.queue("v3","h5(10,0,100)")

    # Use N threads - generally results in factor of N speedup
    # Since we're limited by CPU for unpacking objects from the rootfile
    hists = md.execute(N=5)
    print("Histogram mean values: {}".format(map(lambda x: x.GetMean(), hists.values())))

    # Now try with conventional TTree Draw statements
    print("Now trying conventional tree drawing...")
    N = ch.GetEntries()
    t0 = time.time()
    ch.Draw("v2.Eta()>>h1(5,0,100)","v1<0.5","goff")
    ch.Draw("v2.Pt()>>h2(10,0,100)","v1<0.5","goff")
    ch.Draw("v2.Eta()>>h3(5,0,100)","v3>7","goff")
    ch.Draw("v3>>h5(10,0,100)","","goff")
    print("Regular draw statements processed at {:.1f}kHz".format(0.001*N/(time.time()-t0)))
