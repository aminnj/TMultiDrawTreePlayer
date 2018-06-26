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


class BaseTChain():

    def __init__(self, ch):

        self.ch = ch
        self.player = None
        self.nentries = -1

        self.hist_names = []
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
        self.hist_names.append(hist.split("(",1)[0])
        self.player.queueDraw("{}>>{}".format(varexp,hist), selection, option, nentries, firstentry)
        self.executed = False

    def execute(self):
        if not self.executed:
            self.get_entries()
            # argument is `quiet` -- True does not show progress bar
            self.player.execute(False)

        self.executed = True
        return self.get_hists()

    def execute_parallel(self, first,numentries,done,total,bytesread):
        r.gErrorIgnoreLevel = r.kError
        self.nentries = self.player.GetEntries("")
        r.gErrorIgnoreLevel = -1

        quiet = True
        self.player.execute(quiet,first,numentries,done,total,bytesread)

    def get_hists(self):
        if not self.executed:
            self.execute()

        if not self.hists:
            for hn in set(self.hist_names):
                self.hists[hn] = r.gDirectory.Get(hn)
        return self.hists

oldinit = r.TChain.__init__
class ParallelTChain(r.TChain):

    def __init__(self, *args):
        oldinit(self, *args)

        self.ch = self
        self.hist_names = []
        self.queued = []

        self.executed = True

    # def Draw(self, varexp, hist=None, selection="", option="goff", nentries=1000000000, firstentry=0):
    def Draw(self, varexp, selection="", option="goff", nentries=1000000000, firstentry=0):

        # If option doesn't have goff, add it
        option += "goff" if "goff" not in option else ""

        # Separate blah>>h into 'blah' and 'h'
        tmp = varexp.rsplit(">>",1)
        if len(tmp) > 1: hist = tmp[1]
        else: hist = ""
        varexp = tmp[0]

        # If histogram is unnamed, name it.
        binning = ""
        if not hist or not hist.strip():
            hname = "htemp_1"
        else:
            tokens = hist.split("(",1)
            if len(tokens) == 1: hname, binning = tokens[0], ""
            else: hname, binning = tokens[0], "("+tokens[1]
        # If histogram name is a duplicate, increment a number until it's not anymore
        # https://codegolf.stackexchange.com/questions/38033/increment-every-number-in-a-string
        while hname in self.hist_names:
            hname, nreplacements = re.subn('\d+', lambda x: str(int(x.group())+1),hname)
            # If we didn't find a number to replace, this loop will never end
            # So let's stick a number at the end of the name
            if nreplacements == 0:
                hname = "{}_1".format(hname)
        hist = "{}{}".format(hname,binning)

        self.hist_names.append(hname)
        info = [varexp, hist, selection, option, nentries, firstentry]
        self.queued.append(info)
        self.executed = False

    def GetHists(self, N=1, use_my_tqdm=True, file_cache=None):

        # if user wants to cache histograms in file, then make sure
        # the hash of all the queued draws + list of all files in tchain
        # matches what was in the file
        # In principle, if those 2 match, then results must be identical
        file_hash = hash("".join(sorted([x.GetTitle() for x in (self.ch.GetListOfFiles())])))
        queue_hash = hash(tuple(map(tuple,sorted(self.queued))))
        total_hash = hash(queue_hash+file_hash)
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

        if use_my_tqdm:
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
            if use_my_tqdm:
                total = last
                done = get_sum(dones)
                bytesread = get_sum(bytess)
                while done < total:
                    done = get_sum(dones)
                    bytesread = get_sum(bytess)
                    ioq.add_val(1.0*bytesread/1e6)
                    bar.progress(done,total,True)
                    which_done = map(lambda x:(x[0].value==x[1].value)and(x[0].value>0), zip(dones,totals))
                    label = "[{:.1f}MB @ {:.1f}MB/s]".format(ioq.get_last_val(),ioq.get_rate())
                    label += " [{}]".format("".join(map(lambda x:unichr(0x2022) if x else unichr(0x2219),which_done)).encode("utf-8"))
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
