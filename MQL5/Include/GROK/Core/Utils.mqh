#pragma once
#property strict

inline double Grok_Clamp(double v,double lo,double hi){ return MathMax(lo,MathMin(hi,v)); }
inline bool Grok_IsValidPrice(double p){ return (p>0.0 && p<DBL_MAX); }
