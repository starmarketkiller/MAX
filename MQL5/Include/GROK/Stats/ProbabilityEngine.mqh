#pragma once
#property strict

inline double Prob_ToRiskScale(double score){ if(score<70) return 0.6; if(score<80) return 0.8; if(score<90) return 1.0; return 1.2; }
