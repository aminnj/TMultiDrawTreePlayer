# TMultiDrawTreePlayer

#### Note: this is just a fork with more features -- I take no credit away from the original author for the idea/main implementation.

An extension of ``TTreePlayer`` to support 
* multiple draw calls per tree loop
* multithreaded looping (with python API through multiprocessing)
* caching of identical expression values, selection strings (boolean), and selection values (weights)

## Setup

* `source setup.sh`
* `python example.py`

## Example

The below script is basically just `example.py`. Run it with `python example.py`. It makes a test TTree for you automatically.

```python
import os
import ROOT as r
import api # This powers up TChain ;)

# r.TChain is actually a souped-up subclass of TChain
ch = r.TChain("t")
ch.Add("test.root")

# Woah, these are, like, normal draw statements...
ch.Draw("v2.Eta()>>h1(5,0,100)","v1<0.5")
ch.Draw("v2.Pt()>>h2(10,0,100)","v1<0.5")
ch.Draw("v3>>h5(10,0,100)")

# Execute all draw statements in a single loop, using N processes, and returning a dictionary of histograms
hists = ch.GetHists(N=3)
print(hists)
print("Histogram mean values: {}".format(map(lambda x: x.GetMean(), hists.values())))
```



