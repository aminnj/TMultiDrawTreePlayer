#include <TSelectorMultiDraw.h>
#include <TTreeFormula.h>

ClassImp(TSelectorMultiDraw)

Bool_t TSelectorMultiDraw::CompileVariables(const char *varexp/* = ""*/, const char *selection/* = ""*/) {
    TSelectorDraw::CompileVariables(varexp, selection);

    // Disable quick load on all formulas
    if (fSelect)
        fSelect->SetQuickLoad(false);

    for (size_t i = 0; i < fDimension; i++) {
        fVar[i]->SetQuickLoad(false);
    }
}
