import time
from tqdm import tqdm
import ROOT as r
r.gROOT.SetBatch()
from multiprocessing import Value, Process, Queue

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
        self.player.execute._threaded = True

    def queue(self, varexp, hist="htemp", selection="", option="goff", nentries=1000000000, firstentry=0):
        self.hist_names.append(hist.split("(",1)[0])
        self.player.queueDraw("{}>>{}".format(varexp,hist), selection, option, nentries, firstentry)

    def get_entries(self):
        r.gErrorIgnoreLevel = r.kError
        self.nentries = self.player.GetEntries("")
        r.gErrorIgnoreLevel = -1
        return self.nentries

    def execute(self):
        self.get_entries()
        # argument is `quiet` -- True does not show progress bar
        self.player.execute(False)

        return self.get_hists()

    def execute_parallel(self, first,numentries,done,total):
        r.gErrorIgnoreLevel = r.kError
        self.nentries = self.player.GetEntries("")
        r.gErrorIgnoreLevel = -1

        # self.player.execute(False,first,numentries,done,total)
        self.player.execute(True,first,numentries,done,total)

    def get_hists(self):
        if not self.hists:
            for hn in set(self.hist_names):
                self.hists[hn] = r.gDirectory.Get(hn)
        return self.hists

class ParallelMultiDrawer(object):

    def __init__(self, ch=None):
        self.ch = ch
        self.hist_names = []
        self.queued = []

    def queue(self, varexp, hist="htemp", selection="", option="goff", nentries=1000000000, firstentry=0):
        self.hist_names.append(hist.split("(",1)[0])
        self.queued.append([varexp, hist, selection, option, nentries, firstentry])

    def execute(self, N=1, use_my_tqdm=True):

        def reduce_hists(dicts):
            d_master = {}
            for idx,d in enumerate(dicts):
                for hname, h in d.items():
                    if not h: continue
                    stripped_name = hname.split("_",1)[-1]
                    if stripped_name not in d_master:
                        d_master[stripped_name] = h.Clone(stripped_name)
                    else:
                        d_master[stripped_name].Add(h)
            return d_master

        def get_hists(q, ch, queued, num, first, numentries, done, total):
            prefix = "md{}_".format(num)
            md = MultiDrawer(ch.Clone("ch_{}".format(prefix)))
            for x_ in queued:
                x = x_[:]
                x[1] = "{}{}".format(prefix,x[1])
                md.queue(*x)
            md.execute_parallel(first,numentries,done.get_obj(),total.get_obj())
            hists = {}
            hist_names = map(lambda x:x[1].split("(",1)[0], queued)
            for hn in set(hist_names):
                hists[hn] = r.gDirectory.Get(prefix+hn)
            q.put(hists)
            return 0


        first, last = 0, int(self.ch.GetEntries())
        size = int((last-first) / N)
        firsts = [first+i*size for i in range(N)] + [last]
        diffs = map(lambda x: x[1]-x[0],zip(firsts[:-1],firsts[1:]))
        firsts_and_nentries = zip(firsts[:-1],diffs)

        if use_my_tqdm:
            r.gROOT.ProcessLine(".L tqdm.h")
            bar = r.tqdm()

        q = Queue(N)
        dones, totals, workers = [], [], []
        for i, (first, numentries) in enumerate(firsts_and_nentries):
            done, total = Value("i",0), Value("i",0)
            worker = Process(target=get_hists, args=[q,self.ch,self.queued,i,first,numentries,done,total])
            workers.append(worker)
            worker.start()
            dones.append(done.get_obj())
            totals.append(total.get_obj())

        def get_sum(cs):
            return sum(map(lambda x:x.value, cs))

        if use_my_tqdm:
            total = last
            done = get_sum(dones)
            while done < total-1:
                done = get_sum(dones)
                bar.progress(done,total,True)
                time.sleep(0.1)
        else:
            total = last
            prev_done = get_sum(dones)
            done = get_sum(dones)
            with tqdm(total=total) as pbar:
                while done < total-1:
                    done = get_sum(dones)
                    update = done - prev_done
                    prev_done = done
                    pbar.update(update)
                    time.sleep(0.1)

        dicts = []
        for iw in range(len(workers)):
            dicts.append(q.get())

        for worker in workers:
            worker.join()

        return reduce_hists(dicts)


