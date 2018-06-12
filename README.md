# TMultiDrawTreePlayer

### Note: this is just a fork with more features -- I take no credit away from the original author for the idea/main implementation.

An extension of ``TTreePlayer`` to support multiple draw calls per tree loop

## Context

``TTree::Draw`` is an easy and powerful way to create histograms from trees without the pain to loop over each event manually. Unfortunately, each call to ``Draw`` loops over the whole tree to create the histogram. If you want to create more than one histogram, the runtime is directly proportional to the number of histograms.
``TMultiDrawTreePlayer`` is an extension of ``TTreePlayer``, allowing to *queue* draw call before *executing* them in a one-shot operation.

## Setup

`source setup.sh`.

## Example

The below script is also in `example.py`.

Note that the original implementation is available through `api.MultiDrawer`, but drawing from ROOT files is often limited
by CPU in a single thread due to unpacking the data. We can take advantage of this to easily multiply the speed by
executing the single loop with N processes.

```python
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
for i in range(3,15):
    md.queue("dilep_p4.M()","h{}(100,0,150)".format(i),"hyp_class==4")

# Use N threads - generally results in factor of N speedup
# Since we're limited by CPU for unpacking objects from the rootfile
hists = md.execute(N=8)
print "means:", map(lambda x: x.GetMean(), hists.values())
```



