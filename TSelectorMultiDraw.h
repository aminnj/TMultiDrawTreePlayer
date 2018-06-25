#pragma once
#ifndef ROOT_TSelectorMultiDraw
#define ROOT_TSelectorMultiDraw

#include "TSelectorDraw.h"

class TSelectorMultiDraw: public TSelectorDraw {
    protected:
        virtual Bool_t CompileVariables(const char *varexp="", const char *selection="");

        double fCacheVal;
        double fCacheWeight;

    public:
        
        virtual double GetSelect();
        virtual void SetCache(double val=-999., double weight=1.);
        virtual void ProcessFillMine(Long64_t entry, bool use_cache=false);

        ClassDef(TSelectorMultiDraw, 1);  //A specialized TSelector for multi-drawing
};

#endif
