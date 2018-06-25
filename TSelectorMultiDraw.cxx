#include <TSelectorMultiDraw.h>
#include <TTreeFormula.h>
#include <TTreeFormulaManager.h>
#include <TTree.h>

ClassImp(TSelectorMultiDraw)

Bool_t TSelectorMultiDraw::CompileVariables(const char *varexp/* = ""*/, const char *selection/* = ""*/) {
    Bool_t ret = TSelectorDraw::CompileVariables(varexp, selection);

    // // Disable quick load on all formulas
    // if (fSelect)
    //     fSelect->SetQuickLoad(false);

    // for (size_t i = 0; i < fDimension; i++) {
    //     fVar[i]->SetQuickLoad(false);
    // }

    return ret;
}

////////////////////////////////////////////////////////////////////////////////
/// Called in the entry loop for all entries accepted by Select.

double TSelectorMultiDraw::GetSelect() {
    if (fSelect) {
        return fSelect->EvalInstance(0);
    } else {
        return 1.0;
    }
}

void TSelectorMultiDraw::SetCache(double val, double weight) {
    fCacheVal = val;
    fCacheWeight = weight;
}

void TSelectorMultiDraw::ProcessFillMine(Long64_t entry, bool use_cache)
{
   if (fObjEval) {
      ProcessFillObject(entry);
      return;
   }

   if (fMultiplicity) {
      ProcessFillMultiple(entry);
      return;
   }

   // simple case with no multiplicity
   if (fForceRead && fManager->GetNdata() <= 0) return;

   if (fSelect) {
       if (use_cache) fW[fNfill] = fWeight * fCacheWeight;
       else fW[fNfill] = fWeight * fSelect->EvalInstance(0); // XXX <--- the fSelect eval is slow!, cached it!
       if (!fW[fNfill]) return;
   } else fW[fNfill] = fWeight;
   if (fVal) {
       if (fDimension == 1 && use_cache) {
           fVal[0][fNfill] = fCacheVal;
       } else {
           for (Int_t i = 0; i < fDimension; ++i) {
               if (fVar[i]) fVal[i][fNfill] = fVar[i]->EvalInstance(0);
           }
       }
   }
   fNfill++;
   if (fNfill >= fTree->GetEstimate()) {
       TakeAction();
       fNfill = 0;
   }

}

