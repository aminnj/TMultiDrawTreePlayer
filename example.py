import os
import ROOT as r
import api # This powers up TChain ;)

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

    # Woah, these are, like, normal draw statements...
    ch.SetAlias("x","v1<0.5")
    ch.Draw("v2.Eta()>>h1(5,0,100)","!x")
    ch.Draw("v2.Eta()>>h1(5,0,100)","v1<0.5")
    ch.Draw("v2.Pt()>>h2(10,0,100)","v1<0.5")
    ch.Draw("v2.Eta()>>h3(5,0,100)","v3>7")
    ch.Draw("v3>>h5(10,0,100)")

    # Execute all draw statements in a single loop, using N processes, and returning a dictionary of histograms
    hists = ch.GetHists(N=3)
    print(hists)
    print("Histogram mean values: {}".format(map(lambda x: x.GetMean(), hists.values())))

    # Every time, we do another loop, but what if we want to cache histograms if they are the same?
    os.system("rm -f test_cache.pkl")
    hists = ch.GetHists(N=5, file_cache="test_cache.pkl")
    print("Histogram mean values: {}".format(map(lambda x: x.GetMean(), hists.values())))

    # Since we cached them last loop, this one is instantaneous
    hists = ch.GetHists(file_cache="test_cache.pkl")
    print("Histogram mean values: {}".format(map(lambda x: x.GetMean(), hists.values())))
