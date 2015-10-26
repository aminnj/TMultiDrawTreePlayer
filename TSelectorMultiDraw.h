#pragma once

#include <TSelectorDraw.h>

class TSelectorMultiDraw: public TSelectorDraw {
    protected:
        virtual Bool_t CompileVariables(const char *varexp="", const char *selection="");

    public:
        ClassDef(TSelectorMultiDraw, 1);  //A specialized TSelector for multi-drawing
};
