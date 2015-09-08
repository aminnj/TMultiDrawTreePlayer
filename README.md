# TMultiDrawTreePlayer

An extension of ``TTreePlayer`` to support multiple draw calls per tree loop

## Context

``TTree::Draw`` is an easy and powerful way to create histograms from trees without the pain to loop over each event manually. Unfortunately, each call to ``Draw`` loops over the whole tree to create the histogram. If you want to create more than one histogram, the runtime is directly proportional to the number of histograms, which is non-acceptable.

``TMultiDrawTreePlayer`` is an extension of ``TTreePlayer``, allowing to *queue* draw call before *executing* them in a one-shot operation. The runtime difference between drawing one or many histograms is negligeable.

## Usage

Grab the source file as well as the header file, and put them where your code is. The first thing to do is to change the default ``TreePlayer`` used by ``TTree`` to our custom one :

```C++
#include <TVirtualTreePlayer.h>
#include <TMultiDrawTreePlayer.h>

TVirtualTreePlayer::SetPlayer("TMultiDrawTreePlayer");
```

This code **must** be executed before any ``TTree`` or ``TChain`` are created. The next step is to retrieve the player instance from your tree. In the following, let's assume you have a ``TTree`` instance named ``t``:

```C++
TMultiDrawTreePlayer* p = dynamic_cast<TMultiDrawTreePlayer*>(t->GetPlayer());
```

You're now ready to *queue* some draw commands. For that, you need to use the new function ``queueDraw``, which accepts the exact same arguments as the usual ``Draw`` function:

```C++
bool queueDraw(const char* varexp, const char* selection, Option_t *option = "", Long64_t nentries = 1000000000, Long64_t firstentry = 0)
```

If you want to *queue* more than one draw call, just call ``queueDraw`` how many times you want! Once you're done, you need to *execute* these draw commands. Use the function ``execute``:
```C++
bool execute()
```

Voila, all your draws are done!

There's one draw-back: you can't use these methods to directly draw and open histograms. You **must** use the ``>>histogram`` syntax inside your draw command to further retrieve the histogram and display it if you want.

## Dictionnary generation

You'll need to generate a ROOT dictionnary to use this class. Use the following command to create the C++ source file containing the dictionnary:

```bash
rootcint -f dictionary.cc -c -p classes.h LinkDef.h
```

## Test build

Use the following command line to compile the class into a shared library. Not really useful, but allows to see if it's building.

```bash
g++ -shared -fPIC `root-config --cflags` -I. dictionary.cc TMultiDrawTreePlayer.cxx `root-config --ldflags --libs` -lTreePlayer
```

## Example

```C++
#include <TVirtualTreePlayer.h>
#include <TMultiDrawTreePlayer.h>
#include <TChain.h>

#include <TDirectory.h>

void test() {

    TVirtualTreePlayer::SetPlayer("TMultiDrawTreePlayer");

    TChain* t = new TChain("t");
    t->Add("output_mc.root");

    TMultiDrawTreePlayer* p = dynamic_cast<TMultiDrawTreePlayer*>(t->GetPlayer());

    p->queueDraw("jet_p4.Pt()>>hist1", "jet_p4.Pt() > 20");
    p->queueDraw("jet_p4.Eta()>>hist2", "jet_p4.Pt() > 20");
    p->queueDraw("jet_p4[0].Pt():jet_p4[1].Pt()>>hist3", "jet_p4.Pt() > 50");

    p->execute();

    gDirectory->Get("hist1")->Draw();
    gDirectory->Get("hist2")->Draw();
    gDirectory->Get("hist3")->Draw();
}
```
