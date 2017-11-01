cd /cvmfs/cms.cern.ch/slc6_amd64_gcc530/cms/cmssw/CMSSW_9_2_8; cmsenv; cd -
rootcint -f dictionary.cc -c -p classes.h LinkDef.h
g++ -shared -fPIC `root-config --cflags` -I. dictionary.cc TMultiDrawTreePlayer.cxx TSelectorMultiDraw.cxx `root-config --ldflags --libs` -lTreePlayer  -o libTMulti.so
