#pragma once
#ifndef ROOT_TSelectorMultiDraw
#define ROOT_TSelectorMultiDraw

#include "TSelectorDraw.h"

class TSelectorMultiDraw: public TSelectorDraw {
    protected:
        virtual Bool_t CompileVariables(const char *varexp="", const char *selection="");

    public:
        
        virtual double GetSelect();
        virtual void ProcessFillMine(Long64_t entry, bool use_cache=false, double cache_val=-999., double weight=1.);

        ClassDef(TSelectorMultiDraw, 1);  //A specialized TSelector for multi-drawing
};

#endif
