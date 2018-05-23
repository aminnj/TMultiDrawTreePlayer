import time
import os
import ROOT as r
r.gROOT.SetBatch()
import pickle

class MultiDrawer(object):

    def __init__(self, ch=None):
        self.ch = ch
        self.player = None
        self.nentries = -1

        self.hist_names = []
        self.hists = {}

        self.initialize_tmultidraw()
        self.initialize_chain()

    def initialize_tmultidraw(self):
        import ROOT
        if not hasattr(ROOT, "TMultiDrawTreePlayer"):
            # execute the compilation commands in readme first
            ROOT.gROOT.ProcessLine(".L {}/libTMulti.so".format(__file__.rsplit("/",1)[0]))
            ROOT.TMultiDrawTreePlayer.SetPlayer("TMultiDrawTreePlayer")

    def initialize_chain(self):
        if not self.ch: return

        self.player = self.ch.GetPlayer()

    def queue(self, varexp, hist="htemp", selection="", option="goff", nentries=1000000000, firstentry=0):
        self.hist_names.append(hist.split("(",1)[0])
        self.player.queueDraw("{}>>{}".format(varexp,hist), selection, option, nentries, firstentry)

    def execute(self):
        r.gErrorIgnoreLevel = r.kError
        self.nentries = self.player.GetEntries("")
        r.gErrorIgnoreLevel = -1
        # argument is `quiet` -- True does not show progress bar
        self.player.execute(False)

    def get_hists(self):
        if not self.hists:
            for hn in set(self.hist_names):
                self.hists[hn] = r.gDirectory.Get(hn)
        return self.hists

