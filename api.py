import pickle
import time
import os
import re
import ROOT as r
r.gROOT.SetBatch()
from multiprocessing import Value, Process, Queue

class TimedQueue():
    def __init__(self,N=10):
        self.N = N
        self.vals = [0]
        self.times = [time.time()]

    def get_last_val(self):
        return self.vals[-1]

    def add_val(self,val):
        self.vals.append(val)
        self.times.append(time.time())
        self.clip()

    def clip(self):
        if len(self.vals) > self.N:
            self.vals.pop(0)
            self.times.pop(0)

    def get_rate(self):
        dx = (self.vals[-1] - self.vals[0])
        dt = (self.times[-1] - self.times[0])
        return dx/dt

class Drawables(list):
    def __init__(self, *args):
        super(Drawables, self).__init__(*args)

        self.make_consistent()

    def __repr__(self):
        if len(self) > 10:
            joined = "\n\t".join(map(lambda x:x.__repr__(),self[:3]))
            joined += "\n\t... {} more ...\n\t".format(len(self)-6)
            joined += "\n\t".join(map(lambda x:x.__repr__(),self[-3:]))
        else:
            joined = "\n\t".join(map(lambda x:x.__repr__(),self))
        return "<Drawables \n\t{}\n>".format(joined)

    def make_consistent(self):
        # if the histogram has already been seen in this set of drawables
        # append _idup<#> to the end, where <#> keeps increasing to guarantee
        # uniqueness.
        seen = set([])
        latest_idx = {}
        for d in self:
            hn = d.get_histname()
            if hn in seen:
                idx = latest_idx.get(hn,0)+1
                latest_idx[hn] = idx
                hn = "{}_idup{}".format(hn,idx)
                d.histname = hn
            seen.add(d.get_histname())

class Drawable(object):
    def __init__(self,
            varexp = "",
            selection = "",
            option = "goff",
            nentries = 1000000000,
            firstentry = 0,
            ):
        self.varexp = varexp
        self.selection = selection
        self.option = option
        self.nentries = nentries
        self.firstentry = firstentry
        self.histname = ""
        self.histbinning = ""

        self.parse_varexp()

    def __repr__(self):
        return "<Drawable (\"{}>>{}{}\", \"{}\", \"{}\", {}, {}) at {}>".format(
                self.varexp,
                self.histname,
                self.histbinning,
                self.selection,
                self.option,
                self.nentries,
                self.firstentry,
                hex(id(self)),
                )

    def parse_varexp(self):
        if self.histname: return

        # try >>histname pattern
        tmp = self.varexp.rsplit(">>",1)
        if len(tmp) == 2:
            namebin = tmp[1]
            self.varexp = tmp[0]
            if "(" in tmp[1]:
                self.histname = tmp[1].split("(")[0]
                self.histbinning = "("+tmp[1].split("(")[1]
            else:
                self.histname = tmp[1]

    def get_histname(self):
        return self.histname

    def get_histbinning(self):
        return self.histbinning

    def get_histnamebinning(self):
        if self.histbinning:
            return "{}{}".format(self.histname, self.histbinning)
        else:
            return self.histname

    def get_hash(self):
        return hash("|".join(map(str,[self.varexp,self.histname,self.histbinning,self.nentries,self.firstentry])))

class BaseTChain():

    def __init__(self, ch):

        self.ch = ch
        self.player = None
        self.nentries = -1

        self.hists = {}

        self.initialize_tmultidraw()
        self.initialize_chain()

        self.executed = True

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
        self.player.queueDraw("{}>>{}".format(varexp,hist), selection, option, nentries, firstentry)
        self.executed = False

    def execute(self):
        if not self.executed:
            self.get_entries()
            # argument is `quiet` -- True does not show progress bar
            self.player.execute(False)

        self.executed = True

    def execute_parallel(self, first,numentries,done,total,bytesread):
        r.gErrorIgnoreLevel = r.kError
        self.nentries = self.player.GetEntries("")
        r.gErrorIgnoreLevel = -1

        quiet = True
        self.player.execute(quiet,first,numentries,done,total,bytesread)

oldinit = r.TChain.__init__
class ParallelTChain(r.TChain):

    def __init__(self, *args):
        oldinit(self, *args)

        self.ch = self
        self.queued = []

        self.drawables = Drawables()

        self.executed = True

    def Draw(self, varexp, selection="", option="goff", nentries=1000000000, firstentry=0):
        # Force goff since we're not using this interactively
        option += "goff" if "goff" not in option else ""
        d = Drawable(
            varexp = varexp,
            selection = selection,
            option = option,
            nentries = nentries,
            firstentry = firstentry,
            )
        self.drawables.append(d)
        self.executed = False

    def pre_execution(self):
        self.queued = []
        self.drawables.make_consistent()
        for d in self.drawables:
            info = [
                d.varexp,
                d.get_histnamebinning(),
                d.selection,
                d.option,
                d.nentries,
                d.firstentry,
                ]
            self.queued.append(info)

    def GetHists(self, N=1, use_custom_tqdm=True, file_cache=None):
        self.pre_execution()

        _, con_width = map(int,os.popen('stty size', 'r').read().split())

        # if user wants to cache histograms in file, then make sure
        # the hash of all the queued draws + list of all files in tchain
        # + all the aliases and their values
        # matches what was in the file
        # In principle, if those match, then results must be identical
        file_hash = hash("".join(sorted([x.GetTitle() for x in (self.ch.GetListOfFiles())])))
        # FIXME on osx, the below line will cause a crash after looping when an alias is used
        # does something special happen when calling GetAlias() or GetListOfAliases() before running?
        if os.uname()[0] == "Darwin":
            alias_hash = 1
        else:
            alias_hash = hash(tuple(sorted([(x.GetName(),self.ch.GetAlias(x.GetName())) for x in (self.ch.GetListOfAliases() or [])])))
        queue_hash = hash(tuple(map(tuple,sorted(self.queued))))
        total_hash = hash(queue_hash+file_hash+alias_hash)
        if file_cache and os.path.exists(file_cache):
            with open(file_cache,"r") as fh:
                data = pickle.load(fh)
                hash_cache = data["hash"]
                if hash_cache == total_hash:
                    return data["hists"]

        # take list of dicts of histname:histogram items
        # and reduce them by adding and removing the prefix up to the first
        # underscore
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

        # take variety of things and put histograms from loop into a queue
        def get_hists(q, ch, queued, num, first, numentries, done, total, bytesread):
            prefix = "md{}_".format(num)
            clone = ch.Clone("ch_{}".format(prefix))
            md = BaseTChain(clone)
            for x_ in queued:
                x = x_[:]
                x[1] = "{}{}".format(prefix,x[1])
                md.queue(*x)
            md.execute_parallel(first,numentries,done.get_obj(),total.get_obj(), bytesread.get_obj())
            hists = {}
            hist_names = map(lambda x:x[1].split("(",1)[0], queued)
            for hn in set(hist_names):
                hists[hn] = r.gDirectory.Get(prefix+hn)
            q.put(hists)
            return 0

        # compute event splitting for N jobs
        first, last = 0, int(self.ch.GetEntries())
        size = int((last-first) / N)
        firsts = [first+i*size for i in range(N)] + [last]
        diffs = map(lambda x: x[1]-x[0],zip(firsts[:-1],firsts[1:]))
        firsts_and_nentries = zip(firsts[:-1],diffs)

        if use_custom_tqdm:
            r.gROOT.ProcessLine(".L {}/tqdm.h".format(os.path.realpath(__file__).rsplit("/",1)[0]))
            bar = r.tqdm()

        os.nice(10)
        q = Queue(N)
        dones, totals, bytess, workers = [], [], [], []
        for i, (first, numentries) in enumerate(firsts_and_nentries):
            done, total, bytesread = Value("i",0), Value("i",0), Value("i",0)
            worker = Process(target=get_hists, args=[q,self.ch,self.queued,i,first,numentries,done,total,bytesread])
            workers.append(worker)
            worker.start()
            dones.append(done.get_obj())
            bytess.append(bytesread.get_obj())
            totals.append(total.get_obj())

        def get_sum(cs):
            return sum(map(lambda x:x.value, cs))

        try:
            ioq = TimedQueue(N=30)
            if use_custom_tqdm:
                total = last
                done = get_sum(dones)
                bytesread = get_sum(bytess)
                while done < total:
                    done = get_sum(dones)
                    bytesread = get_sum(bytess)
                    ioq.add_val(1.0*bytesread/1e6)
                    bar.progress(done,total,True)
                    which_done = map(lambda x:(x[0].value==x[1].value)and(x[0].value>0), zip(dones,totals))
                    if con_width > 110:
                        label = "[{:.1f}MB @ {:.1f}MB/s]".format(ioq.get_last_val(),ioq.get_rate())
                        label += " [{}]".format("".join(map(lambda x:unichr(0x2022) if x else unichr(0x2219),which_done)).encode("utf-8"))
                    else:
                        label = ""
                    bar.set_label(label)
                    time.sleep(0.04)
                label = "[{:.1f}MB @ {:.1f}MB/s]".format(ioq.get_last_val(),ioq.get_rate())
                label += " [{}]".format("".join([unichr(0x2022) for _ in dones]).encode("utf-8"))
                bar.set_label(label)
                bar.progress(total,total,True)
            else:
                from tqdm import tqdm
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
        except KeyboardInterrupt as e:
            print("[!] Early keyboard interruption...continuing with histograms anyway")

        dicts = []
        for iw in range(len(workers)):
            dicts.append(q.get())

        for worker in workers:
            worker.join()

        # don't let one tqdm bar clobber another
        print

        reduced_hists = reduce_hists(dicts)

        # if user wants to cache histograms in file,
        # then dump the hists as well as a hash
        if file_cache:
            with open(file_cache,"w") as fh:
                data = {"hash": total_hash, "hists": reduced_hists}
                pickle.dump(data,fh)

        self.executed = True

        return reduced_hists

r.TChain = ParallelTChain
